from ..bus_models import Bus
from dataclasses import dataclass
from typing import ClassVar, Optional

@dataclass
class Generator:
    bus: 'Bus'
    id: int
    name: Optional[str] = None
    pb: float = 1.0
    p_input: float = 0.0
    q_input: float = 0.0
    p_max_input: float = float('inf')
    p_min_input: float = 0.0
    q_max_input: Optional[float] = 99999
    q_min_input: Optional[float] = -99999

    def __post_init__(self):
        if self.name is None:
            self.name = f"Generator_{self.id}"

        self.bus.add_generator(self)
        self.network = self.bus.network
        self.network.generators.append(self)

    # --- Potência Ativa (p) ---
    @property
    def p(self) -> float:
        return self.p_input / self.pb
    
    @p.setter
    def p(self, new_p_pu: float):
        self.p_input = new_p_pu * self.pb

    # --- Potência Reativa (q) ---
    @property
    def q(self) -> float:
        return self.q_input / self.pb

    @q.setter
    def q(self, new_q_pu: float):
        self.q_input = new_q_pu * self.pb

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

    def __repr__(self):
        return (f"Generator(id={self.id}, bus={self.bus.id}, p={self.p:.3f}, q={self.q:.3f}, "
                f"p_range=[{self.p_min:.3f},{self.p_max:.3f}], q_range=[{self.q_min},{self.q_max}])")
