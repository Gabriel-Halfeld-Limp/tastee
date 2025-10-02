import math
from .. import Network, Bus, Line, Generator, Load

class SystemB7L8(Network):
    """
    Classe para representar o sistema de teste de 7 barras.
    """
    def __init__(self):
        super().__init__(name="Sistema de 7 Barras")
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()

    def _create_buses(self):
        """
        Cria as barras do sistema a partir da matriz DBAR.
        - Tipo 2 -> 'Slack', Tipo 1 -> 'PV', Tipo 0 -> 'PQ'.
        - Ângulos foram convertidos de graus para radianos.
        """
        bus_type_map = {0: 'PQ', 1: 'PV', 2: 'Slack'}
        
        # Dados da matriz DBAR: [NB, T, G, VT, Angle, ..., QBAR]
        bus_data = [
            [1, 2, 1, 1.0,   0.0,    1.0, 6.9, -9999, 9999.0, 0.0,  0.0,  0.0],
            [2, 0, 0, 1.0,  -4.98,   0.0, 0.0,   0.0,    0.0, 20.0, 8.5,  0.0],
            [3, 1, 1, 1.0,  -12.72,  0.0, 0.0, -200.0, 250.0, 40.0, 17.0, 0.0],
            [4, 1, 1, 1.0,   0.0,    0.0, 0.0, -200.0, 250.0, 30.0, 4.0,  0.0],
            [5, 0, 0, 1.0,  -4.98,   0.0, 0.0,   0.0,    0.0, 30.0, 12.7, 0.0],
            [6, 0, 0, 1.0,  -10.72,  0.0, 0.0,   0.0,    0.0, 40.0, 17.3, 0.0],
            [7, 0, 0, 1.0,  -12.72,  0.0, 0.0,   0.0,    0.0, 5.0,  1.3,  0.0]
        ]

        self.buses = []
        for row in bus_data:
            self.buses.append(
                Bus(self, 
                    id=int(row[0]), 
                    bus_type=bus_type_map[int(row[1])], 
                    v=float(row[3]), 
                    theta=math.radians(float(row[4])),
                    Sh=float(row[11])
                )
            )

    def _create_lines(self):
        """
        Cria as linhas de transmissão a partir da matriz DLIN.
        """
        # Dados da matriz DLIN: [From, T0, r, x, Bsh]
        line_data = [
            [1, 2, 1, 10, 0.0],
            [2, 3, 2, 17, 0.0],
            [3, 4, 5, 10, 0.0],
            [4, 5, 1, 15, 0.0],
            [5, 6, 2, 18, 0.0],
            [3, 6, 3, 13, 0.0],
            [1, 5, 1, 14, 0.0],
            [5, 7, 2, 13, 0.0],
            [4, 2, 2, 12, 0.0]
        ]
        
        self.lines = []
        for i, row in enumerate(line_data):
            from_bus_id = int(row[0])
            to_bus_id = int(row[1])
            self.lines.append(
                Line(id=i + 1,
                     from_bus=self.buses[from_bus_id - 1],
                     to_bus=self.buses[to_bus_id - 1],
                     r=float(row[2]),
                     x=float(row[3]),
                     b_half=float(row[4]) / 2.0
                )
            )

    def _create_generators(self):
        """
        Cria os geradores a partir da matriz DBAR (onde a coluna G=1).
        """
        # Dados da matriz DBAR: [NB, T, G, ..., PG, ...]
        bus_data = [
            [1, 2, 1, 1.0,   0.0,    1.0],
            [2, 0, 0, 1.0,  -4.98,   0.0],
            [3, 1, 1, 1.0,  -12.72,  0.0],
            [4, 1, 1, 1.0,   0.0,    0.0],
            [5, 0, 0, 1.0,  -4.98,   0.0],
            [6, 0, 0, 1.0,  -10.72,  0.0],
            [7, 0, 0, 1.0,  -12.72,  0.0]
        ]

        self.generators = []
        gen_id = 1
        for row in bus_data:
            # Apenas cria gerador se o indicador G (índice 2) for 1
            if int(row[2]) == 1:
                bus_id = int(row[0])
                p_gen = float(row[5])
                
                self.generators.append(
                    Generator(id=gen_id, 
                              bus=self.buses[bus_id - 1], 
                              pb=100,
                              p_input=p_gen)
                )
                gen_id += 1

    def _create_loads(self):
        """
        Cria as cargas a partir das colunas PLOAD e QLOAD da matriz DBAR.
        """
        # Dados da matriz DBAR: [NB, ..., PLOAD, QLOAD]
        bus_data = [
            [1, 0.0, 0.0],
            [2, 20.0, 8.5],
            [3, 40.0, 17.0],
            [4, 30.0, 4.0],
            [5, 30.0, 12.7],
            [6, 40.0, 17.3],
            [7, 5.0,  1.3]
        ]
        
        self.loads = []
        load_id = 1
        for row in bus_data:
            p_load = float(row[1])
            q_load = float(row[2])
            
            if p_load > 0 or q_load > 0:
                bus_id = int(row[0])
                self.loads.append(
                    Load(id=load_id,
                         bus=self.buses[bus_id - 1],
                         pb=100,
                         p_input=p_load,
                         q_input=q_load
                    )
                )
                load_id += 1