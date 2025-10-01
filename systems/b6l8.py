import math
from power.models.electricity_models import *

class SystemB6L8(Network):
    """
    Classe para representar o sistema de teste de 6 barras.
    """
    def __init__(self):
        super().__init__(name="Sistema de 6 Barras")
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
        # Mapeamento de tipo de barra
        bus_type_map = {0: 'PQ', 1: 'PV', 2: 'Slack'}
        
        # Dados da matriz DBAR: [NB, T, G, VT, Angle, PG, QG, QMIN, QMAX, PLOAD, QLOAD, QBAR]
        # Índices:             0   1  2   3      4    5   6     7     8      9      10     11
        bus_data = [
            [1, 2, 1, 1.0,   0.0,    1.0, 6.9, -9999, 9999.0, 0.0,  0.0,  0.0],
            [2, 0, 0, 1.0,  -4.98,   0.0, 0.0,   0.0,    0.0, 20.0, 8.5,  0.0],
            [3, 1, 1, 1.05, -12.72,  0.0, 0.0, -200.0, 250.0, 40.0, 17.0, 0.0],
            [4, 1, 1, 1.0,   0.0,    0.0, 0.0, -200.0, 250.0, 30.0, 4.0,  0.0],
            [5, 0, 0, 1.0,  -4.98,   0.0, 0.0,   0.0,    0.0, 30.0, 12.7, 0.0],
            [6, 0, 0, 1.0,  -12.72,  0.0, 0.0,   0.0,    0.0, 40.0, 17.3, 0.0]
        ]

        self.buses = []
        for row in bus_data:
            bus_id = int(row[0])
            bus_type_code = int(row[1])
            voltage = row[3]
            angle_deg = row[4]
            shunt_sh = row[11] # QBAR

            self.buses.append(
                Bus(self, 
                    id=bus_id, 
                    bus_type=bus_type_map[bus_type_code], 
                    v=voltage, 
                    theta=math.radians(angle_deg),
                    Sh=shunt_sh
                )
            )

    def _create_lines(self):
        """
        Cria as linhas de transmissão a partir da matriz DLIN.
        """
        # Dados da matriz DLIN: [From, T0, r, x, Bsh, ...]
        # Índices:                0    1   2  3    4
        line_data = [
            [1, 2, 1, 10, 0.0],
            [2, 3, 2, 17, 0.0],
            [3, 4, 5, 10, 0.0],
            [4, 5, 1, 15, 0.0],
            [5, 6, 2, 18, 0.0],
            [3, 6, 3, 13, 0.0],
            [1, 5, 1, 14, 0.0],
            [4, 2, 2, 12, 0.0]
        ]
        
        self.lines = []
        for i, row in enumerate(line_data):
            from_bus_id = int(row[0])
            to_bus_id = int(row[1])
            r = float(row[2])
            x = float(row[3])
            b_half = float(row[4]) / 2.0 # Bsh é a susceptância total, b_half é a metade

            self.lines.append(
                Line(id=i + 1,
                     from_bus=self.buses[from_bus_id - 1],
                     to_bus=self.buses[to_bus_id - 1],
                     r=r,
                     x=x,
                     b_half=b_half
                )
            )

    def _create_generators(self):
        """
        Cria os geradores a partir da matriz DBAR (onde G=1).
        A potência ativa (p_input) é retirada da coluna PG.
        """
        # [NB, T, G, VT, Angle, PG, ...]
        bus_data = [
            [1, 2, 1, 1.0, 0.0, 1.0],
            [3, 1, 1, 1.05, -12.72, 0.0],
            [4, 1, 1, 1.0, 0.0, 0.0]
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
                              pb=100, # Base de potência assumida
                              p_input=p_gen)
                )
                gen_id += 1

    def _create_loads(self):
        """
        Cria as cargas a partir das colunas PLOAD e QLOAD da matriz DBAR.
        """
        # [NB, ..., PLOAD, QLOAD]
        # Índices: 0        9      10
        bus_data = [
            [1, 0.0, 0.0],
            [2, 20.0, 8.5],
            [3, 40.0, 17.0],
            [4, 30.0, 4.0],
            [5, 30.0, 12.7],
            [6, 40.0, 17.3]
        ]
        
        self.loads = []
        load_id = 1
        for row in bus_data:
            p_load = float(row[1])
            q_load = float(row[2])
            
            # Apenas cria a carga se houver consumo (P ou Q > 0)
            if p_load > 0 or q_load > 0:
                bus_id = int(row[0])
                self.loads.append(
                    Load(id=load_id,
                         bus=self.buses[bus_id - 1],
                         pb=100, # Base de potência assum