# File: src/core_models/temporal_structure.py

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum
import calendar

class Discretization(Enum):
    """Define a granularidade temporal do modelo."""
    HOUR = "Hour"
    DAY = "Day"
    MONTH = "Month"
    YEAR = "Year"

@dataclass
class TemporalStructure:
    """
    Define a estrutura de tempo do problema de otimização (SDDP/Despacho).

    Gerencia o mapeamento entre a granularidade (Discretization) e o 
    número total de estágios.
    """
    start_date: datetime
    end_date: datetime
    discretization: Discretization
    
    # Armazena o número de estágios calculado/fornecido
    num_stages: Optional[int] = field(init=False)
    
    def __post_init__(self):
        # 1. Validação básica
        if self.start_date >= self.end_date:
            raise ValueError("A data de início deve ser anterior à data de fim.")

        # 2. Determinação do número de estágios
        self._calculate_num_stages()

        if self.num_stages <= 0:
            raise ValueError(f"Não foi possível determinar um número válido de estágios com a discretização {self.discretization.value}.")

    def _calculate_num_stages(self):
        """Calcula o número de estágios com base na granularidade temporal."""
        
        delta = self.end_date - self.start_date

        if self.discretization == Discretization.MONTH:
            # Conta a diferença de meses, considerando a virada do ano
            num_months = (self.end_date.year - self.start_date.year) * 12 + \
                        (self.end_date.month - self.start_date.month)
            self.num_stages = num_months
            
        elif self.discretization == Discretization.HOUR:
            self.num_stages = int(delta.total_seconds() / 3600)
            
        elif self.discretization == Discretization.DAY:
            self.num_stages = delta.days
            
        elif self.discretization == Discretization.YEAR:
             self.num_stages = self.end_date.year - self.start_date.year
        
        else:
            self.num_stages = 0


    def get_stage_duration(self, stage_index: int) -> timedelta:
        """Retorna a duração do estágio, ajustando para meses/anos."""
        if self.discretization == Discretization.MONTH:
            # Lógica para obter dias no mês
            current_date = self.get_stage_start_date(stage_index)
            _, days_in_month = calendar.monthrange(current_date.year, current_date.month)
            return timedelta(days=days_in_month)

        if self.discretization == Discretization.HOUR:
            return timedelta(hours=1)
        if self.discretization == Discretization.DAY:
            return timedelta(days=1)
        if self.discretization == Discretization.YEAR:
            return timedelta(days=365.25) # Aproximação

        return timedelta(0)


    def get_stage_start_date(self, stage_index: int) -> datetime:
        """Calcula a data de início de um estágio específico."""
        if stage_index < 0 or stage_index >= self.num_stages:
            raise IndexError(f"Índice do estágio {stage_index} fora dos limites (0 a {self.num_stages - 1}).")

        if self.discretization == Discretization.MONTH:
            # Itera mês a mês para encontrar a data correta
            year = self.start_date.year + (self.start_date.month + stage_index - 1) // 12
            month = (self.start_date.month + stage_index - 1) % 12 + 1
            day = min(self.start_date.day, calendar.monthrange(year, month)[1])
            return datetime(year, month, day)
        
        # Para DAY, HOUR, YEAR: Usa a duração fixa
        duration = self.get_stage_duration(0)
        return self.start_date + duration * stage_index


    def __repr__(self):
        return (f"TemporalStructure(Stages={self.num_stages}, Unit='{self.discretization.value}', "
                f"Range={self.start_date.date()} to {self.end_date.date()})")

if __name__ == "__main__":
    from datetime import date
    
    print("--- Guia Prático e Testes da Classe TemporalStructure ---")
    
    # Exemplo 1: Mensal
    print("\n[Exemplo 1: Discretização Mensal]")
    ts_mensal = TemporalStructure(datetime(2025, 1, 15), datetime(2025, 5, 15), Discretization.MONTH)
    print(ts_mensal)
    
    # Teste de datas e durações (mês a mês)
    print(f"Estágio 0: {ts_mensal.get_stage_start_date(0).date()} | Duração: {ts_mensal.get_stage_duration(0).days} dias")
    print(f"Estágio 1: {ts_mensal.get_stage_start_date(1).date()} | Duração: {ts_mensal.get_stage_duration(1).days} dias")
    print(f"Estágio 3: {ts_mensal.get_stage_start_date(3).date()} | Duração: {ts_mensal.get_stage_duration(3).days} dias") # Março para Abril

    # Exemplo 2: Horária
    print("\n[Exemplo 2: Discretização Horária]")
    ts_horaria = TemporalStructure(datetime(2025, 1, 1, 10, 0), datetime(2025, 1, 3, 10, 0), Discretization.HOUR)
    print(ts_horaria)
    print(f"Total de Estágios: {ts_horaria.num_stages}")
    print(f"Estágio Final: {ts_horaria.get_stage_start_date(ts_horaria.num_stages-1)}")
    
    # Exemplo 3: Anual
    print("\n[Exemplo 3: Discretização Anual]")
    ts_anual = TemporalStructure(datetime(2025, 1, 1), datetime(2030, 1, 1), Discretization.YEAR)
    print(ts_anual)