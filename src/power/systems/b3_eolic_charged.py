from power.electricity_models import Network, Bus, Line, BusType, Load, WindGenerator, ThermalGenerator
class B3EOLCharged(Network):
    """
    Classe para representar o sistema de 3 barras fornecido.
    """
    def __init__(self):
        super().__init__(name="B3_EOLIC")
        self.sb = 100
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()
        self.mvu = 0.2
        self.mvd = 0.2

    def _create_buses(self):
        """
        Cria as barras do sistema.
        Suposições:
        - Barra 1 é a barra de referência (Slack) por ser a primeira e ter um gerador.
        - Barras 2 e 3 são do tipo PV
        - Tensão inicial de 1.0 p.u. e ângulo 0.0 para todas as barras (exceto Slack que já tem ângulo 0).
        """
        Bus(self, id=1, btype=BusType.SLACK)
        Bus(self, id=2)
        Bus(self, id=3)

    def _create_lines(self):
        """
        Cria as linhas de transmissão.
        Suposição: O valor 'cap' na matriz DLIN é a susceptância total da linha (B),
        portanto shunt_half_pu = cap / 2. Os valores de R e X foram usados como fornecidos.
        """
        Line(id=1, from_bus=self.buses[0], to_bus=self.buses[1], r_pu=0.10,  x_pu=1  , flow_max_pu=0.02)
        Line(id=2, from_bus=self.buses[0], to_bus=self.buses[2], r_pu=0.15,  x_pu=1  , flow_max_pu=0.10)
        Line(id=3, from_bus=self.buses[1], to_bus=self.buses[2], r_pu=0.05,  x_pu=0.5, flow_max_pu=0.10)

    def _create_generators(self):
        """
        Cria os geradores do sistema.
        """
        WindGenerator(id=1, bus=self.buses[0], p_max_mw=30, q_max_mvar=15)
        ThermalGenerator(id=2, bus=self.buses[1], cost_b_mw=20, p_max_mw=30, q_max_mvar=15)

    def _create_loads(self):
        """
        Cria as cargas do sistema.
        """
        Load(id=1, bus=self.buses[2], p_mw=20.0, q_mvar=10.0, cost_shed_mw=400)