import pulp as pl
import numpy as np  # Precisamos do numpy para np.pi
from power import Network, ThermalGenerator

def extract_dual(problem: pl.LpProblem, net: Network) -> dict:
    """
    Extrai todos os valores das variáveis duais (preços-sombra) do problema,
    convertendo-os para unidades físicas consistentes ($/MWh, $/grau).
    """
    def get_dual(constraint_name, multiplier=1):
        constraint = problem.constraints.get(constraint_name)
        return constraint.pi * multiplier if constraint is not None else None

    try:
        power_base = net.sb
        rad_para_grau = np.pi / 180

        return {
            'preco_marginal_energia': {
                bus.id: get_dual(f'B{bus.id}_Power_Balance') / power_base
                for bus in net.buses
            },
            'limites_fluxo': {
                line.id: {
                    'limite_superior_dual': get_dual(f'Constraint_Flow_{line.id}_Upper', -1) / power_base,
                    'limite_inferior_dual': get_dual(f'Constraint_Flow_{line.id}_Lower', 1) / power_base
                } for line in net.lines
            },
            'limites_geracao': {
                gen.id: {
                    'limite_superior_dual': get_dual(f'Constraint_P{gen.id}_Upper', -1) / power_base,
                    'limite_inferior_dual': get_dual(f'Constraint_P{gen.id}_Lower', 1) / power_base
                } for gen in net.generators
            },
            'limites_corte_carga': {
                load.id: {
                    'limite_superior_dual': get_dual(f"Constraint_P_Shed{load.id}_Upper", -1) / power_base, 
                    'limite_inferior_dual': get_dual(f"Constraint_P_Shed{load.id}_Lower", 1) / power_base
                } for load in net.loads
            },
            'limites_theta': {
                bus.id: {
                    'limite_superior_dual': get_dual(f"Constraint_Theta_{bus.id}_Upper", -1) * rad_para_grau, 
                    'limite_inferior_dual': get_dual(f"Constraint_Theta_{bus.id}_Lower", 1) * rad_para_grau
                } for bus in net.buses
            }
        }
    except Exception as e:
        print(f"[ERRO] Falha ao extrair variáveis duais: {e}")
        return None