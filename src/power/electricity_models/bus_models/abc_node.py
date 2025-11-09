from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod

@dataclass 
class AbstractNode(ABC):
    "Define common elements with a power net injection"
    network: "Network"
    id: int
    name: Optional[str] = None

    @property
    def sb_mva(self) -> float:
        "Base Power in MVA"
        return self.network.sb_mva

    @property
    @abstractmethod
    def p_pu(self) -> float:
        """Net active power injection (pu)"""
        pass

    @property
    @abstractmethod
    def q_pu(self) -> float:
        """Net reactive power injection (pu)"""
        pass

    @property
    def p_mw(self) -> float:
        """Injeção líquida de potência ativa em MW."""
        return self.p_pu * self.sb_mva
    
    @property
    def q_mvar(self) -> float:
        """Injeção líquida de potência reativa em MVAr."""
        return self.q_pu * self.sb_mva