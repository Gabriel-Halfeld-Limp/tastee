from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from power.electricity_models.generator_models.generator import Generator

# from power.hydraulic_models.node_models.hydro_node import HydroBus


@dataclass
class HydroGenerator(Generator):
    """
    Representa um gerador hidráulico. Conectado a um nó elétrico e hidráulico.
    """
    hydro_bus: Optional['HydroBus'] = None
    # Atributos Físicos do Reservatório e Máquina   
    vol_min: float = 0.0         # Volume Mínimo (hm3)
    vol_max: float = 0.0         # Volume Máximo (hm3) - Se 0, é fio d'água
    prod: float = 1.0            # Produtibilidade (MW / m3/s)
    engolimento_max: float = 10000.0  # Engolimento máximo (m3/s)

    def __post_init__(self):
        if self.hydro_bus is None:
            raise ValueError(f"hydro_bus must be provided for HydroGenerator{self.id}.")
    
        if self.name is None:
            self.name = f"HydroGenerator_{self.id}"

        super().__post_init__()
        self.hydro_bus.add_generator(self)
        self.hydro_network = self.hydro_bus.hydro_network
        self.hydro_network.add_generator(self)

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
        return f"Hydro{base_repr}"