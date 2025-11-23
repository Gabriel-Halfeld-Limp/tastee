from power.electricity_models import Network, Bus, BusType, Line, Load, WindGenerator, Battery, ThermalGenerator

class B6L8EOLIC_BESS(Network):
    """
    Classe para representar o sistema de 6 barras com eólica e BESS.
    """
    def __init__(self):
        super().__init__(name="B6L8_EOLIC_BESS")
        self.sb = 100
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()

    def _create_buses(self):
        """
        Cria as barras do sistema.
        Suposições:,
        - Barra 1 é a barra de referência (Slack), por ser a primeira e ter um gerador.
        - Barras 2 ,e 3 são do tipo PV,
        - Tensão inicial de 1.0 p.u. e ângulo 0.0,, para todas as barras (exceto Slack que já tem ângulo 0).
        """
        Bus(self, id=1, theta_deg=   0.00, btype=BusType.SLACK)
        Bus(self, id=2, theta_deg=  -4.98)
        Bus(self, id=3, theta_deg= -12.72, v_pu=1.05)
        Bus(self, id=4, theta_deg=   0.00)
        Bus(self, id=5, theta_deg=  -4.98)
        Bus(self, id=6, theta_deg= -12.72)

    def _create_lines(self):
        """
        Cria as linhas de transmissão.
        Suposição: O valor 'cap' na matriz DLIN é a susceptância total da linha (B),
        portanto shunt_half_pu = cap / 2. Os valores de R e X foram usados como fornecidos.
        """
        Line(id=1, from_bus=self.buses[0], to_bus=self.buses[1], r_pu=0.01, x_pu=0.1 , flow_max_pu=0.15) 
        Line(id=2, from_bus=self.buses[1], to_bus=self.buses[2], r_pu=0.02, x_pu=0.17, flow_max_pu=0.15) 
        Line(id=3, from_bus=self.buses[2], to_bus=self.buses[3], r_pu=0.05, x_pu=0.10, flow_max_pu=0.10) 
        Line(id=4, from_bus=self.buses[3], to_bus=self.buses[4], r_pu=0.01, x_pu=0.15, flow_max_pu=0.25) 
        Line(id=5, from_bus=self.buses[4], to_bus=self.buses[5], r_pu=0.02, x_pu=0.18, flow_max_pu=0.20) 
        Line(id=6, from_bus=self.buses[2], to_bus=self.buses[5], r_pu=0.03, x_pu=0.13, flow_max_pu=0.30) 
        Line(id=7, from_bus=self.buses[0], to_bus=self.buses[4], r_pu=0.01, x_pu=0.14, flow_max_pu=0.30) 
        Line(id=8, from_bus=self.buses[3], to_bus=self.buses[1], r_pu=0.02, x_pu=0.12, flow_max_pu=0.20)

    def _create_generators(self):
        """
        Cria os geradores do sistema.
        """
        ThermalGenerator(id=1, bus=self.buses[0], p_mw=1, q_mvar=6.9, cost_b_mw=10, p_max_mw=50)
        ThermalGenerator(id=2, bus=self.buses[2], p_mw=0, q_mvar=0  , cost_b_mw=20, p_max_mw=70)
        ThermalGenerator(id=3, bus=self.buses[3], p_mw=0, q_mvar=0  , cost_b_mw=30, p_max_mw=60)

        WindGenerator(id=4, bus=self.buses[0], p_max_mw=50)
        WindGenerator(id=5, bus=self.buses[2], p_max_mw=70)
        WindGenerator(id=6, bus=self.buses[3], p_max_mw=60)

        Battery(id=7, bus=self.buses[1], capacity_mwh=20.0, soc_mwh=10.0, max_charge_rate_mw=5.0,
                max_discharge_rate_mw=5.0, cost_charge_mw=2.0, cost_discharge_mw=3.0)
        
        