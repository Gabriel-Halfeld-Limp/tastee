from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class ABCHydroNode(ABC):
    """Abstract base class for a hydraulic node."""
    hydro_network: "Network"
    id: int
    name: Optional[str] = None
