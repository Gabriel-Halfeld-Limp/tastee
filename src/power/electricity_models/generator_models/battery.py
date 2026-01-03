from dataclasses import dataclass
from typing import Optional
from power.electricity_models.generator_models.generator import Generator

@dataclass
class Battery(Generator):
    capacity_mwh:         float = 0.0           # Energia total armazenável
    soc_mwh:              float = 0.0           # Estado de carga atual (energia) em MWh
    efficiency_charge:    float = 0.95     # Eficiência de carga
    efficiency_discharge: float = 0.95  # Eficiência de descarga
    cost_charge_mw:       float = -1       # Custo de carregar por MW (custo negativo indica pagamento para carregar)
    cost_discharge_mw:    float = 0.0      # Custo de descarregar por MW

    def __post_init__(self):
        super().__post_init__()
        if self.soc_mwh > self.capacity_mwh:
            raise ValueError("Estado de carga (soc_mwh) não pode exceder a capacidade (capacity_mwh).")
        # Renomeia se vier com nome default do Generator
        if self.name == f"Generator_{self.id}":
            self.name = f"Battery_{self.id}"

    # --- Capacidade em pu (assumindo base de energia = sb_mva * 1h) ---
    @property
    def capacity_pu(self) -> float:
        return self.capacity_mwh / self.sb_mva if self.sb_mva > 0 else 0.0

    @capacity_pu.setter
    def capacity_pu(self, new_capacity_pu: float):
        if new_capacity_pu < 0.0:
            raise ValueError("Capacidade em pu deve ser não negativa.")
        self.capacity_mwh = new_capacity_pu * self.sb_mva

    # --- Estado de Carga em pu ---
    @property
    def soc_pu(self) -> float:
        return self.soc_mwh / self.capacity_mwh if self.capacity_mwh > 0 else 0.0

    @soc_pu.setter
    def soc_pu(self, new_soc_pu: float):
        self.soc_mwh = new_soc_pu * self.capacity_mwh

    # --- Custos em pu ---
    @property
    def cost_charge_pu(self) -> float:
        return self.cost_charge_mw * self.sb_mva

    @cost_charge_pu.setter
    def cost_charge_pu(self, new_cost_charge_pu: float):
        self.cost_charge_mw = new_cost_charge_pu / self.sb_mva

    @property
    def cost_discharge_pu(self) -> float:
        return self.cost_discharge_mw * self.sb_mva

    @cost_discharge_pu.setter
    def cost_discharge_pu(self, new_cost_discharge_pu: float):
        self.cost_discharge_mw = new_cost_discharge_pu / self.sb_mva

    # --- Aliases para taxas de carga/descarga usando p_min/p_max ---
    @property
    def max_discharge_rate_mw(self) -> float:
        return self.p_max_mw

    @max_discharge_rate_mw.setter
    def max_discharge_rate_mw(self, value: float):
        self.p_max_mw = value

    @property
    def max_discharge_rate_pu(self) -> float:
        return self.p_max_pu

    @max_discharge_rate_pu.setter
    def max_discharge_rate_pu(self, value_pu: float):
        self.p_max_pu = value_pu

    @property
    def max_charge_rate_mw(self) -> float:
        # p_min_mw deve ser negativo para permitir carga; retornamos valor positivo
        return -self.p_min_mw if self.p_min_mw < 0 else 0.0

    @max_charge_rate_mw.setter
    def max_charge_rate_mw(self, value: float):
        if value < 0:
            raise ValueError("Taxa máxima de carga (MW) deve ser não negativa.")
        # Define p_min_mw como negativo do limite de carga
        self.p_min_mw = -value

    @property
    def max_charge_rate_pu(self) -> float:
        return self.max_charge_rate_mw / self.sb_mva

    @max_charge_rate_pu.setter
    def max_charge_rate_pu(self, value_pu: float):
        if value_pu < 0:
            raise ValueError("Taxa máxima de carga (pu) deve ser não negativa.")
        self.max_charge_rate_mw = value_pu * self.sb_mva


