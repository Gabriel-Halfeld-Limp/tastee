from .. import Network, Bus, Line, Generator, Load, WindGenerator, ThermalGenerator
class B3(Network):
    """
    Classe para representar o sistema de 3 barras fornecido.
    """
    def __init__(self):
        super().__init__(name="B3")
        self.sb = 100
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()


    def _create_buses(self):
        """
        Cria as barras do sistema.
        Suposições:
        - Barra 1 é a barra de referência (Slack) por ser a primeira e ter um gerador.
        - Barras 2 e 3 são do tipo PV
        - Tensão inicial de 1.0 p.u. e ângulo 0.0 para todas as barras (exceto Slack que já tem ângulo 0).
        """
        self.buses = [
            Bus(self, id=1, bus_type='Slack'),
            Bus(self, id=2),
            Bus(self, id=3),
        ]

    def _create_lines(self):
        """
        Cria as linhas de transmissão.
        Suposição: O valor 'cap' na matriz DLIN é a susceptância total da linha (B),
        portanto b_half = cap / 2. Os valores de R e X foram usados como fornecidos.
        """
        self.lines = [
            # Line(id, from, to, r, x, b_half)
            Line(id=1, from_bus=self.buses[0], to_bus=self.buses[1], r=0.10,  x=1  , flow_max=0.02), 
            Line(id=2, from_bus=self.buses[0], to_bus=self.buses[2], r=0.15,  x=1  , flow_max=0.10),  
            Line(id=3, from_bus=self.buses[1], to_bus=self.buses[2], r=0.05,  x=0.5, flow_max=0.10), 
        ]

    def _create_generators(self):
        """
        Cria os geradores do sistema.
        Nota: A matriz DGER define limites e custos, mas não a potência ativa inicial (p_input).
        Os geradores são apenas alocados às barras.
        """
        ThermalGenerator(id=1, bus=self.buses[0], cost_b_input=10, pb=self.sb, p_max_input=15),
        ThermalGenerator(id=2, bus=self.buses[1], cost_b_input=20, pb=self.sb, p_max_input=15),

    def _create_loads(self):
        """
        Cria as cargas do sistema.
        """
        Load(id=1, bus=self.buses[2], pb=self.sb, p_input=10.0, cost_shed_input=400)