from dataclasses import dataclass, field
from .generator import Generator

@dataclass
class WindGenerator(Generator):
    """
    Representa um gerador eólico.
    Herda da classe Generator, mas com custo marginal de geração zero.
    Sua potência máxima (p_max) é variável e representa a potência 
    disponível do vento em um determinado cenário.
    """
    # Sobrescreve os valores padrão dos custos para serem zero
    cost_a_input: float = 0.0
    cost_b_input: float = 0.0
    cost_c_input: float = 0.0

    def __post_init__(self):
        # Chama o __post_init__ da classe pai (Generator) para garantir
        # que o gerador seja adicionado ao barramento e à rede.
        super().__post_init__()

    def __repr__(self):
        # Reutiliza a representação da classe pai, mas muda o nome para clareza
        base_repr = super().__repr__()
        return f"Wind{base_repr}"

