from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Union, List
from power.hydraulic_models.node_models.abc_hydro_node import ABCHydroNode
from data_models.time_series import TimeSeries

@dataclass
class HydroBus(ABCHydroNode):
    """
    Representa um nó na rede hidráulica, tipicamente um reservatório.
    """
    
    natural_inflow_ts: Optional[TimeSeries] = field(default=None, repr=False)
    natural_inflow_m3s: float = 0.0  # Afluência natural (m³/s)

    hydro_generators: List['HydroGenerator'] = field(default_factory=list)
    
    def __post_init__(self):
        # Inicializa o valor instantâneo com o primeiro ponto da série, se fornecida
        if self.natural_inflow_ts is not None:
            # Assume que get_value(0, 0) retorna o valor do primeiro estágio/cenário
            self.natural_inflow_m3s = self.natural_inflow_ts.get_value(0, 0)
    
    def add_generator(self, generator: 'HydroGenerator'):
        self.hydro_generators.append(generator)
    
    # --- MÉTODOS DE ACESSO À CURVA ---
    def get_inflow_at(self, stage: int, scenario: int = 0) -> float:
        """
        Retorna o valor de afluência natural (m³/s ou unidade do TS) 
        para um estágio e cenário específico.
        """
        if self.natural_inflow_ts is not None:
            return self.natural_inflow_ts.get_value(stage, scenario)
        
        # Retorna o valor estático/instantâneo se a série não estiver definida
        return self.natural_inflow_m3s

    def apply_stage_data(self, stage: int, scenario: int = 0):
        """
        [MÉTODO DO SIMULADOR]
        Atualiza o valor instantâneo de afluência natural (natural_inflow_m3s) 
        para o valor do ponto (stage, scenario) da TimeSeries.
        """
        self.natural_inflow_m3s = self.get_inflow_at(stage, scenario)

    def __repr__(self):
        # Atualizando o repr para incluir o estado de afluência
        return (f"HydroBus(id={self.id}, name='{self.name}', "
                f"Inflow_TS={'Sim' if self.natural_inflow_ts else 'Não'}, "
                f"Inflow_Current={self.natural_inflow_m3s:.2f} m³/s)")

if __name__ == "__main__":
    import numpy as np
    from dataclasses import dataclass
    from typing import List, Union

    # --- MOCKS PARA TESTE AUTÔNOMO ---

    # 1. Mock da HydroNetwork (ESSENCIAL: O HydroBus precisa pertencer a uma rede)
    class MockHydroNetwork:
        def __init__(self):
            self.nodes = []
        
        # Métodos 'fake' para o caso do HydroBus tentar se registrar na rede
        def add_node(self, node):
            self.nodes.append(node)
            print(f"[MockNetwork] Node '{node.name}' registrado na rede com sucesso.")
        
        def add_bus(self, bus):
            self.add_node(bus)

    # 2. Mock da TimeSeries (Mantive sua lógica, apenas ajustei para dataclass funcionar aqui)
    @dataclass
    class MockTimeSeries:
        data: np.ndarray
        
        def __post_init__(self):
            if self.data.ndim == 1:
                self.data = self.data.reshape(-1, 1)
            self.num_stages, self.num_scenarios = self.data.shape

        def get_value(self, stage_index: int, scenario_index: int = 0) -> float:
            return self.data[stage_index, scenario_index]

        def get_percentile_profile(self, percentile: Union[int, float]) -> np.ndarray:
            return np.percentile(self.data, percentile, axis=1)

        def __repr__(self):
            return f"MockTimeSeries(Stages={self.num_stages}, Scenarios={self.num_scenarios})"

    print("--- Teste de Integração HydroBus e TimeSeries ---")

    # 1. Instanciar a Rede Mock (Para evitar erro de argumento faltando)
    mock_net = MockHydroNetwork()

    # 2. Criação de Dados Estocásticos
    afluencia_data = np.array([
        [150.0, 200.0],  # Mês 1
        [120.0, 180.0],  # Mês 2
        [130.0, 190.0]   # Mês 3
    ])

    # 3. Criação da Série Temporal
    afluencia_ts = MockTimeSeries(afluencia_data)
    print(f"Série criada: {afluencia_ts}")
    print(f"Perfil P90 (Conservador): {afluencia_ts.get_percentile_profile(10)}")

    # 4. Criação do HydroBus (AGORA CORRETO)
    try:
        res_furnas = HydroBus(
            id=1,
            name="Furnas",
            hydro_network=mock_net,  # <--- AQUI ESTAVA O ERRO ANTES (Agora passamos a rede)
            natural_inflow_ts=afluencia_ts
        )
        print(f"\nEstado Inicial do Nó: {res_furnas}")
        # Nota: Assumindo que seu HydroBus tem o atributo natural_inflow_m3s ou similar
        # Se der erro aqui, verifique se o nome do atributo na sua classe é esse mesmo.
        if hasattr(res_furnas, 'natural_inflow_m3s'):
             print(f"Inflow lido no init: {res_furnas.natural_inflow_m3s:.2f} m³/s")
    except TypeError as e:
        print(f"\nERRO FATAL NA CRIAÇÃO: {e}")
        exit()

    # 5. Simulação de Estágio
    print("\n--- Simulação de Estágios ---")
    
    # ESTÁGIO 1, CENÁRIO ÚMIDO (w=1)
    stage_1 = 1
    scenario_umido = 1 
    
    # Verificando se o método existe antes de chamar (boas práticas de teste)
    if hasattr(res_furnas, 'apply_stage_data'):
        res_furnas.apply_stage_data(stage=stage_1, scenario=scenario_umido)
        print(f"Aplicando Estágio {stage_1}, Cenário {scenario_umido}: {getattr(res_furnas, 'natural_inflow_m3s', 'N/A')} m³/s")
        
        # ESTÁGIO 2, CENÁRIO SECO (w=0)
        stage_2 = 2
        scenario_seco = 0 
        res_furnas.apply_stage_data(stage=stage_2, scenario=scenario_seco)
        print(f"Aplicando Estágio {stage_2}, Cenário {scenario_seco}: {getattr(res_furnas, 'natural_inflow_m3s', 'N/A')} m³/s")
    else:
        print("AVISO: Método 'apply_stage_data' não encontrado na classe HydroBus.")

    print(f"\nEstado Final do Nó: {res_furnas}")