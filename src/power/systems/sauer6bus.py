from power.electricity_models import Network, Bus, BusType, Line, Load, ThermalGenerator

class Sauer6Bus(Network):
    """
    Class to represent the Sauer 6 bus system.
    """
    def __init__(self):
        super().__init__(name="Sauer 6 Bus System")
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()

    def _create_buses(self):
        """
        Creates the buses for the Sauer 6 bus system.
        """
        Bus(self, id=1, btype=BusType.SLACK, v_pu=1.05, theta_deg=0.0, q_shunt_mvar=1)
        Bus(self, id=2, btype=BusType.PV, v_pu=1.10, theta_deg=0.0)
        Bus(self, id=3, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=4, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=5, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=6, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)


    def _create_lines(self):
        """
        Creates the lines for the Sauer 6 bus system.
        """
        Line(id=1,  from_bus=self.buses[0], to_bus=self.buses[3], r_pu=0.080, x_pu=0.370, shunt_half_pu=0.00014)
        Line(id=2,  from_bus=self.buses[0], to_bus=self.buses[5], r_pu=0.123, x_pu=0.518, shunt_half_pu=0.00021)
        Line(id=3,  from_bus=self.buses[1], to_bus=self.buses[2], r_pu=0.723, x_pu=1.050, shunt_half_pu=0.0)
        Line(id=4,  from_bus=self.buses[1], to_bus=self.buses[4], r_pu=0.282, x_pu=0.640, shunt_half_pu=0.0)
        Line(id=5,  from_bus=self.buses[3], to_bus=self.buses[5], r_pu=0.097, x_pu=0.407, shunt_half_pu=0.00015)
        Line(id=6,  from_bus=self.buses[3], to_bus=self.buses[2], r_pu=0.000, x_pu=0.266, shunt_half_pu=0.0, tap_ratio=1.025)
        Line(id=7,  from_bus=self.buses[3], to_bus=self.buses[2], r_pu=0.000, x_pu=0.266, shunt_half_pu=0.0, tap_ratio=1.025)
        Line(id=8,  from_bus=self.buses[5], to_bus=self.buses[4], r_pu=0.000, x_pu=0.428, shunt_half_pu=0.0, tap_ratio=1.1)
        Line(id=9,  from_bus=self.buses[5], to_bus=self.buses[4], r_pu=0.000, x_pu=1.000, shunt_half_pu=0.0, tap_ratio=1.1)

    def _create_generators(self):
        # Criar os geradores
        ThermalGenerator(id=1, bus=self.buses[0], pb=1.0)    # Slack (bus 1)
        ThermalGenerator(id=2, bus=self.buses[1], pb=1.0, p_mw=0.500)    # PV
    
    def _create_loads(self):
        # Criar as cargas
        Load(id=1, bus=self.buses[2], pb=1.0, p_mw=0.550, q_mvar=0.130)  # Bus 3
        Load(id=2, bus=self.buses[4], pb=1.0, p_mw=0.300, q_mvar=0.180)  # Bus 5
        Load(id=3, bus=self.buses[5], pb=1.0, p_mw=0.500, q_mvar=0.050)   # Bus 6