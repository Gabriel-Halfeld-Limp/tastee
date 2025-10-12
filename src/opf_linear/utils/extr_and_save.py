import pulp as pl
import numpy as np
import json
from power import Network
from power import WindGenerator

def extract_and_save_results(problem: pl.LpProblem, net: Network, output_filename: str = "optimization_results.json"):
    """
    Extrai as variáveis primais e duais de um problema de otimização resolvido,
    estrutura os resultados e os exporta para um arquivo JSON.

    Args:
        problem (pl.LpProblem): O objeto do problema PuLP já resolvido.
        net (object): O objeto da rede contendo as listas de 'buses' e 'lines'.
        output_filename (str): O nome do arquivo para salvar os resultados em JSON.

    Returns:
        tuple: Uma tupla contendo (primal_results, dual_results) se a solução for ótima,
        caso contrário, retorna (None, None).
    """
    # 1. Verifica o status do solver antes de prosseguir
    if problem.status != pl.LpStatusOptimal:
        print(f"\n[AVISO] A solução não é ótima ({pl.LpStatus[problem.status]}). Nenhum resultado será extraído.")
        return None, None

    # --- Extração das Variáveis Primais ---
    try:
        primal_results = {
            'geracao_pu': {gen.id: f"{gen.p_var.value():.4f}" for gen in net.generators},
            'thetas_deg': {bus.id: f"{np.rad2deg(bus.theta_var.value()):.4f}" for bus in net.buses},
            # Nota: usei 'flow_var'. Se o seu for 'flux_var', ajuste aqui.
            'fluxo_pu': {line.id: f"{line.flow_var.value():.4f}" for line in net.lines}
        }
    except AttributeError as e:
        print(f"[ERRO] Falha ao extrair variáveis primais. Verifique os nomes dos atributos (ex: p_var, theta_var): {e}")
        return None, None
    
    # ----- Sumário de Cargas e Perdas --------
    try:
        total_load_pu = sum(load.p for load in net.loads)
        total_loss_pu = sum(bus.loss for bus in net.buses if hasattr(bus, "loss"))

        loss_summary = {
            # Valores totais do sistema
            'carga_total_pu': f"{total_load_pu:.4f}",
            'perdas_totais_pu': f"{total_loss_pu:.4f}",
            # Valores individuais
            'cargas_individuais_pu': {
                load.id: f"{load.p:.4f}" for load in net.loads
            },
            'perdas_por_barra_pu': {
                bus.id: f"{bus.loss:.6f}" for bus in net.buses if hasattr(bus, 'loss')
            }
        }

        curtailment_individual = {}
        total_curtailment = 0
        for g in net.generators:
            if isinstance(g, WindGenerator):
                disponivel = g.p_max
                despachado = g.p_var.value()
                curtailment = disponivel - despachado
                curtailment_individual[g.id] = {
                    "disponivel_pu": f"{disponivel:.4f}",
                    "despachado_pu": f"{despachado:.4f}",
                    "curtailment_pu": f"{curtailment:.4f}"
                }
                total_curtailment += curtailment
        
        curtailment_summary = {
        "curtailment_total_pu": f"{total_curtailment:.4f}",
        "curtailment_por_gerador": curtailment_individual
        }

    
    except Exception as e:
        print(f"[ERRO] Falha ao extrair sumário de cargas e perdas: {e}")
        return None, None


    # --- Extração das Variáveis Duais (Multiplicadores de Lagrange) ---
    
    # Função auxiliar para obter o valor dual de forma segura
    def get_dual(constraint_name, multiplier=1):
        constraint = problem.constraints.get(constraint_name)
        if constraint is not None:
            return constraint.pi * multiplier
        return "N/A" # Retorna 'N/A' se a restrição não for encontrada

    dual_results = {
        'custo_marginal_de_energia_LMP': {
            # O LMP é o dual da restrição de balanço nodal (com sinal trocado)
            bus.id: f"${get_dual(f'B{bus.id}_Power_Balance'):.2f}/pu"
            for bus in net.buses
        },
        'congestionamento_de_fluxo': {
            # Duals das restrições de limite de fluxo
            line.id: {
                # Para restrições <=, o lambda é -pi
                'limite_superior': get_dual(f'Constraint_Flow_{line.id}_Upper', multiplier=-1),
                # Para restrições >=, o lambda é pi
                'limite_inferior': get_dual(f'Constraint_Flow_{line.id}_Lower')
            }
            for line in net.lines
        },
        'limites_de_geracao': {
            gen.id: {
                'limite_superior': get_dual(f'Constraint_P{gen.id}_Upper', multiplier=-1),
                'limite_inferior': get_dual(f'Constraint_P{gen.id}_Lower')
            }
            for gen in net.generators
        }
    }
    
    # --- Montagem Final e Exportação ---
    final_results = {
        'solver_status': pl.LpStatus[problem.status],
        'custo_total': f"${problem.objective.value():.2f}",
        'sumario_perdas': loss_summary,
        'sumario_curtailment': curtailment_summary,
        'primal_results': primal_results,
        'dual_results': dual_results
    }

    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, indent=4, ensure_ascii=False)
        print(f"\n[SUCESSO] Resultados exportados para o arquivo '{output_filename}'")
    except Exception as e:
        print(f"\n[ERRO] Não foi possível exportar os resultados para JSON: {e}")

    return primal_results, dual_results


# Classe auxiliar para garantir que tipos NumPy sejam serializáveis em JSON
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)
