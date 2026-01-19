from dataclasses import dataclass
from typing import Optional
from .generator import Generator

@dataclass
class WindGenerator(Generator):
    """
    Representa um gerador eólico. Não possui custos de combustível.
    """
    inverter_s_max_mva: Optional[float] = None
    
    def __post_init__(self):
        if self.name is None:
            self.name = f"WindGenerator_{self.id}"
        super().__post_init__()

    @property 
    def p_curtailment_pu(self) -> float:
        return self.p_max_pu - self.p_pu
    
    @property
    def p_curtailment_mw(self) -> float:
        return self.p_max_mw - self.p_mw
    
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
        return f"Wind{base_repr}"