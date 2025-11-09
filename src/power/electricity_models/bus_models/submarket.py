from __future__ import annotations
from power.electricity_models.bus_models.abc_node import AbstractNode
from dataclasses import dataclass, field
from typing import List
from power.electricity_models.bus_models.abc_node import AbstractNode
import numpy as np
from enum import Enum


@dataclass
class SubMarket(AbstractNode):
    """
    Representa um Submercado. Agrega um conjunto de Bus e implementa 
    AbstractNode para fornecer injeção líquida agregada.
    """
    buses: List["Bus"] = field(default_factory=list, repr=False)
    price_usd_per_mwh: float = 0.0      # Preço em $/MWh
    max_import_mw: float = 1e9          # Limite máximo de importação (entrada)
    max_export_mw: float = 1e9          # Limite máximo de exportação (saída)

    def __post_init__(self):
        # O __post_init__ do AbstractNode não faz nada. 
        # Aqui, apenas adicionamos um nome padrão mais significativo.
        if self.name is None:
            self.name = f"Submarket_{self.id}"
        
        # Adiciona este submercado à rede, se a rede tiver uma lista para isso
        if hasattr(self.network, 'submarkets'):
            self.network.submarkets.append(self)
        
    def add_bus(self, bus: 'Bus'):
        """Adiciona uma barra a este submercado."""
        if bus not in self.buses:
            self.buses.append(bus)

    @property
    def p_pu(self) -> float:
        """Agregação da injeção líquida de potência ativa de todas as barras em p.u."""
        # Usa a propriedade p_pu de cada Bus contido
        return sum(bus.p_pu for bus in self.buses)

    @property
    def q_pu(self) -> float:
        """Agregação da injeção líquida de potência reativa de todas as barras em p.u."""
        # Usa a propriedade q_pu de cada Bus contido
        return sum(bus.q_pu for bus in self.buses)
    
    @property
    def max_import_pu(self) -> float:
        """Limite máximo de importação (recebimento de potência) em p.u."""
        return self.max_import_mw / self.sb_mva
    
    @property
    def max_export_pu(self) -> float:
        """Limite máximo de exportação (envio de potência) em p.u."""
        return self.max_export_mw / self.sb_mva

    def __repr__(self) -> str:
        """Representação textual amigável do Submercado."""
        return (f"SubMarket(id={self.id}, name='{self.name}', buses={len(self.buses)}, "
                f"P_net={self.p_mw:.2f} MW, Q_net={self.q_mvar:.2f} MVAr, "
                f"Price={self.price_usd_per_mwh:.2f} $/MWh, "
                f"Limits=[-{self.max_import_mw:.0f} MW, {self.max_export_mw:.0f} MW])")

if __name__ == "__main__":

    class BusType(Enum):
        SLACK = "SLACK"
        PQ = "PQ"
        PV = "PV"
        
    @dataclass
    class MockNetwork:
        buses: List["Bus"] = field(default_factory=list)
        submarkets: List["SubMarket"] = field(default_factory=list) # Adiciona lista de submarkets

    # Definindo Mocks para Carga/Geração (Simplificado)
    @dataclass
    class MockLoad:
        bus: "Bus"
        p_pu: float = 0.0
        q_pu: float = 0.0
        
        def __post_init__(self):
            # Solução: Adicionar esta carga à lista de loads do bus
            self.bus.loads.append(self)

    @dataclass
    class MockGenerator:
        bus: "Bus"
        p_pu: float = 0.0
        q_pu: float = 0.0
        
        def __post_init__(self):
            # Solução: Adicionar esta geração à lista de generators do bus
            self.bus.generators.append(self)

    # Definindo Mocks de AbstractNode e Bus para o escopo do teste
    @dataclass 
    class AbstractNode: # Mock simplificado
        network: "MockNetwork"
        id: int
        sb_mva: float = 100.0

        @property
        def p_pu(self) -> float: raise NotImplementedError
        @property
        def q_pu(self) -> float: raise NotImplementedError
        @property
        def p_mw(self) -> float: return self.p_pu * self.sb_mva
        @property
        def q_mvar(self) -> float: return self.q_pu * self.sb_mva

    @dataclass
    class Bus(AbstractNode):
        loads: List[MockLoad] = field(default_factory=list, repr=False)
        generators: List[MockGenerator] = field(default_factory=list, repr=False)
        
        def __post_init__(self):
            self.network.buses.append(self)
        
        @property
        def p_pu(self) -> float:
            return sum(g.p_pu for g in self.generators) - sum(l.p_pu for l in self.loads)

        @property
        def q_pu(self) -> float:
            return sum(g.q_pu for g in self.generators) - sum(l.q_pu for l in self.loads) 

    print("\n--- Iniciando Teste de Debug da Classe SubMarket ---")
    # Setup
    sb_base = 250.0 # Base maior para destacar conversões
    rede_mock = MockNetwork()
    
    # 1. Criação de Barras com Potência Líquida
    b1 = Bus(network=rede_mock, id=1, sb_mva=sb_base)
    MockGenerator(bus=b1, p_pu=2.0, q_pu=1.0) # Injeção B1: P=2.0, Q=1.0 pu
    MockLoad(bus=b1, p_pu=0.5, q_pu=0.2)      # P_net=1.5, Q_net=0.8 pu
    b2 = Bus(network=rede_mock, id=2, sb_mva=sb_base)
    MockLoad(bus=b2, p_pu=1.0, q_pu=0.5)      # Injeção B2: P=-1.0, Q=-0.5 pu
    b3 = Bus(network=rede_mock, id=3, sb_mva=sb_base)

    print(f"B1 P_pu: {b1.p_pu:.2f}, B2 P_pu: {b2.p_pu:.2f}")

    # 2. Teste de Instanciação e Agregação
    print("\n[Teste 1: Instanciação, Adição de Bus e P/Q Agregado]")
    
    sm_sul = SubMarket(network=rede_mock, id=50, name="SM_SUL", sb_mva=sb_base, 
                        price_usd_per_mwh=80.50, max_import_mw=100.0, max_export_mw=50.0)
    
    sm_sul.add_bus(b1)
    sm_sul.add_bus(b2)
    sm_sul.add_bus(b3)

    assert len(rede_mock.submarkets) == 1
    assert len(sm_sul.buses) == 3
    
    # Agregação de Potência em p.u.
    p_net_pu_calc = sm_sul.p_pu
    q_net_pu_calc = sm_sul.q_pu
    p_net_pu_esp = 0.5
    q_net_pu_esp = 0.3
 
    assert np.isclose(p_net_pu_calc, p_net_pu_esp)
    assert np.isclose(q_net_pu_calc, q_net_pu_esp)
    print(f"OK - P_pu agregado: {p_net_pu_calc:.2f} pu (Esperado: {p_net_pu_esp:.2f} pu)")
    
    # 3. Teste de Unidades Físicas (MW/MVAr)
    print("\n[Teste 2: Unidades Físicas e Limites]")
    
    p_net_mw_esp = p_net_pu_esp * sb_base
    q_net_mvar_esp = q_net_pu_esp * sb_base
    assert np.isclose(sm_sul.p_mw, p_net_mw_esp)
    assert np.isclose(sm_sul.q_mvar, q_net_mvar_esp)
    print(f"OK - P_mw: {sm_sul.p_mw:.1f} MW (Esperado: {p_net_mw_esp:.1f} MW)")

    max_imp_pu_esp = 100.0 / 250.0
    max_exp_pu_esp = 50.0 / 250.0
    assert np.isclose(sm_sul.max_import_pu, max_imp_pu_esp)
    assert np.isclose(sm_sul.max_export_pu, max_exp_pu_esp)
    print(f"OK - Limites em p.u. (Import={sm_sul.max_import_pu:.2f} pu, Export={sm_sul.max_export_pu:.2f} pu) corretos.")
    
    # 4. Teste de Representação (__repr__)
    print("\n[Teste 3: Representação textual (__repr__)]")
    print(f"  Repr SubMarket: {sm_sul}")
    
    sm_repr = repr(sm_sul)
    assert "id=50" in sm_repr
    assert "buses=3" in sm_repr
    assert "P_net=125.00 MW" in sm_repr
    assert "Price=80.50 $/MWh" in sm_repr
    assert "Limits=[-100 MW, 50 MW]" in sm_repr
    print("OK - Formato __repr__ parece correto.")
    print("\n--- Fim do Teste de Debug da Classe SubMarket ---")