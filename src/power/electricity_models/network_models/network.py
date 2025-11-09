import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional
from power.electricity_models.generator_models import Generator, ThermalGenerator, WindGenerator, SolarGenerator, HydroGenerator
from power.electricity_models.line_models import Line
from power.electricity_models.load_models import Load
from power.electricity_models.bus_models import Bus

@dataclass
class Network:
    sb_mva:             float                  = 100
    id:                 Optional[int]          = None
    name:               Optional[str]          = None
    buses:              List[Bus]              = field(default_factory=list)
    lines:              List[Line]             = field(default_factory=list)
    loads:              List[Load]             = field(default_factory=list)
    generators:         List[Generator]        = field(default_factory=list)
    thermal_generators: List[ThermalGenerator] = field(default_factory=list)
    wind_generators:    List[WindGenerator]    = field(default_factory=list)
    solar_generators:   List[SolarGenerator]   = field(default_factory=list)
    hydro_generators:   List[HydroGenerator]   = field(default_factory=list)

    #Attributes for caching
    _ybus: Optional[np.ndarray] = field(default=None, init=False, repr=False)
    _zbus_ground: Optional[np.ndarray] = field(default=None, init=False, repr=False)
    def __post_init__(self):
        if self.name is None:
            if self.id is not None:
                self.name = f"Network_{self.id}"
            else:
                self.name = "Network"

    @property
    def bus_idx(self) -> dict:
        """
        Returns a dictionary mapping bus IDs to their indices in the buses list.
        This is useful for quickly accessing buses by their ID.
        """
        return {bus.id: i for i, bus in enumerate(self.buses)}
    
    @property
    def y_bus(self) -> np.ndarray:
        """Retorna a Matriz Ybus da rede (calculada apenas se necessário)."""
        if self._ybus is not None:
            return self._ybus
        
        n = len(self.buses)
        ybus = np.zeros((n, n), dtype=complex) # <-- Inicialização (ybus minúsculo)
        bus_idx = self.bus_idx
        
        # 1. Adicionar Elementos de Linha
        for line in self.lines:
            # Obtém os índices globais das barras de e para:
            i = bus_idx[line.from_bus.id] # 'from_bus' é a barra 'i'
            j = bus_idx[line.to_bus.id]   # 'to_bus' é a barra 'j'
            Y_elements = line.get_ybus_elements() 
            ybus[i, i] += Y_elements['Yff']
            ybus[i, j] += Y_elements['Yft']
            ybus[j, i] += Y_elements['Ytf']
            ybus[j, j] += Y_elements['Ytt']
        
        # 2. Adicionar Shunts de Barra
        for i, bus in enumerate(self.buses):
            ybus[i, i] += bus.shunt_pu 
            
        self._ybus = ybus
        return self._ybus
        
    @property
    def g_bus(self):
        """ Returns real part of Ybus."""
        return self.y_bus.real
    
    @property
    def b_bus(self):
        """ Returns imaginary part of Ybus."""
        return self.y_bus.imag
    
    def add_generator(self, generator: Generator):
        if generator not in self.generators:
            self.generators.append(generator)
            if isinstance(generator, ThermalGenerator):
                self.thermal_generators.append(generator)
            elif isinstance(generator, WindGenerator):
                self.wind_generators.append(generator)
            elif isinstance(generator, HydroGenerator):
                self.hydro_generators.append(generator)
            elif isinstance(generator, SolarGenerator):
                self.solar_generators.append(generator)
    
    def _reset_matrices(self):
        """Invalida as matrizes Y/Z para forçar o recálculo após uma alteração na rede."""
        self._ybus = None
        self._zbus_ground = None

    def get_Z_bus(self, ref_bus: Optional[Bus] = None) -> np.ndarray:
        """
        Returns the Z bus matrix of the network.
        Args:
            ref_bus (Bus, optional): The bus to reference the Z bus matrix to. If None, the Z bus is not referenced.
        Returns:
            Z_bus (np.ndarray): The Z bus matrix of the network.
        """
        Z = np.linalg.inv(self.y_bus())
        if ref_bus is None:
            return Z
        
        if ref_bus.id not in self.bus_idx:
            raise ValueError(f"Bus {ref_bus.id} is not part of the network.")
        s = self.bus_idx[ref_bus.id]
        Zs = (Z - Z[:, [s]] - Z[[s], :] + Z[s, s])
        return Zs
    
    def get_Z_bus_arb_tie(self, ref_bus: Bus, z_tie: complex) -> np.ndarray:
        """
        Returns the Z bus matrix of the network with an arbitrary tie line.
        Args:
            ref_bus (Bus): The bus to reference the Z bus matrix to.
            z_tie (complex): The impedance of the tie line.
        Returns:
            Z_bus (np.ndarray): The Z bus matrix of the network with the tie line.
        """

        # Ground referenced Z bus
        Z = self.get_Z_bus()

        if ref_bus.id not in self.bus_idx:
            raise ValueError(f"Bus {ref_bus.id} is not part of the network.")
        
        s = self.bus_idx[ref_bus.id]

        #Denominator:
        denom = Z[s, s] + z_tie
        if denom == 0:
            raise ValueError("The denominator for the Z bus with tie line is zero, check the impedance values.")
        
        Z_tie = Z - np.outer(Z[:, s], Z[s, :]) / denom
        
        return Z_tie
    
    def CTDF(self, ref_bus: Optional[Bus] = None, z_tie: Optional[complex] = None) -> np.ndarray:
        """
        Current Transfer Distribution Factors (CTDF) for the network.
        Args:
            ref_bus (Bus, optional): The bus to reference the CTDF to. If None, the CTDF is not referenced.
            z_tie (complex, optional): The impedance of a tie line. If None, no tie line is considered.
        """
        if ref_bus is None:
            Zbus = self.get_Z_bus()
        elif z_tie is None:
            Zbus = self.get_Z_bus(ref_bus)
        else:
            Zbus = self.get_Z_bus_arb_tie(ref_bus, z_tie)

        CTDF = np.array([line.get_dfactors(Zbus, self.bus_idx) for line in self.lines])
        return CTDF

    def ACtoDC(self):
        """
        Converts the AC network to a DC network in place, by removing line r_pu and shunt elements.
        """
        for branch in self.lines:
            branch.r_pu = 0
            branch.shunt_half_pu = 0
            branch.tap_ratio = 1
            branch.tap_phase_deg = 0

        for bus in self.buses:
            bus.q_shunt_mvar = 0 

    def __repr__(self):
        return f"Network(name={self.name})"
    
def main():
    net = Network(id=1, name="Test Network")
    print(net)

if __name__ == "__main__":
    main()