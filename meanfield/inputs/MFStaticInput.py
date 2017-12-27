from typing import Dict, Union

from brian2 import units, check_units, PoissonInput

from meanfield.inputs.MFInput import MFInput
from meanfield.utils import lazyproperty
from meanfield.parameters import IP
from meanfield.parameters.MFParams import MFParams
from meanfield.populations.MFPop import MFPop
from meanfield.parameters import Connection
from meanfield.parameters.Connection import ConnectionStrategy


class MFStaticInput(MFInput):

    @check_units(rate=units.hertz, n=1)
    def __init__(self, name: str, pop: MFPop, n: int, rate: units.hertz, params: Union[Dict, MFParams], connection: ConnectionStrategy=Connection.all_to_all()):
        super().__init__(name, pop, params, connection, add_as_input=False)

        self.rate = rate
        self.n = n

    @check_units(result=1)
    def g_dyn(self):
        return self.rate * self.n * self.params[IP.TAU]

    @lazyproperty
    def brian2(self):
        return PoissonInput(self.pop.brian2, self.post_variable_name, self.n, self.rate, 1)