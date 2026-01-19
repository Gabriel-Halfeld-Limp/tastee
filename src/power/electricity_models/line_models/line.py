import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict
from power.electricity_models.bus_models import Bus

@dataclass
class Line:
    from_bus:      Bus
    to_bus:        Bus
    id:            int
    name:          Optional[str] = None
    r_pu:          float = 0.0
    x_pu:          float = 0.01
    shunt_half_pu: float = 0.0
    flow_max_pu:   float = 999999.0
    flow_min_pu:   float = -999999.0
    tap_ratio:     float = 1.0
    tap_phase_deg: float = 0.0
    # Properties to hold flow current states
    p_flow_out_pu:  float = 0.0
    p_flow_in_pu:   float = 0.0
    q_flow_out_pu:  float = 0.0
    q_flow_in_pu:   float = 0.0


    def __post_init__(self):
        if self.name is None:
            self.name = f"Line_{self.id}"
        else:
            self.name = str(self.name)

        if self.from_bus.network != self.to_bus.network:
            raise ValueError("Both buses must belong to the same network.")
        
        self.network = self.from_bus.network #Add network to line
        self.network.lines.append(self) #Add line to network
        self.sb_mva = self.network.sb_mva

    @property
    def z_pu(self) -> complex:
        """Impedância da linha (pu)"""
        return complex(self.r_pu, self.x_pu)

    @property
    def y_pu(self) -> complex:
        """Admitância da linha (pu)"""
        return 1 / self.z_pu if self.z_pu != 0 else 0

    @property
    def tap_phase_rad(self) -> float:
        """Fase de tap em radianos"""
        return np.deg2rad(self.tap_phase_deg)
    
    @property
    def line_loss_pu(self) -> float:
        """Calcula a perda de potência ativa na linha (pu)"""
        return self.p_flow_out_pu + self.p_flow_in_pu
    
    def get_ybus_elements(self):
        """Gera os elementos de admitância baseados nos parâmetros da linha"""
        y = self.y_pu
        b = self.shunt_half_pu * 1j
        a = self.tap_ratio * np.exp(1j * self.tap_phase_rad)
        if self.tap_ratio != 1.0 or self.tap_phase_deg != 0.0:
            Yff = y / (a * np.conj(a)) + b
            Yft = -y / np.conj(a)
            Ytf = -y / a
            Ytt = y + b
        else:
            Yff = y + b
            Yft = -y
            Ytf = -y
            Ytt = y + b
        return {'Yff': Yff, 'Yft': Yft, 'Ytf': Ytf, 'Ytt': Ytt}

    def get_dfactors(self, Zbus: np.ndarray, bus_index: Dict[str, int]) -> np.ndarray:
        """
        Calculates the Current Distribution Factors (T_factors) for this line,
        referenced to the ground bus.

        The factor T_line_k for each bus k indicates the contribution of the current
        injected at bus k to the current flowing through this line.

        Args:
            Zbus (np.ndarray): The bus z_pu matrix (size n x_ohms n).
            bus_index (Dict[str, int]): Mapping of bus IDs to their indices in Zbus.

        Returns:
            np.ndarray: A 1D array of complex numbers, size n (number of buses),
                        representing the distribution factors T_line_k.
        """
        i = bus_index[self.from_bus.id]
        j = bus_index[self.to_bus.id]
        z_pu = self.z_pu

        if z_pu == 0:
            raise ZeroDivisionError(f"z_pu of {self.name} is zero!")

        T_line = (Zbus[i, :] - Zbus[j, :]) / z_pu
        return T_line

    def __repr__(self):
        return (f"Line(id={self.name}, From:{self.from_bus.id}, To:{self.to_bus.id}, "
                f"r={self.r_pu:.4f}, x={self.x_pu:.4f}, "
                f"FlowP_Out={self.p_flow_out_pu:.3f}, FlowP_In={self.p_flow_in_pu:.3f})")