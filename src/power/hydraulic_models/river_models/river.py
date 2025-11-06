from dataclasses import dataclass
from ..node_models.hydro_node import HydroNode

@dataclass
class River:
    """Represents a river connecting two hydraulic nodes."""
    id: int
    name: str
    from_node: HydroNode
    to_node: HydroNode
