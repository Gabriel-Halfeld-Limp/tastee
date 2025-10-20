from ..bus_models import Bus
from dataclasses import dataclass
from typing import ClassVar, Optional
from .generator import Generator

@dataclass
class ThermalGenerator(Generator):
# --- Thermal-Specific Attributes ---
    cost_a_input: Optional[float] = 0.0
    cost_b_input: Optional[float] = 0.0
    cost_c_input: Optional[float] = 0.0
    ramp_input: Optional[float] = 0.0
    mvu_input: Optional[float] = None
    mvd_input: Optional[float] = None

    def __post_init__(self):
        super().__post_init__()
        if self.mvu_input is None:
            self.mvu_input = self.p_max_input * 0.2

        if self.mvd_input is None:
            self.mvd_input = self.p_max_input * 0.2

    # --- Coeficiente de Custo 'a' (quadrático) ---
    @property
    def cost_a(self) -> float:
        return self.cost_a_input
        
    @cost_a.setter
    def cost_a(self, new_cost_a: float):
        self.cost_a_input = new_cost_a

    # --- Coeficiente de Custo 'b' (linear) ---
    @property
    def cost_b(self) -> float:
        return self.cost_b_input * self.pb
        
    @cost_b.setter
    def cost_b(self, new_cost_b_pu: float):
        self.cost_b_input = new_cost_b_pu / self.pb

    # --- Coeficiente de Custo 'c' (fixo) ---
    @property
    def cost_c(self) -> float:
        return self.cost_c_input * self.pb**2
        
    @cost_c.setter
    def cost_c(self, new_cost_c_pu: float):
        self.cost_c_input = new_cost_c_pu / (self.pb**2)
    
    # --- Rampa (ramp) ---
    @property
    def ramp(self) -> float:
        return self.ramp_input / self.pb
        
    @ramp.setter
    def ramp(self, new_ramp_pu: float):
        self.ramp_input = new_ramp_pu * self.pb

    # --- MVU E MVD ---
    @property
    def mvu(self) -> float:
        return self.mvu_input / self.pb

    @property
    def mvd(self) -> float:
        return self.mvd_input / self.pb

    def __repr__(self):
        return (f"ThermalGenerator(id={self.id}, bus={self.bus.id}, p={self.p:.3f}, q={self.q:.3f}, "
                f"p_range=[{self.p_min:.3f},{self.p_max:.3f}], q_range=[{self.q_min},{self.q_max}])")
    


