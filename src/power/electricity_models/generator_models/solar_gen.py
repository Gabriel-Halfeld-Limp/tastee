from dataclasses import dataclass
from typing import Optional
from .generator import Generator

@dataclass
class SolarGenerator(Generator):
    """
    Representa um gerador eólico. Não possui custos de combustível.
    """
    inverter_s_max_mva: Optional[float] = None
    
    def __post_init__(self):
        if self.name is None:
            self.name = f"SolarGenerator_{self.id}"
        super().__post_init__()

    
    @property
    def inverter_s_max_pu(self) -> Optional[float]:
        if self.inverter_s_max_mva is not None:
            return self.inverter_s_max_mva / self.sb_mva
        return None
    
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
        return f"Solar{base_repr}"