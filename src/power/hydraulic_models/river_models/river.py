from dataclasses import dataclass
from power.hydraulic_models.node_models.hydro_node import HydroBus

@dataclass
class River:
    """Represents a river connecting two hydraulic nodes."""
    id: int
    name: str
    from_node: HydroBus
    to_node: HydroBus
    
