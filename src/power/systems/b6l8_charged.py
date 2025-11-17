from power.electricity_models import Network, Bus, BusType, Line, Load, ThermalGenerator, WindGenerator
class B6L8Charged(Network):
    """
    Classe para representar o sistema de 3 barras fornecido.
    """
    def __init__(self):
        super().__init__(name="B6L8")
        self.sb = 100
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()

        ThermalGenerator(id=1, bus=self.buses[0], p_mw=1, q_mvar=6.9, cost_b_mw=10, p_max_mw=50)
        ThermalGenerator(id=2, bus=self.buses[2], p_mw=0, q_mvar=0  , cost_b_mw=20, p_max_mw=70)
        ThermalGenerator(id=3, bus=self.buses[3], p_mw=0, q_mvar=0  , cost_b_mw=30, p_max_mw=60)
        WindGenerator(id=4, bus=self.buses[0], p_max_mw=70)
        WindGenerator(id=5, bus=self.buses[2], p_max_mw=70)
        WindGenerator(id=6, bus=self.buses[3], p_max_mw=70)

        Load(id=1, bus=self.buses[1], p_mw=2*20.0, q_mvar= 8.5, cost_shed_mw=400)
        Load(id=2, bus=self.buses[2], p_mw=2*40.0, q_mvar=17.0, cost_shed_mw=400)
        Load(id=3, bus=self.buses[3], p_mw=2*30.0, q_mvar= 4.0, cost_shed_mw=400)
        Load(id=4, bus=self.buses[4], p_mw=2*30.0, q_mvar=12.7, cost_shed_mw=400)
        Load(id=5, bus=self.buses[5], p_mw=2*40.0, q_mvar=17.3, cost_shed_mw=400)

    def _create_buses(self):
        """
        Cria as barras do sistema.
        Suposições:
        - Barra 1 é a barra de referência (Slack) por ser a primeira e ter um gerador.
        - Barras 2 e 3 são do tipo PV
        - Tensão inicial de 1.0 p.u. e ângulo 0.0 para todas as barras (exceto Slack que já tem ângulo 0).
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
        Nota: A matriz DGER define limites e custos, mas não a potência ativa inicial (p_mw).
        Os geradores são apenas alocados às barras.
        """
        ThermalGenerator(id=1, bus=self.buses[0], p_mw=1, q_mvar=6.9, cost_b_mw=10, p_max_mw=50)
        ThermalGenerator(id=2, bus=self.buses[2], p_mw=0, q_mvar=0  , cost_b_mw=20, p_max_mw=70)
        ThermalGenerator(id=3, bus=self.buses[3], p_mw=0, q_mvar=0  , cost_b_mw=30, p_max_mw=60)
        WindGenerator(id=4, bus=self.buses[0], p_max_mw=70)
        WindGenerator(id=5, bus=self.buses[2], p_max_mw=70)
        WindGenerator(id=6, bus=self.buses[3], p_max_mw=70)
    
    def _create_loads(self):
        Load(id=1, bus=self.buses[1], p_mw=2*20.0, q_mvar= 8.5, cost_shed_mw=400)
        Load(id=2, bus=self.buses[2], p_mw=2*40.0, q_mvar=17.0, cost_shed_mw=400)
        Load(id=3, bus=self.buses[3], p_mw=2*30.0, q_mvar= 4.0, cost_shed_mw=400)
        Load(id=4, bus=self.buses[4], p_mw=2*30.0, q_mvar=12.7, cost_shed_mw=400)
        Load(id=5, bus=self.buses[5], p_mw=2*40.0, q_mvar=17.3, cost_shed_mw=400)
