from power.electricity_models import Network, Bus, BusType, Line, Load, ThermalGenerator


class Test2Bus(Network):
    def __init__(self):
        super().__init__(id=1, name="Simple 2-Bus System")
        self._create_buses()
        self._create_loads()
        self._create_generators()
        self._create_lines()

    def _create_buses(self):
        # Create buses
        Bus(self, id=1, btype=BusType.SLACK, v_pu=1.00, theta_deg=0.0, q_shunt_mvar=1)
        Bus(self, id=2, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)

    def _create_loads(self):
        # Create loads
        Load(id=1, bus=self.buses[1], p_mw=0.5, q_mvar=0)  # Bus 2

    def _create_generators(self):
        # Create generators
        ThermalGenerator(id=1, bus=self.buses[0])  # Slack (bus 1)

    def _create_lines(self):
        # Create lines
        Line(id=1, from_bus=self.buses[0], to_bus=self.buses[1], r_pu=0.0, x_pu=0.1)

