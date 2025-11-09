from dataclasses import dataclass, field
from typing import ClassVar, Optional
import numpy as np

from ..bus_models import Bus

@dataclass
class Load:
    bus:         'Bus'
    id:           int
    name:         Optional[str] = None
    p_mw:         float = 0.0
    q_mvar:       float = 0.0
    p_max_mw:     float = float('inf')
    p_min_mw:     float = 0.0
    q_max_mvar:   float = None
    q_min_mvar:   float = None
    cost_shed_mw: float = 10000.0
    power_factor: float = 1.0
    p_mw_series:  np.ndarray = field(default_factory=lambda: np.array([]))
    #Attributes for loads that make bids on a market
    cost_a_mw:    float = 0.0
    cost_b_mw:    float = 0.0
    cost_c_mw:    float = 0.0

    def __post_init__(self):
        if self.name is None:
            self.name = f"Load_{self.id}"
        self.bus.add_load(self)
        self.network = self.bus.network
        self.network.loads.append(self)
        self.sb_mva = self.network.sb_mva

    # --- Potência Ativa (p) ---
    @property
    def p_pu(self) -> float:
        return self.p_mw / self.sb_mva
    
    @p_pu.setter
    def p_pu(self, new_p_pu: float):
        self.p_mw = new_p_pu * self.sb_mva
    
    @property
    def p_series(self) -> np.ndarray:
        return self.p_mw_series/ self.sb_mva

    # --- Potência Reativa (q) ---
    @property
    def q_pu(self) -> float:
        return self.q_mvar / self.sb_mva

    @q_pu.setter
    def q_pu(self, new_q_pu: float):
        self.q_mvar = new_q_pu * self.sb_mva
    
    @property
    def q_series(self) -> np.ndarray:
        return self.p_series * np.tan(np.arccos(self.power_factor))
    
    # --- Potência Ativa Máxima (p_max_pu) ---
    @property
    def p_max_pu(self) -> float:
        return self.p_max_mw / self.sb_mva
    
    @p_max_pu.setter
    def p_max_pu(self, new_p_max_pu: float):
        self.p_max_mw = new_p_max_pu * self.sb_mva

    # --- Potência Ativa Mínima (p_min_pu) ---
    @property
    def p_min_pu(self) -> float:
        return self.p_min_mw / self.sb_mva
        
    @p_min_pu.setter
    def p_min_pu(self, new_p_min_pu: float):
        self.p_min_mw = new_p_min_pu * self.sb_mva

    # --- Potência Reativa Máxima (q_max) ---
    @property
    def q_max(self) -> Optional[float]:
        return self.q_max_mvar / self.sb_mva if self.q_max_mvar is not None else None

    @q_max.setter
    def q_max(self, new_q_max_pu: Optional[float]):
        self.q_max_mvar = new_q_max_pu * self.sb_mva if new_q_max_pu is not None else None

    # --- Potência Reativa Mínima (q_min) ---
    @property
    def q_min(self) -> Optional[float]:
        return self.q_min_mvar / self.sb_mva if self.q_min_mvar is not None else None

    @q_min.setter
    def q_min(self, new_q_min_pu: Optional[float]):
        self.q_min_mvar = new_q_min_pu * self.sb_mva if new_q_min_pu is not None else None

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

    @property
    def cost_shed_pu(self) -> float:
        return self.cost_shed_mw * self.sb_mva
    
    @cost_shed_pu.setter
    def cost_shed_pu(self, new_cost_shed_pu: float):
        self.cost_shed_mw = new_cost_shed_pu / self.sb_mva

    def __repr__(self):
        return (f"Load(id={self.id}, bus={self.bus.id}, p_pu={self.p_pu:.3f}, q_pu={self.q_pu:.3f}, "
                f"p_range=[{self.p_min_pu:.3f},{self.p_max_pu:.3f}], q_range=[{self.q_min},{self.q_max}])")