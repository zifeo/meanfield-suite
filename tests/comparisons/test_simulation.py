from brian2 import PopulationRateMonitor, Network, defaultclock, NeuronGroup, Synapses, PoissonInput
from brian2.units import *
import matplotlib.pyplot as plt
import numpy as np

from meanfield.MFSystem import MFSystem
from meanfield.parameters import NP
from meanfield.parameters import SP
from meanfield.populations.MFLinearPop import MFLinearPop
from meanfield.solvers.MFSolver import MFSolverRatesVoltages
from meanfield.sources.MFStaticSource import MFStaticSource
from meanfield.sources.MFLinearSource import MFLinearSource
from tests.utils import enable_cpp
from meanfield.utils import brian2_introspect

enable_cpp()

class TestSimulation(object):

    def test_brian2_simulation(self):

        eqs = '''
        I_rec = (9.73 * psiemens) * (v - (-70. * volt)) * s_rec : amp
        I_noise = (2. * nsiemens) * (v - (0. * volt)) * s_noise : amp
        I = I_rec + I_noise : amp
        dv/dt = int(not_refractory)*((- (25. * nsiemens) * (v - (-70. * mvolt)) - I) / (0.5 * nfarad)) : volt (unless refractory)
        ds_rec/dt = - s_rec / (10. * msecond) : 1
        ds_noise/dt = - s_noise / (2. * msecond) : 1
        '''



    def test_simulation_theory(self):

        t = 10000 * ms
        dt = 0.01 * ms
        defaultclock.dt = dt

        pop = MFLinearPop("pop", 100, {
            NP.GM: 25. * nS,
            NP.CM: 0.5 * nF,
            NP.VL: -70. * mV,
            NP.VTHR: -50. * mV,
            NP.VRES: -55. * mV,
            NP.TAU_RP: 2. * ms
        })
        pop.rate = 10 * Hz

        noise = MFStaticSource("noise", pop, 1000, 10 * Hz, {
            SP.GM: 2 * nS,
            SP.VREV: 0 * volt,
            SP.TAU: 2. * ms,
        })
        pop.add_noise(noise)

        rec = MFLinearSource("rec", pop, {
            SP.GM: 0.973/100 * nS,
            SP.VREV: -70 * volt,
            SP.TAU: 10. * ms,
        }, pop)

        system = MFSystem("pop noise rec")
        system.pops += [pop]

        solver = MFSolverRatesVoltages(system, solver='mse', maxiter=1)
        sol = solver.run()
        theory = sol.state[0]

        rm = PopulationRateMonitor(pop.brian2)

        net = Network()
        net.add(pop.brian2)
        net.add(noise.brian2)
        net.add(rec.brian2)
        net.add(rm)
        net.run(t)

        print(pop.brian2)
        print(noise.brian2)
        print(rec.brian2)

        brian2_introspect(net)
        system.introspect()

        stable_t = int(t / dt * 0.1)
        isolated = np.array(rm.rate)[stable_t:-stable_t]
        print(isolated.mean())

        plt.plot(rm.t / ms, rm.smooth_rate(width=25 * ms) / Hz)
        plt.plot(np.ones(10000) * isolated.mean(), label='mean')
        plt.plot(np.ones(10000) * theory, label='theory')
        plt.legend()
        plt.show()



