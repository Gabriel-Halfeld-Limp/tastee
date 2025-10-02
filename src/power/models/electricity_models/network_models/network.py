import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional

from ..bus_models import Bus
from ..generator_models import Generator
from ..line_models import Line
from ..load_models import Load

@dataclass
class Network:
    id: Optional[int] = None
    name: Optional[str] = None
    buses: List[Bus] = field(default_factory=list)
    lines: List[Line] = field(default_factory=list)
    loads: List[Load] = field(default_factory=list)
    generators: List[Generator] = field(default_factory=list)

    @property
    def bus_idx(self) -> dict:
        """
        Returns a dictionary mapping bus IDs to their indices in the buses list.
        This is useful for quickly accessing buses by their ID.
        """
        return {bus.id: i for i, bus in enumerate(self.buses)}
    
    def y_bus(self) -> np.ndarray:
        """
        Returns the Y bus matrix of the network.
        """
        n = len(self.buses)
        ybus = np.zeros((n, n), dtype=complex)
        for line in self.lines: #Adiciona os elementos de admitância da linha
            for (i, j), y in line.get_admittance_elements(self.bus_idx):
                ybus[i, j] += y
        
        for i, bus in enumerate(self.buses):
            ybus[i, i] += bus.shunt
    
        return ybus
        
    def get_G(self):
        return self.y_bus().real
    
    def get_B(self):
        return self.y_bus().imag

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
        Converts the AC network to a DC network in place, by removing line resistance and shunt elements.
        """
        for branch in self.lines:
            branch.r = 0
            branch.b_half = 0
            branch.tap_ratio = 1
            branch.phase_shift = 0

        for bus in self.buses:
            if bus.bus_type != 'Slack':
                bus.Sh = 0  

        #self.buses[0].Sh = 0.1    

    def __repr__(self):
        return f"Network(id={self.id}, name={self.name})"
    
def main():
    # Create a network
    net = Network(id=1, name="Test Network")
    print(net)

if __name__ == "__main__":
    main()