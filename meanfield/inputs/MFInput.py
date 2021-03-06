from abc import abstractmethod
from types import MappingProxyType
from typing import Union, Dict

from brian2 import units, check_units, Equations, BrianObject

from meanfield.parameters import Connection
from meanfield.parameters import IP, PP
from meanfield.parameters.Connection import ConnectionStrategy
from meanfield.parameters.MFParameters import MFParameters
from meanfield.populations.MFPopulation import MFPopulation
from meanfield.utils import create_identifier, create_name


class MFInput(object):
    """Source: a synapse coupled to pops"""

    arguments = MappingProxyType({
        IP.GM: units.siemens,
        IP.VREV: units.volt,
        IP.TAU: units.second,
    })

    defaults = MappingProxyType({})

    def __init__(self, origin: Union[None, MFPopulation], target: MFPopulation, parameters: Union[Dict, MFParameters]=None, name: str=None, connection: ConnectionStrategy=Connection.all_to_all()):

        self.name = name if name else create_name(self)
        self.ref = create_identifier(self.name)

        self.parameters = MFParameters({}) if not parameters else MFParameters(parameters)
        self.parameters.fill(self.defaults)
        self.parameters.verify(self.arguments)

        self.origin = origin
        self.target = target
        self.connection = connection

    def __getitem__(self, key):
        return self.parameters[key]

    def __setitem__(self, key, value):
        self.parameters[key] = value

    def __repr__(self) -> str:
        return "{} [{}] ({}, {})".format(self.__class__.__name__, self.name, self.parameters, self.connection)

    # Theory

    @property
    @check_units(result=units.siemens)
    def conductance(self) -> units.siemens:
        return self.g_dyn() * self[IP.GM]

    @property
    @check_units(result=units.amp)
    def voltage_conductance(self) -> units.amp:
        return self.conductance * (self[IP.VREV] - self.target[PP.VL])

    @abstractmethod
    def g_dyn(self):
        pass

    # Simulation

    @abstractmethod
    def brian2(self) -> BrianObject:
        """Builds lazily Brian2 synapse component once."""
        pass

    @property
    def brian2_model(self) -> Equations:
        """Returns Brian2 dynamic (Equations) affecting specified populations."""
        return Equations(
            '''
            I = g * (v - vrev) * s : amp
            ds / dt = - s / tau : 1
            ''',
            I=self.current_name,
            g=self[IP.GM],
            s=self.post_variable_name,
            vrev=self[IP.VREV],
            tau=self[IP.TAU],
        )

    @property
    def current_name(self) -> str:
        return f'I_{self.ref}'

    @property
    def post_variable_name(self) -> str:
        return f's_{self.ref}'

