from dataclasses import dataclass
from .generator import Generator

@dataclass
class SolarGenerator(Generator):
    """
    Representa um gerador eólico. Não possui custos de combustível.
    """

    def __post_init__(self):
        super().__post_init__()
        if self.name == f"Generator_{self.id}":
            self.name = f"SolarGenerator_{self.id}"
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