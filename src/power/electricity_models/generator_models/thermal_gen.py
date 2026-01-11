from power.electricity_models.generator_models.generator import Generator
from dataclasses import dataclass

@dataclass
class ThermalGenerator(Generator):
# --- Thermal-Specific Attributes ---
    cost_a_mw: float = 0.0
    cost_b_mw: float = 0.0
    cost_c_mw: float = 0.0
    max_ramp_up_mw: float = 99999
    max_ramp_down_mw: float = -99999

    def __post_init__(self):
        if self.name is None:
            self.name = f"ThermalGenerator_{self.id}"
        super().__post_init__()

    # --- Coeficiente de Custo 'a' (quadrático) ---
    @property
    def cost_a_pu(self) -> float:
        return self.cost_a_mw
        
    @cost_a_pu.setter
    def cost_a_pu(self, new_cost_a: float):
        self.cost_a_mw = new_cost_a

    # --- Coeficiente de Custo 'b' (linear) ---
    @property
    def cost_b_pu(self) -> float:
        return self.cost_b_mw * self.sb_mva
        
    @cost_b_pu.setter
    def cost_b_pu(self, new_cost_b_pu: float):
        self.cost_b_mw = new_cost_b_pu / self.sb_mva

    # --- Coeficiente de Custo 'c' (fixo) ---
    @property
    def cost_c_pu(self) -> float:
        return self.cost_c_mw * self.sb_mva**2
        
    @cost_c_pu.setter
    def cost_c_pu(self, new_cost_c_pu: float):
        self.cost_c_mw = new_cost_c_pu / (self.sb_mva**2)
    
    # --- Rampa (ramp_pu) ---
    @property
    def max_ramp_up_pu(self) -> float:
        return self.max_ramp_up_mw / self.sb_mva
    
    @max_ramp_up_pu.setter
    def max_ramp_up_pu(self, new_ramp_up_pu: float):
        self.max_ramp_up_mw = new_ramp_up_pu * self.sb_mva
    
    @property
    def max_ramp_down_pu(self) -> float:
        return self.max_ramp_down_mw / self.sb_mva
    
    @max_ramp_down_pu.setter
    def max_ramp_down_pu(self, new_ramp_down_pu: float):
        self.max_ramp_down_mw = new_ramp_down_pu * self.sb_mva

    def __repr__(self):
        return (f"ThermalGenerator(id={self.id}, bus={self.bus.id}, p_mw={self.p_mw:.3f}, q_mvar={self.q_mvar:.3f}, "
                f"p_range=[{self.p_min_mw:.3f},{self.p_max_mw:.3f}], q_range=[{self.q_min_mvar},{self.q_max_mvar}])")

