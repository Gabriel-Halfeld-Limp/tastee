from dataclasses import dataclass, field
from typing import List
from power.hydraulic_models.node_models.hydro_node import HydroNode
from power.hydraulic_models.river_models.river import River

@dataclass
class HydroNetwork:
    """Represents a hydraulic network."""
    nodes: List[HydroNode] = field(default_factory=list)
    rivers: List[River] = field(default_factory=list)
