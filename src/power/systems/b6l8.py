from .. import Network, Bus, Line, Generator, Load
class B6L8(Network):
    """
    Classe para representar o sistema de 3 barras fornecido.
    """
    def __init__(self):
        super().__init__(name="Sistema de 3 Barras")
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
        Bus(self, id=1, theta=   0.00, bus_type='Slack')
        Bus(self, id=2, theta=  -4.98)
        Bus(self, id=3, theta= -12.72, v=1.05)
        Bus(self, id=4, theta=   0.00)
        Bus(self, id=5, theta=  -4.98)
        Bus(self, id=6, theta= -12.72)

    def _create_lines(self):
        """
        Cria as linhas de transmissão.
        Suposição: O valor 'cap' na matriz DLIN é a susceptância total da linha (B),
        portanto b_half = cap / 2. Os valores de R e X foram usados como fornecidos.
        """
        Line(id=1, from_bus=self.buses[0], to_bus=self.buses[1], r=0.01, x=0.1 , flow_max=0.15) 
        Line(id=2, from_bus=self.buses[1], to_bus=self.buses[2], r=0.02, x=0.17, flow_max=0.15) 
        Line(id=3, from_bus=self.buses[2], to_bus=self.buses[3], r=0.05, x=0.10, flow_max=0.10) 
        Line(id=4, from_bus=self.buses[3], to_bus=self.buses[4], r=0.01, x=0.15, flow_max=0.25) 
        Line(id=5, from_bus=self.buses[4], to_bus=self.buses[5], r=0.02, x=0.18, flow_max=0.20) 
        Line(id=6, from_bus=self.buses[2], to_bus=self.buses[5], r=0.03, x=0.13, flow_max=0.30) 
        Line(id=7, from_bus=self.buses[0], to_bus=self.buses[4], r=0.01, x=0.14, flow_max=0.30) 
        Line(id=8, from_bus=self.buses[3], to_bus=self.buses[1], r=0.02, x=0.12, flow_max=0.20)


    def _create_generators(self):
        """
        Cria os geradores do sistema.
        Nota: A matriz DGER define limites e custos, mas não a potência ativa inicial (p_input).
        Os geradores são apenas alocados às barras.
        """

        Generator(id=1, pb=self.sb, bus=self.buses[0], p_input=1, q_input=6.9, cost_b_input=10, p_max_input=50)
        Generator(id=2, pb=self.sb, bus=self.buses[2], p_input=0, q_input=0  , cost_b_input=20, p_max_input=70)
        Generator(id=3, pb=self.sb, bus=self.buses[3], p_input=0, q_input=0  , cost_b_input=30, p_max_input=60)


        for index, bus_object in enumerate(self.buses):
            Generator(
                id=1001 + index,
                bus=bus_object,
                cost_b_input=400,
                pb=self.sb,
                p_max_input=99999,
                p_min_input=0
            )
    
    def _create_loads(self):
        Load(id=1, bus=self.buses[1], pb=self.sb, p_input=20.0, q_input= 8.5)
        Load(id=2, bus=self.buses[2], pb=self.sb, p_input=40.0, q_input=17.0)
        Load(id=3, bus=self.buses[3], pb=self.sb, p_input=30.0, q_input= 4.0)
        Load(id=4, bus=self.buses[4], pb=self.sb, p_input=30.0, q_input=12.7)
        Load(id=5, bus=self.buses[5], pb=self.sb, p_input=40.0, q_input=17.3)
