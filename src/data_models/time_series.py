# File: src/energetic_planning/time_series.py (Corrigido o bloco de testes)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Union
import numpy as np

# A importação do pandas é crucial para aceitar DataFrames
try:
    import pandas as pd
except ImportError:
    pd = None
    print("Aviso: Pandas não está instalado. A classe TimeSeries só aceitará numpy.ndarray/List.")

# Definição de tipos
TimeSeriesData = np.ndarray

@dataclass
class TimeSeries:
    """
    Gerencia séries temporais/estocásticas como uma matriz (Estágio x Cenário).
    """
    data: Union[TimeSeriesData, List, pd.DataFrame]
    name: Optional[str] = None
    unit: str = "pu"
    
    num_stages: int = field(init=False)
    num_scenarios: int = field(init=False)
    
    def __post_init__(self):
        
        # 1. Converte Pandas DataFrame para NumPy array
        if pd is not None and isinstance(self.data, pd.DataFrame):
            self.data = self.data.to_numpy(dtype=float)
        
        # 2. Garante que o input é um array numpy
        if not isinstance(self.data, np.ndarray):
            self.data = np.array(self.data, dtype=float)
        
        # 3. Garante que a estrutura é 2D (Estágio x Cenário)
        if self.data.ndim == 1:
            self.data = self.data.reshape(-1, 1)
        elif self.data.ndim > 2:
            raise ValueError(f"Dimensões de dados inválidas: esperado 1D ou 2D (recebido {self.data.ndim}D).")

        self.num_stages, self.num_scenarios = self.data.shape
        
        if self.name is None:
            self.name = "TimeSeries_Generic"

    def get_value(self, stage_index: int, scenario_index: int = 0) -> float:
        """Retorna o valor específico para um estágio e cenário."""
        if stage_index < 0 or stage_index >= self.num_stages:
            raise IndexError(f"Índice do estágio {stage_index} fora dos limites (0 a {self.num_stages - 1}).")
        if scenario_index < 0 or scenario_index >= self.num_scenarios:
            raise IndexError(f"Índice do cenário {scenario_index} fora dos limites (0 a {self.num_scenarios - 1}).")
            
        return self.data[stage_index, scenario_index]

    def get_mean_profile(self) -> TimeSeriesData:
        """Calcula o perfil médio ao longo dos cenários para cada estágio."""
        return np.mean(self.data, axis=1)

    def get_percentile_profile(self, percentile: Union[int, float]) -> TimeSeriesData:
        """
        Calcula o perfil de percentil (Px) ao longo dos cenários para cada estágio.

        Args:
            percentile (int/float): O percentil desejado (e.g., 50 para P50).
        """
        if not 0 <= percentile <= 100:
            raise ValueError("O percentil deve estar entre 0 e 100.")
            
        # O axis=1 aplica o cálculo sobre os cenários para cada estágio
        return np.percentile(self.data, percentile, axis=1)

    def to_pu(self, base_mva: float) -> TimeSeries:
        """Cria uma nova TimeSeries com os dados convertidos para p.u."""
        if self.unit.lower() in ["mw", "mvar"]:
            new_data = self.data / base_mva
            new_unit = "pu"
            return TimeSeries(new_data, self.name + "_pu", new_unit)
        return TimeSeries(self.data.copy(), self.name, self.unit)
        
    def __repr__(self):
        return (f"TimeSeries(name='{self.name}', Stages={self.num_stages}, "
                f"Scenarios={self.num_scenarios}, Unit='{self.unit}')")


if __name__ == "__main__":
    print("--- Guia Prático e Testes da Classe TimeSeries ---")
    
    # Geração de dados de exemplo para o teste Px
    NUM_STAGES = 5
    NUM_SCENARIOS = 100
    
    # Matriz de dados com ruído (simulando geração eólica)
    np.random.seed(42) 
    base_data = np.tile(np.linspace(100, 200, NUM_STAGES), (NUM_SCENARIOS, 1)).T
    stochastic_data = base_data + np.random.normal(0, 20, (NUM_STAGES, NUM_SCENARIOS))

    eolica_ts = TimeSeries(stochastic_data, name="Geração Eólica", unit="MW")
    print(eolica_ts)
    
    print("\n[Teste de Percentis (Px) - P90 < P50 < P10]")
    
    # P90 (Conservador): Usamos o 10º percentil do NumPy (90% dos valores são maiores que este)
    p90_conservative = eolica_ts.get_percentile_profile(10)
    # P50 (Mediana): Usamos o 50º percentil (metade dos valores são maiores e metade menores)
    p50_median = eolica_ts.get_percentile_profile(50)
    # P10 (Otimista): Usamos o 90º percentil (apenas 10% dos valores são maiores que este)
    p10_optimistic = eolica_ts.get_percentile_profile(90)
    
    print(f"P10 (Otimista) em MW: {p10_optimistic}")
    print(f"P50 (Mediana) em MW: {p50_median}")
    print(f"P90 (Conservador) em MW: {p90_conservative}")
    
    # Verificação: P10 > P50 > P90
    p10_val = p10_optimistic[0]
    p50_val = p50_median[0]
    p90_val = p90_conservative[0]

    print("\nVerificação (Estágio 0):")
    print(f"P10 (Otimista): {p10_val:.2f}")
    print(f"P50 (Mediana): {p50_val:.2f}")
    print(f"P90 (Conservador): {p90_val:.2f}")
    
    if p10_val > p50_val and p50_val > p90_val:
        print("Resultado OK: Percentis estão na ordem esperada (P10 > P50 > P90).")
    else:
        print("Resultado INVÁLIDO: Percentis fora de ordem!")