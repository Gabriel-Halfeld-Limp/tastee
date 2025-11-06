from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import List
from enum import Enum
import cmath
from power.electricity_models.bus_models.abc_node import AbstractNode

class BusType(Enum):
    SLACK = "SLACK"
    PQ = "PQ"
    PV = "PV"

@dataclass
class Bus(AbstractNode):
    """
    Representa uma barra (Bus) em um sistema de potência.
    
    Os valores de entrada são em unidades físicas (MW, MVAr, MVA, graus)
    e são convertidos para 'per unit' (pu) através de propriedades
    para uso em cálculos. Apenas tensão o valor de entrada já é pu
    """
    
    # --- Atributos Principais de Entrada ---
    btype: BusType = BusType.PQ
    v_pu: float = 1.0        # Tensão (magnitude) em p.u.
    theta_deg: float = 0.0   # Ângulo: Armazenamos em 'graus' (degrees) por ser mais intuitivo.
    q_shunt_mvar: float = 0.0   # Potência reativa do shunt em MVAr (a 1.0 pu V)

    loads:              List["Load"]             = field(default_factory=list, repr=False)
    generators:         List["Generator"]        = field(default_factory=list, repr=False)
    thermal_generators: List["ThermalGenerator"] = field(default_factory=list)
    wind_generators:    List["WindGenerator"]    = field(default_factory=list)
    solar_generators:   List["SolarGenerator"]   = field(default_factory=list)
    hydro_generators:   List["HydroGenerator"]   = field(default_factory=list)

    def __post_init__(self):
        if self.name is None:
            self.name = f"Bus_{self.id}"
        self.network.buses.append(self) #Add this bus to network's buses list
    
    @property
    def theta_rad(self) -> float:
        return np.deg2rad(self.theta_deg)
    
    @theta_rad.setter
    def theta_rad(self, value: float):
        self.theta_deg = np.rad2deg(value)

    @property
    def v_complex(self) -> complex:
        return cmath.rect(self.v_pu, self.theta_rad)
    
    @property
    def shunt_pu(self) -> complex:
        return self.q_shunt_mvar * 1j / self.sb_mva
    
    @property
    def p_pu(self) -> float:
        """Net active power injection (pu)"""
        return sum(g.p_pu for g in self.generators) - sum(l.p_pu for l in self.loads)

    @property
    def q_pu(self) -> float:
        """Net reactive power injection (pu)"""
        return sum(g.q_pu for g in self.generators) - sum(l.q_pu for l in self.loads) 
    
    def add_generator(self, generator: 'Generator'):
        "Add a generator to this bus"
        if generator not in self.generators:
            self.generators.append(generator)
            # Verifica o nome da classe como string
            class_name = generator.__class__.__name__
            if class_name == 'ThermalGenerator':
                self.thermal_generators.append(generator)
            elif class_name == 'WindGenerator':
                self.wind_generators.append(generator)
            elif class_name == 'HydroGenerator':
                self.hydro_generators.append(generator)
            elif class_name == 'SolarGenerator':
                self.solar_generators.append(generator)


    def add_load(self, load: 'Load'):
        "Add a load to this bus"
        if load not in self.loads:
            self.loads.append(load)

    def __repr__(self):
                """Representação textual amigável da barra."""
                return (f"Bus(id={self.id}, name='{self.name}', btype={self.btype.name}, "
                        f"v={self.v_pu:.3f} pu, theta={self.theta_deg:.3f} deg, "
                        f"p_net={self.p_pu:.3f} pu, q_net={self.q_pu:.3f} pu, "
                        f"y_sh={self.shunt_pu:.2f} pu, "
                        f"gens={len(self.generators)}, loads={len(self.loads)})")





##################################################### TESTE #########################################################
if __name__ == "__main__":
    import math
    @dataclass
    class MockNetwork:
        """Simulação da classe Network apenas para testes."""
        sb_mva: float = 100.0
        buses: List[Bus] = field(default_factory=list)

    @dataclass
    class MockLoad:
        """Simulação da classe Load."""
        bus: Bus
        p_pu: float = 0.0
        q_pu: float = 0.0
        
        def __post_init__(self):
            # Simula o comportamento de se auto-adicionar à barra
            self.bus.add_load(self)

    @dataclass
    class MockGenerator:
        """Simulação da classe Generator."""
        bus: Bus
        p_pu: float = 0.0
        q_pu: float = 0.0
        
        def __post_init__(self):
            # Simula o comportamento de se auto-adicionar à barra
            self.bus.add_generator(self)

    print("--- Iniciando Teste de Debug da Classe Bus ---")

    # 1. Teste de Instanciação e __post_init__
    print("\n[Teste 1: Instanciação e Padrões]")
    rede_mock = MockNetwork(sb_mva=100.0)
    assert len(rede_mock.buses) == 0

    # Cria a barra. O __post_init__ deve rodar aqui.
    b1 = Bus(network=rede_mock, id=1)

    # Asserts de __post_init__
    assert b1.name == "Bus_1"          # Nome foi auto-gerado?
    assert len(rede_mock.buses) == 1   # Barra foi add à rede?
    assert rede_mock.buses[0] is b1    # É a barra correta?

    # Asserts de valores padrão
    assert b1.btype == BusType.PQ
    assert b1.v_pu == 1.0
    assert b1.theta_deg == 0.0
    assert b1.q_shunt_mvar == 0.0
    print("OK - Instanciação, __post_init__ e padrões corretos.")
    print("\n[Teste 2: Getter/Setter de Ângulo]")
    
    # Testando o GETTER (theta_rad)
    b1.theta_deg = 90.0
    valor_getter = b1.theta_rad
    valor_esperado_rad = math.pi / 2.0
    print(f"  Definido: theta_deg = 90.0")
    print(f"  Obtido (getter): theta_rad = {valor_getter:.6f}")
    assert np.isclose(valor_getter, valor_esperado_rad)

    # Testando o SETTER (theta_rad)
    valor_setter_rad = math.pi
    b1.theta_rad = valor_setter_rad # Usando o setter
    valor_esperado_deg = 180.0
    print(f"  Definido (setter): theta_rad = {valor_setter_rad:.6f}")
    print(f"  Obtido: theta_deg = {b1.theta_deg}")
    assert np.isclose(b1.theta_deg, valor_esperado_deg)
    print("OK - Getter e Setter de ângulo (rad/deg) funcionam.")

    # 3. Teste de Propriedades Calculadas
    print("\n[Teste 3: Propriedades Calculadas]")
    b2 = Bus(network=rede_mock, id=2, v_pu=1.1, theta_deg=-30.0, q_shunt_mvar=50.0)
    
    # Teste v_complex
    v_comp_calc = b2.v_complex
    v_comp_esp = cmath.rect(1.1, np.deg2rad(-30.0)) # (0.9526 - 0.55j)
    print(f"  v_complex calculado: {v_comp_calc:.4f}")
    print(f"  v_complex esperado: {v_comp_esp:.4f}")
    assert np.isclose(v_comp_calc, v_comp_esp)

    # Teste y_shunt_pu
    y_sh_calc = b2.shunt_pu
    y_sh_esp = (50.0 * 1j) / 100.0 # 0.5j
    print(f"  y_shunt_pu calculado: {y_sh_calc}")
    print(f"  y_shunt_pu esperado: {y_sh_esp}")
    assert y_sh_calc == y_sh_esp
    print("OK - Propriedades v_complex e y_shunt_pu corretas.")

    # 4. Teste de Agregação (p_pu, q_pu)
    print("\n[Teste 4: Agregação p_pu / q_pu]")
    
    # As cargas e geradores mocks se auto-adicionam à b2
    g1 = MockGenerator(bus=b2, p_pu=1.5, q_pu=0.8) # p_total = 1.5
    l1 = MockLoad(bus=b2, p_pu=0.7, q_pu=0.2)      # p_total = 1.5 - 0.7 = 0.8
    g2 = MockGenerator(bus=b2, p_pu=0.5, q_pu=0.1) # p_total = 0.8 + 0.5 = 1.3
    
    assert len(b2.generators) == 2
    assert len(b2.loads) == 1

    p_net_calc = b2.p_pu
    q_net_calc = b2.q_pu
    p_net_esp = (1.5 + 0.5) - 0.7 # 1.3
    q_net_esp = (0.8 + 0.1) - 0.2 # 0.7

    print(f"  p_pu líquido calculado: {p_net_calc:.3f} (esperado: {p_net_esp:.3f})")
    print(f"  q_pu líquido calculado: {q_net_calc:.3f} (esperado: {q_net_esp:.3f})")
    
    assert np.isclose(p_net_calc, p_net_esp)
    assert np.isclose(q_net_calc, q_net_esp)
    print("OK - Agregação p_pu e q_pu correta.")

    # 5. Teste de Representação (__repr__)
    print("\n[Teste 5: Representação textual (__repr__)]")
    print(f"  Repr Barra 1: {b1}")
    print(f"  Repr Barra 2: {b2}")
    
    # Teste simples de __repr__
    b2_repr = repr(b2)
    assert "id=2" in b2_repr
    assert "btype=PQ" in b2_repr # b2 foi criada como PQ (padrão)
    assert "v=1.100 pu" in b2_repr
    assert "theta=-30.000 deg" in b2_repr
    assert "p_net=1.300 pu" in b2_repr
    assert "y_sh=0.00+0.50j pu" in b2_repr
    assert "gens=2" in b2_repr
    assert "loads=1" in b2_repr
    print("OK - Formato __repr__ parece correto.")



