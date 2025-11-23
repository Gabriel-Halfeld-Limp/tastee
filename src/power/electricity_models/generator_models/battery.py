from dataclasses import dataclass
from typing import Optional
from src.power.electricity_models.generator_models.generator import Generator
from src.power.electricity_models.bus_models.bus import Bus

@dataclass
class Battery(Generator):
    capacity_mwh: float = 0.0  # Capacidade total da bateria em MWh
    soc_mwh:      float = 0.0  # Estado de carga atual em MWh
    efficiency_charge: float = 0.95  # Eficiência de carga
    efficiency_discharge: float = 0.95  # Eficiência de descarga
    max_charge_rate_mw: float = 0.0  # Taxa máxima de carga em MW
    max_discharge_rate_mw: float = 0.0  # Taxa máxima de descarga em MW
    cost_charge_mw: float = 0.0  # Custo de carga por MW
    cost_discharge_mw: float = 0.0  # Custo de descarga por MW


    def __post_init__(self):
        super().__post_init__()
        if self.soc_mwh > self.capacity_mwh:
            raise ValueError("Estado de carga (soc_mwh) não pode exceder a capacidade (capacity_mwh).")
        if self.name == f"Generator_{self.id}":
            self.name = f"Battery_{self.id}"
    
    # Capacity in per unit
    @property
    def capacity_pu(self) -> float:
        return self.capacity_mwh / self.capacity_mwh if self.capacity_mwh > 0 else 0.0

    @capacity_pu.setter
    def capacity_pu(self, new_capacity_pu: float):
        if new_capacity_pu < 0.0:
            raise ValueError("Capacidade em pu deve ser não negativa.")
        self.capacity_mwh = new_capacity_pu * self.capacity_mwh

    # --- Estado de Carga (soc_pu) ---
    @property
    def soc_pu(self) -> float:
        return self.soc_mwh / self.capacity_mwh if self.capacity_mwh > 0 else 0.0

    @soc_pu.setter
    def soc_pu(self, new_soc_pu: float):
        if not (0.0 <= new_soc_pu <= 1.0):
            raise ValueError("Estado de carga em pu deve estar entre 0 e 1.")
        self.soc_mwh = new_soc_pu * self.capacity_mwh

    # --- Custo de Carga (cost_charge_pu) ---
    @property
    def cost_charge_pu(self) -> float:
        return self.cost_charge_mw * self.sb_mva
    
    @cost_charge_pu.setter
    def cost_charge_pu(self, new_cost_charge_pu: float):
        self.cost_charge_mw = new_cost_charge_pu / self.sb_mva

    # --- Custo de Descarga (cost_discharge_pu) ---
    @property
    def cost_discharge_pu(self) -> float:
        return self.cost_discharge_mw * self.sb_mva
    
    @cost_discharge_pu.setter
    def cost_discharge_pu(self, new_cost_discharge_pu: float):  
        self.cost_discharge_mw = new_cost_discharge_pu / self.sb_mva
    
    #--- Max Taxa de Carga (max_charge_rate_pu) ---
    @property
    def max_charge_rate_pu(self) -> float:
        return self.max_charge_rate_mw / self.sb_mva
    
    @max_charge_rate_pu.setter
    def max_charge_rate_pu(self, new_max_charge_rate_pu: float):
        self.max_charge_rate_mw = new_max_charge_rate_pu * self.sb_mva
    
    #--- Max Taxa de Descarga (max_discharge_rate_pu) ---
    @property
    def max_discharge_rate_pu(self) -> float:
        return self.max_discharge_rate_mw / self.sb_mva
    
    @max_discharge_rate_pu.setter
    def max_discharge_rate_pu(self, new_max_discharge_rate_pu: float):
        self.max_discharge_rate_mw = new_max_discharge_rate_pu * self.sb_mva
    

    