from dataclasses import dataclass
from .abc_hydro_node import ABCHydroNode

@dataclass
class HydroNode(ABCHydroNode):
    """Represents a node in the hydraulic network."""
    id: int
    name: str

    def __repr__(self):
        return f"HydroNode(id={self.id}, name='{self.name}')"
