import signal
import sys
from functools import partial

import matplotlib.pylab as plt
import numpy as np
from brian2 import units
from scipy.optimize import root, minimize

from meanfield.solvers.MFConstraint import MFConstraint
from meanfield.solvers.MFState import MFState


def gradient_solver(mfstate, p_0, dt=.1, tmax=30.):
    """Simple gradient descent along the error."""

    t = 0.
    state = np.array(p_0)
    states = [state]

    print("GRADIENT SOLVER START", flush=True)
    while t < tmax:
        state -= [dt * v for v in mfstate(state)]
        print(state)
        t += dt
        states.append(list(state))

    states = np.array(states).T
    nspl = states.shape[0]
    #for i in range(nspl):
    #    plt.subplot(nspl, 1, i + 1)
    #    plt.plot(states[i, :])
    #plt.show()

    # minimal solution object to return
    class sol:
        x = state
        fun = mfstate.error

    return sol()


class MFSolver(object):

    # FIXME max iter = 20
    def __init__(self, mfstate, maxiter=1, solver="hybr", print_status=False, crit=1e-5, tol=1e-12, fail_val=None):

        self.mfstate = mfstate
        self.solver = solver
        self.maxiter = maxiter
        self.print_status = print_status
        self.crit = crit
        self.tol = tol
        self.it = 0
        self.error = 1e10
        self.state = "initialized"
        self.fail_val = fail_val

    def run(self, state_0=None, noise_percent=.1):

        # set solver state to the passed state if none was explicitly given
        if not state_0:
            state_0 = self.mfstate.state

        self.it = 0
        abs_err = 1e10
        min_sol = None
        min_abs_err = 1e10
        crit = self.crit
        tol = self.tol

        print("\n-------------------")
        print("[%s] initializing minimization: %s" % (self.__class__.__name__, self.solver))
        print("[")

        # allow interruption of minimization loop, did not work otherwise.
        signal_handler = lambda signal, frame: sys.exit(0)
        signal.signal(signal.SIGINT, signal_handler)

        # loop over tries to solve the system
        while abs_err > crit:

            self.it += 1

            # interrupt upon reaching the maxiter.
            if self.it > self.maxiter:
                print("]\n[%s] maximum iterations reached" % self.__class__.__name__)
                self.state = "EXCEEDED"
                return self.finalize(min_sol)

            # get stochastic initial state
            up_dist = [c.bound_up - state_0[i] for i, c in enumerate(self.mfstate.constraints)]
            down_dist = [c.bound_up - state_0[i] for i, c in enumerate(self.mfstate.constraints)]
            max_dist = [min(up_dist[i], down_dist[i]) for i in range(len(self.mfstate.constraints))]

            p_0 = state_0

            bounds = [[c.bound_down, c.bound_up] for c in self.mfstate.constraints]

            plotting = False

            # solve
            if self.solver == "gradient":  # own implementation
                sol = gradient_solver(self.mfstate, p_0)
                abs_err = max(np.abs(sol.fun))


            elif self.solver == "mse":
                sq = lambda y: np.sum(np.array(y) ** 2)
                #print(self.mfstate)
                xs2 = []
                ys2 = []
                def f(x):
                    v = self.mfstate(x, fun=sq)
                    xs2.append(np.array(x)[0])
                    ys2.append(v)
                    #print(np.array(x)[0], v)
                    return v

                #sol = minimize(f, p_0, bounds=bounds, method='Nelder-Mead')
                sol = minimize(f, p_0, bounds=bounds, method='L-BFGS-B')
                #, options={
                    #'disp': None,
                    #'maxls': 20,
                    #'iprint': -1,
                    #'gtol': 1e-05,
                #    'eps': 0.00001,
                    #'maxiter': 15000,
                    #'ftol': 2.220446049250313e-09,
                    #'maxcor': 10,
                    #'maxfun': 15000
                #})

                # watch out nit

                if plotting:
                    xs = np.array(xs2)
                    ys = np.array(ys2)
                    plt.plot(xs[xs.argsort()], ys[xs.argsort()])
                    plt.show()

                    xs = np.linspace(0, 10, 200) * units.Hz
                    plt.plot(xs, [f([x]) for x in xs], label='fun')
                    #plt.axvline(sol.x, c='r', label='sol')
                    plt.legend()
                    plt.show()

                abs_err = np.sqrt(sol.fun)

            else:  # scipy solvers
                sol = root(self.mfstate, p_0, jac=None, method=self.solver, tol=tol)
                abs_err = max(abs(sol.fun))

            # calculate the abs err, store minimal solution
            if abs_err < min_abs_err:
                min_abs_err = abs_err
                min_sol = sol
                sys.stdout.write('X')
            else:
                # display update
                sys.stdout.write('.')

            if self.it > 1 and self.it % 50 == 0 and self.it < self.maxiter:
                sys.stdout.write('\n ')
            sys.stdout.flush()

        print("]\n[%s] finished successfully" % self.__class__.__name__)
        self.state = "SUCCESS"
        return self.finalize(sol)

    def finalize(self, sol):
        self.mfstate.state = sol.x

        # set the state value to the fail_val if we did not converge
        if (self.fail_val is not None) and self.state != 'SUCCESS':
            self.mfstate.state = sol.x * self.fail_val

        self.error = sol.fun
        print(self.mfstate)
        print("-------------------\n")
        return self.mfstate

class MFSolverRatesVoltages(MFSolver):

    def __init__(self, system, force_nmda=False, *args, **kwargs):
        # create constraints on the firing rates and mean voltages

        constraints = []
        functions = []

        for p in system.populations:

            constraints.append(
                MFConstraint(
                    "%s-%s" % (p.name, "rate"),
                    free_get=partial(lambda x: x.rate, p),
                    free_set=partial(lambda x, val: setattr(x, "rate", val), p),
                    error_fun=partial(lambda x: x.rate - x.rate_prediction, p),
                    bound_down=0. * units.Hz,
                    bound_up=1000. * units.Hz
                )
            )

            # def any([s.is_nmda for s in p.inputs])
            if False:#p.has_nmda or force_nmda:
                print("Population %s has NMDA -> solving for voltages" % p.name)
                constraints.append(
                    MFConstraint(
                        "%s-%s" % (p.name, "v_mean"),
                        partial(lambda x: x.v_mean, p),
                        partial(lambda x, val: setattr(x, "v_mean", val), p),
                        partial(lambda x: x.v_mean - x.v_mean_prediction, p),
                        -80. * units.mV, 50. * units.mV
                    )
                )
            else:
                functions.append(
                    partial(lambda x: setattr(x, "v_mean", x.v_mean_prediction), p),
                )

        state = MFState(constraints, dependent_functions=functions)
        super(MFSolverRatesVoltages, self).__init__(state, *args, **kwargs)

