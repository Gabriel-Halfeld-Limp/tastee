from dataclasses import dataclass, field
from typing import ClassVar, Optional
import numpy as np

from ..bus_models import Bus

@dataclass
class Load:
    bus: 'Bus'
    id: int
    name: Optional[str] = None

    pb: float = 1.0
    p_input: float = 0.0
    p_input_series: np.ndarray = field(default_factory=lambda: np.array([]))
    q_input: float = 0.0
    power_factor: float = 1.0
    p_max_input: float = float('inf')
    p_min_input: float = 0.0
    q_max_input: Optional[float] = None
    q_min_input: Optional[float] = None
    cost_shed_input: Optional[float] = 10000.0
    
    #Attributes for loads that make bids on a market
    cost_a_input: float = 0.0
    cost_b_input: float = 0.0
    cost_c_input: float = 0.0

    def __post_init__(self):
        if self.name is None:
            self.name = f"Load {self.id}"

        self.bus.add_load(self)
        self.network = self.bus.network
        self.network.loads.append(self)

    # --- Potência Ativa (p) ---
    @property
    def p(self) -> float:
        return self.p_input / self.pb
    
    @p.setter
    def p(self, new_p_pu: float):
        self.p_input = new_p_pu * self.pb
    
    @property
    def p_series(self) -> np.ndarray:
        return self.p_input_series/ self.pb

    # --- Potência Reativa (q) ---
    @property
    def q(self) -> float:
        return self.q_input / self.pb

    @q.setter
    def q(self, new_q_pu: float):
        self.q_input = new_q_pu * self.pb
    
    @property
    def q_series(self) -> np.ndarray:
        return self.p_series * np.tan(np.arccos(self.power_factor))
    
    # --- Potência Ativa Máxima (p_max) ---
    @property
    def p_max(self) -> float:
        return self.p_max_input / self.pb
    
    @p_max.setter
    def p_max(self, new_p_max_pu: float):
        self.p_max_input = new_p_max_pu * self.pb

    # --- Potência Ativa Mínima (p_min) ---
    @property
    def p_min(self) -> float:
        return self.p_min_input / self.pb
        
    @p_min.setter
    def p_min(self, new_p_min_pu: float):
        self.p_min_input = new_p_min_pu * self.pb

    # --- Potência Reativa Máxima (q_max) ---
    @property
    def q_max(self) -> Optional[float]:
        return self.q_max_input / self.pb if self.q_max_input is not None else None

    @q_max.setter
    def q_max(self, new_q_max_pu: Optional[float]):
        self.q_max_input = new_q_max_pu * self.pb if new_q_max_pu is not None else None

    # --- Potência Reativa Mínima (q_min) ---
    @property
    def q_min(self) -> Optional[float]:
        return self.q_min_input / self.pb if self.q_min_input is not None else None

    @q_min.setter
    def q_min(self, new_q_min_pu: Optional[float]):
        self.q_min_input = new_q_min_pu * self.pb if new_q_min_pu is not None else None

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

    @property
    def cost_shed(self) -> float:
        return self.cost_shed_input * self.pb
    
    @cost_shed.setter
    def cost_shed(self, new_cost_shed_pu: float):
        self.cost_shed_input = new_cost_shed_pu / self.pb

    def __repr__(self):
        return (f"Load(id={self.id}, bus={self.bus.id}, p={self.p:.3f}, q={self.q:.3f}, "
                f"p_range=[{self.p_min:.3f},{self.p_max:.3f}], q_range=[{self.q_min},{self.q_max}])")