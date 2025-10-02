from .. import Network, Bus, Line, Generator, Load
class System3Bus(Network):
    """
    Classe para representar o sistema de 3 barras fornecido.
    """
    def __init__(self):
        super().__init__(name="Sistema de 3 Barras")
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()

    def _create_buses(self):
        """
        Cria as barras do sistema.
        Suposições:
        - Barra 1 é a barra de referência (Slack) por ser a primeira e ter um gerador.
        - Barras 2 e 3 são do tipo PV, pois possuem geradores conectados.
        - Tensão inicial de 1.0 p.u. e ângulo 0.0 para todas as barras (exceto Slack que já tem ângulo 0).
        """
        self.buses = [
            Bus(self, id=1, bus_type='Slack', v=1.0, theta=0.0),
            Bus(self, id=2, bus_type='PV',    v=1.0, theta=0.0),
            Bus(self, id=3, bus_type='PV',    v=1.0, theta=0.0),
        ]

    def _create_lines(self):
        """
        Cria as linhas de transmissão.
        Suposição: O valor 'cap' na matriz DLIN é a susceptância total da linha (B),
        portanto b_half = cap / 2. Os valores de R e X foram usados como fornecidos.
        """
        self.lines = [
            # Line(id, from, to, r, x, b_half)
            Line(id=1, from_bus=self.buses[0], to_bus=self.buses[1], r=10.0, x=100.0, b_half=1.0),  # cap=2 -> b_half=1
            Line(id=2, from_bus=self.buses[0], to_bus=self.buses[2], r=15.0, x=100.0, b_half=5.0),  # cap=10 -> b_half=5
            Line(id=3, from_bus=self.buses[1], to_bus=self.buses[2], r=5.0,  x=50.0,  b_half=5.0),  # cap=10 -> b_half=5
        ]

    def _create_generators(self):
        """
        Cria os geradores do sistema.
        Nota: A matriz DGER define limites e custos, mas não a potência ativa inicial (p_input).
        Os geradores são apenas alocados às barras.
        """
        self.generators = [
            Generator(id=1, bus=self.buses[0]),
            Generator(id=2, bus=self.buses[1]),
            Generator(id=3, bus=self.buses[2]),
        ]

    def _create_loads(self):
        """
        Cria as cargas do sistema.
        Suposição: A coluna 'carga' (valor 10.0) na matriz DBAR para a barra 3
        representa a carga reativa (q_input). A carga ativa (p_input) é considerada 0.
        """
        self.loads = [
            Load(id=1, bus=self.buses[2], pb=100, p_input=0.0, q_input=10.0),
        ]
