from dataclasses import dataclass, field
from typing import List, Optional
from power.hydraulic_models.node_models.hydro_node import HydroBus
from power.electricity_models.generator_models.hydro_gen import HydroGenerator
from power.hydraulic_models.river_models.river import River


@dataclass
class HydroNetwork:
    """Represents a hydraulic network."""
    id:              Optional[int]        = None
    name:            Optional[str]        = None
    hydro_buses:     List[HydroBus]       = field(default_factory=list)
    rivers:          List[River]          = field(default_factory=list)
    hydro_generators: List[HydroGenerator] = field(default_factory=list)

    def __post_init__(self):
        if self.name is None:
            if self.id is not None:
                self.name = f"HydroNetwork_{self.id}"
            else:
                self.name = "HydroNetwork"
    
    def add_generator(self, generator:HydroGenerator):
        if generator not in self.hydro_generators:
            self.hydro_generators.append(generator)
    

