from dataclasses import dataclass
from .generator import Generator

@dataclass
class WindGenerator(Generator):
    """
    Representa um gerador eólico. Não possui custos de combustível.
    """

    def __post_init__(self):
        super().__post_init__()

    @property
    def cost_a(self) -> float:
        return 0.0

    @property
    def cost_b(self) -> float:
        return 0.0

    @property
    def cost_c(self) -> float:
        return 0.0

    def __repr__(self):
        base_repr = super().__repr__()
        return f"Wind{base_repr}"