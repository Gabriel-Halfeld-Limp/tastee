from power.electricity_models.bus_models import Bus
from dataclasses import dataclass
from typing import Optional

@dataclass
class Generator:
    bus:       'Bus'
    id:         int
    name:       Optional[str] = None
    p_mw:       float         = 0.0
    q_mvar:     float         = 0.0
    p_max_mw:   float         = 99999
    p_min_mw:   float         = 0.0
    q_max_mvar: float         = 99999
    q_min_mvar: float         = 0.0

    def __post_init__(self):
        if self.name is None:
            self.name = f"Generator_{self.id}"
        self.network = self.bus.network
        self.network.add_generator(self)
        self.bus.add_generator(self)
        self.sb_mva = self.network.sb_mva

    # --- Potência Ativa (p_pu) ---
    @property
    def p_pu(self) -> float:
        return self.p_mw / self.sb_mva
    
    @p_pu.setter
    def p_pu(self, new_p_pu: float):
        self.p_mw = new_p_pu * self.sb_mva

    # --- Potência Reativa (q_pu) ---
    @property
    def q_pu(self) -> float:
        return self.q_mvar / self.sb_mva

    @q_pu.setter
    def q_pu(self, new_q_pu: float):
        self.q_mvar = new_q_pu * self.sb_mva

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

    # --- Potência Reativa Máxima (q_max_pu) ---
    @property
    def q_max_pu(self) -> Optional[float]:
        return self.q_max_mvar / self.sb_mva if self.q_max_mvar is not None else None

    @q_max_pu.setter
    def q_max_pu(self, new_q_max_pu: Optional[float]):
        self.q_max_mvar = new_q_max_pu * self.sb_mva if new_q_max_pu is not None else None

    # --- Potência Reativa Mínima (q_min_pu) ---
    @property
    def q_min_pu(self) -> Optional[float]:
        return self.q_min_mvar / self.sb_mva if self.q_min_mvar is not None else None

    @q_min_pu.setter
    def q_min_pu(self, new_q_min_pu: Optional[float]):
        self.q_min_mvar = new_q_min_pu * self.sb_mva if new_q_min_pu is not None else None

    def __repr__(self):
        return (f"Generator(id={self.id}, bus={self.bus.id}, p_pu={self.p_pu:.3f}, q_pu={self.q_pu:.3f}, "
                f"p_range=[{self.p_min_pu:.3f},{self.p_max_pu:.3f}], q_range=[{self.q_min_pu},{self.q_max_pu}])")
