from dataclasses import dataclass
from typing import Optional
from power.electricity_models.generator_models.generator import Generator
from power.hydraulic_models.node_models.hydro_node import HydroNode

@dataclass
class HydroGenerator(Generator):
    """
    Representa um gerador eólico. Não possui custos de combustível.
    """
    hydro_node: Optional[HydroNode] = None

    def __post_init__(self):
        super().__post_init__()
        if self.name == f"Generator_{self.id}":
            self.name = f"HydroGenerator_{self.id}"

    @property
    def cost_a_pu(self) -> float:
        return 0.0

    @property
    def cost_b_pu(self) -> float:
        return 0.0

    @property
    def cost_c_pu(self) -> float:
        return 0.0

    def __repr__(self):
        base_repr = super().__repr__()
        return f"Hydro{base_repr}"