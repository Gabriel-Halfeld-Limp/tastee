from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import ClassVar, List, Optional


@dataclass
class Bus:
    network: "Network"
    id: Optional[int] = None
    name: Optional[str] = None
    bus_type: str = "PQ"  # "slack", "PQ", "PV"
    v: float = 1.0 # in pu
    theta: float = 0.0 # in degrees
    Sb: float = 1.0 # Base power in MVA
    Sh: float = 0.0 # Shunt admittance connected to the bus

    # Relacionamentos
    loads: List["Load"] = field(default_factory=list)
    generators: List["Generator"] = field(default_factory=list)

    _id_counter: ClassVar[int] = 0

    def __post_init__(self):
        if self.id is None:
            self.id = Bus._id_counter
            Bus._id_counter += 1
        else:
            self.id = int(self.id)
            if self.id >= Bus._id_counter:
                Bus._id_counter = self.id + 1

        if self.name is None:
            self.name = f"Bus {self.id}"

        # Add the bus to the network
        self.network.buses.append(self)
    
    @property
    def theta_rad(self) -> float:
        return np.deg2rad(self.theta)
    
    @property
    def p(self) -> float:
        """Net active power injection (pu)"""
        return sum(g.p for g in self.generators) - sum(l.p for l in self.loads)

    @property
    def q(self) -> float:
        """Net reactive power injection (pu)"""
        return sum(g.q for g in self.generators) - sum(l.q for l in self.loads) 

    @property
    def shunt(self) -> complex:
        """Shunt admittance connected to the bus (pu)"""
        return (self.Sh*1j)/self.Sb
    
    # add_generator and add_load methods are used inside Generator and Load classes automatically. 
    # You just need to inform wich bus the generator or load is connected to.
    def add_generator(self, generator: 'Generator'):
        if generator not in self.generators:
            self.generators.append(generator)

    def add_load(self, load: 'Load'):
        if load not in self.loads:
            self.loads.append(load)

    def __repr__(self):
        return (f"Bus(id={self.id}, type={self.bus_type}, v={self.v:.3f} pu, "
                 f"theta={self.theta_rad:.3f} rad, p={self.p:.3f} pu, q={self.q:.3f} pu, "
                 f"shunt={self.shunt:.3f} pu, "
                 f"gen={len(self.generators)}, load={len(self.loads)})")
    