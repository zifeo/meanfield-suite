import matplotlib.pyplot as plt
import numpy as np
from brian2 import PopulationRateMonitor
from brian2.units import *

from meanfield.MFSystem import MFSystem
from meanfield.inputs.MFStaticInput import MFStaticInput
from meanfield.parameters import IP
from meanfield.parameters import PP
from meanfield.populations.MFLinearPopulation import MFLinearPopulation
from meanfield.solvers.MFSolver import MFSolverRatesVoltages
from meanfield.utils import reset_brian2

n_pop = 25
n_noise = 100


def for_rate(rate):
    reset_brian2()

    pop = MFLinearPopulation(n_pop, {
        PP.GM: 25. * nS,
        PP.CM: 0.5 * nF,
        PP.VL: -70. * mV,
        PP.VTHR: -50. * mV,
        PP.VRES: -55. * mV,
        PP.TAU_RP: 2. * ms
    })
    pop.rate = 1 * Hz

    MFStaticInput(n_noise, rate * Hz, pop, {
        IP.GM: 2 * nS,
        IP.VREV: 0 * volt,
        IP.TAU: 2. * ms,
    })

    t = 500 * ms
    dt = 0.1 * ms

    system = MFSystem(pop)
    rate = PopulationRateMonitor(pop.brian2)
    net = system.collect_brian2_network(rate)
    net.run(t)
    stable_t = int(t / dt * 0.1)
    isolated = np.array(rate.rate)[stable_t:-stable_t]
    sim = np.mean(isolated)

    solver = MFSolverRatesVoltages(system, solver='simplex', maxiter=1)
    sol = solver.run()
    return [sol.state[0], sim]


rates = np.linspace(1, 100, 20)
dom = np.array([for_rate(r) for r in rates])
print(dom)
plt.plot(rates, dom[:, 0], label='theory')
plt.plot(rates, dom[:, 1], label='simulation')
plt.xlabel(f'Noise rate (Hz) on {n_pop}')
plt.ylabel(f'Population rate (Hz) from {n_noise}')
plt.legend()
plt.show()

print(dom[:, 0] - dom[:, 1])
plt.plot(rates, dom[:, 0] - dom[:, 1])
plt.show()