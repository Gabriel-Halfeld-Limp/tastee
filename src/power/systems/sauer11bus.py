from power.electricity_models import Network, Bus, BusType, Line, Load, ThermalGenerator

class Sauer11Bus(Network):
    def __init__(self):
        super().__init__(id=2, name="Sauer 11-bus System")
        self._create_buses()
        self._create_loads()
        self._create_generators()
        self._create_lines()
        
    def _create_buses(self):
        # Criar as barras
        Bus(self, id=1, btype=BusType.SLACK, v_pu=1.02, theta_deg=0.0, q_shunt_mvar=1)
        Bus(self, id=2, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=3, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=4, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=5, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=6, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=7, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=8, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=9, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=10, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)
        Bus(self, id=11, btype=BusType.PQ, v_pu=1.00, theta_deg=0.0)

        
    def _create_loads(self):
        # Criar as cargas
        Load(id=1, bus=self.buses[1],  pb=10.0, p_mw=3.720, q_mvar=0.830)  # Bus 2
        Load(id=2, bus=self.buses[2],  pb=10.0, p_mw=1.340, q_mvar=0.157)   # Bus 3
        Load(id=3, bus=self.buses[4],  pb=10.0, p_mw=-10.460, q_mvar=-1.116)  # Bus 5 (negative load to represent non controllable generation)
        Load(id=4, bus=self.buses[5],  pb=10.0, p_mw=3.700, q_mvar=0.122)   # Bus 6
        Load(id=5, bus=self.buses[6],  pb=10.0, p_mw=1.000, q_mvar=0.067)   # Bus 7
        Load(id=6, bus=self.buses[9],  pb=10.0, p_mw=1.370, q_mvar=0.041)     # Bus 10
        Load(id=7, bus=self.buses[10], pb=10.0, p_mw=-3.960, q_mvar=0.258)  # Bus 11(negative load to represent non controllable generation)
        
    def _create_generators(self):
        # Criar os geradores
        ThermalGenerator(id=1, bus=self.buses[0])      # Slack (bus 1)
        
    def _create_lines(self):
        # Criar as linhas
        Line(id=1,  from_bus=self.buses[0], to_bus=self.buses[2], r_pu=0.0015, x_pu=0.0212, shunt_half_pu=0.1920)
        Line(id=2,  from_bus=self.buses[0], to_bus=self.buses[2], r_pu=0.0016, x_pu=0.0242, shunt_half_pu=0.21315)
        Line(id=3,  from_bus=self.buses[1], to_bus=self.buses[2], r_pu=0.0034, x_pu=0.0496, shunt_half_pu=0.4130)
        Line(id=4,  from_bus=self.buses[2], to_bus=self.buses[3], r_pu=0.0023, x_pu=0.0333, shunt_half_pu=0.30115)
        Line(id=5,  from_bus=self.buses[3], to_bus=self.buses[5], r_pu=0.0011, x_pu=0.0152, shunt_half_pu=0.13685)
        Line(id=6,  from_bus=self.buses[3], to_bus=self.buses[5], r_pu=0.0008, x_pu=0.0262, shunt_half_pu=0.0)
        Line(id=7,  from_bus=self.buses[5], to_bus=self.buses[6], r_pu=0.0203, x_pu=0.1553, shunt_half_pu=0.0361)
        Line(id=8,  from_bus=self.buses[6], to_bus=self.buses[9], r_pu=0.0284, x_pu=0.1330, shunt_half_pu=0.0153)
        Line(id=9,  from_bus=self.buses[8], to_bus=self.buses[9], r_pu=0.0000, x_pu=0.0277, shunt_half_pu=0.0)
        Line(id=10, from_bus=self.buses[8], to_bus=self.buses[4], r_pu=0.0001, x_pu=0.0024, shunt_half_pu=0.02165)
        Line(id=11, from_bus=self.buses[6], to_bus=self.buses[7], r_pu=0.0000, x_pu=0.0277, shunt_half_pu=0.0)
        Line(id=12, from_bus=self.buses[7], to_bus=self.buses[10],r_pu=0.0014, x_pu=0.0142, shunt_half_pu=0.1329)
        Line(id=13, from_bus=self.buses[7], to_bus=self.buses[4], r_pu=0.0011, x_pu=0.0178, shunt_half_pu=0.0921)