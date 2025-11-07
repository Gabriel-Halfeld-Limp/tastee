import pulp as pl
import numpy as np
import json
from power import Network
from power import WindGenerator

def extract_and_save_results(problem: pl.LpProblem, net: Network, output_filename: str = None) -> dict:
    """
    Extrai as variáveis primais e duais de um problema de otimização resolvido,
    estrutura os resultados e os exporta para um arquivo JSON.

    Args:
        problem (pl.LpProblem): O objeto do problema PuLP já resolvido.
        net (object): O objeto da rede contendo as listas de 'buses' e 'lines'.
        output_filename (str): O nome do arquivo para salvar os resultados em JSON.

    Returns:
        dict
    """
    # 1. Verifica o status do solver antes de prosseguir
    if problem.status != pl.LpStatusOptimal:
        print(f"\n[AVISO] A solução não é ótima ({pl.LpStatus[problem.status]}). Nenhum resultado será extraído.")
        return None

    # --- Extração das Variáveis Primais ---
    try:
        primal_results = {
            'geracao_pu': {gen.id: gen.p_var.value() for gen in net.generators},
            'corte_carga_pu': {load.id: load.p_shed_var.value() for load in net.loads if hasattr(load, 'p_shed_var')},
            'thetas_deg': {bus.id: np.rad2deg(bus.theta_var.value()) for bus in net.buses},
            'fluxo_pu': {line.id: line.flow_var.value() for line in net.lines}
        }
    except AttributeError as e:
        print(f"[ERRO] Falha ao extrair variáveis primais. Verifique os nomes dos atributos (ex: p_var, theta_var): {e}")
        return None
    
    # ----- Sumário de Cargas e Perdas --------
    try:
        total_load_pu = sum(load.p_pu for load in net.loads)
        total_loss_pu = sum(bus.loss for bus in net.buses if hasattr(bus, "loss"))
        total_shed_pu = sum(l.p_shed_var.value() for l in net.loads if hasattr(l, 'p_shed_var'))
        loss_summary = {
            # Valores totais do sistema
            'carga_total_pu': total_load_pu,
            'perdas_totais_pu': total_loss_pu,
            'corte_total_pu'  : total_shed_pu,
            # Valores individuais
            'cargas_individuais_pu': {
                load.id: load.p_pu for load in net.loads
            },
            'perdas_por_barra_pu': {
                bus.id: bus.loss for bus in net.buses if hasattr(bus, 'loss')
            },
        }

        curtailment_individual = {}
        total_curtailment = 0
        for g in net.generators:
            if isinstance(g, WindGenerator):
                disponivel = g.p_max_pu
                despachado = g.p_var.value()
                curtailment = disponivel - despachado
                if curtailment > 1e-6:
                    curtailment_individual[g.id] = {
                        "disponivel_pu": disponivel,
                        "despachado_pu": despachado,
                        "curtailment_pu": curtailment
                    }
                    total_curtailment += curtailment
        
        curtailment_summary = {
        "curtailment_total_pu": total_curtailment,
        "curtailment_por_gerador": curtailment_individual
        } 
        shedding_individual = {}
        total_shedding = 0
        for l in net.loads:
            if hasattr(l, 'p_shed_var'):
                shed_amount = l.p_shed_var.value()
                if shed_amount > 1e-6: # Apenas registra se for significativo
                    shedding_individual[l.id] = {
                        "demanda_nominal_pu": l.p_pu,
                        "carga_cortada_pu": shed_amount,
                        "carga_atendida_pu": l.p_pu - shed_amount
                    }
                    total_shedding += shed_amount
        shedding_summary = {
            "corte_total_pu": total_shedding,
            "corte_por_carga": shedding_individual
        }

    
    except Exception as e:
        print(f"[ERRO] Falha ao extrair sumário de cargas e perdas: {e}")
        return None


    # --- Extração das Variáveis Duais (Multiplicadores de Lagrange) ---
    
    # Função auxiliar para obter o valor dual de forma segura
    def get_dual(constraint_name, multiplier=1):
        constraint = problem.constraints.get(constraint_name)
        if constraint is not None:
            return constraint.pi * multiplier
        return None # Retorna 'N/A' se a restrição não for encontrada

    dual_results = {
        'custo_marginal_de_energia_LMP': {
            # O LMP é o dual da restrição de balanço nodal (com sinal trocado)
            bus.id: get_dual(f'B{bus.id}_Power_Balance')
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
        'custo_total': problem.objective.value(),
        'sumario_perdas': loss_summary,
        'sumario_curtailment': curtailment_summary,
        'sumario_corte': shedding_summary,
        'primal_results': primal_results,
        'dual_results': dual_results
    }
    
    if output_filename:
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(final_results, f, indent=4, ensure_ascii=False, cls=NpEncoder)
            print(f"\n[SUCESSO] Resultados exportados para o arquivo '{output_filename}'")
        except Exception as e:
            print(f"\n[ERRO] Não foi possível exportar os resultados para JSON: {e}")

    return final_results


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
