import numpy as np
import copy
import pulp as pl
from power import Network, Line
from power.systems import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from metaheuristic.aoa_metaheuristic.optimizer import AOA
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from trabalhos_transmissao.utils.load_scen import apply_load_scen

# Definição da função auxiliar de extração de duais (mantida do exemplo anterior)
def extract_line_duals(solver, net: Network):
    """Extrai os multiplicadores de Lagrange (duais) dos limites de fluxo das linhas."""
    
    power_base = net.sb
    limites_fluxo_duais = {}
    
    # Nota: Devemos iterar sobre as linhas da rede que está sendo resolvida (net)
    for line in net.lines:
        upper_name = f'Constraint_Flow_{line.id}_Upper'
        lower_name = f'Constraint_Flow_{line.id}_Lower'
        
        # Acessa os objetos de restrição
        constraint_upper = solver.problem.constraints.get(upper_name)
        constraint_lower = solver.problem.constraints.get(lower_name)

        # Extrai os valores duais e ajusta o sinal/base
        dual_upper = constraint_upper.pi * (-1) / power_base if (constraint_upper and constraint_upper.pi is not None) else 0.0
        dual_lower = constraint_lower.pi * (1) / power_base if (constraint_lower and constraint_lower.pi is not None) else 0.0
        
        # O preço-sombra total é a soma dos duais (com os sinais corretos)
        limites_fluxo_duais[line.id] = dual_upper + dual_lower
    
    return limites_fluxo_duais

# --- 1. Configuração do Problema ---
BASE_NET = B3EOLCharged()
seed = 42
nscen = 3
rng = np.random.default_rng(seed=seed)
line_ids = [line.id for line in BASE_NET.lines] # LTs originais para inicialização

# --- 2. Definição da Função de Fitness ---
def main():
    """
    Calcula o custo total (reforço + operação) para um dado plano de reforço.
    """
    
    # --- 1. Inicialização para Acumulação ---
    all_costs = []
    all_curtailment = []
    all_deficits = []
    
    # Dicionário para acumular a soma dos duais de fluxo (chave: id da LT)
    sum_line_duals = {line_id: 0.0 for line_id in line_ids}
    
    # Contador para o número de amostras (cenário + contingência) para cada LT
    count_line_duals = {line_id: 0 for line_id in line_ids}
    
    # Itera sobre os cenários
    for scen in range(nscen):
        print(f"\n--- Processando Cenário {scen} ---")
        net_scen = copy.deepcopy(BASE_NET)
        
        apply_wnd_scen(net=net_scen, rng=rng)
        apply_load_scen(net=net_scen, rng=rng)
        
        # --- CASO BASE (N) ---
        print("    - Caso base sendo resolvido")
        solve_base = LinearDispatch(net_scen)
        status_base, final_cost, _ = solve_base.solve_loss()

        if status_base == 'Optimal':
            all_costs.append(final_cost)
            
            # 💡 ACUMULANDO DUAIS DO CASO BASE 💡
            duais_base = extract_line_duals(solve_base, net_scen)
            
            for line_id, dual_value in duais_base.items():
                sum_line_duals[line_id] += dual_value
                count_line_duals[line_id] += 1
            
            # Cálculo Caso Base (curtailment e deficit)
            defict_scen = 0
            for load in net_scen.loads:
                defict_scen += load.p_shed_var.value()
            all_deficits.append(defict_scen)

            curtailment_scen = 0
            for wnd_gen in net_scen.wind_generators:
                curtailment_scen += wnd_gen.p_max_pu - wnd_gen.p_var.value()
            all_curtailment.append(curtailment_scen)

            # --- CONTINGÊNCIAS (N-1) ---
            # Iteramos sobre a rede ORIGINAL (BASE_NET) para saber qual LT será contingenciada.
            for line in BASE_NET.lines:
                line_id_ctg = line.id
                
                print(f"    - Simulando contingência da linha: {line_id_ctg}")
                
                # A rede de contingência ctg_net é uma cópia da net_scen
                ctg_net = copy.deepcopy(net_scen)
                line_to_remove = next((l for l in ctg_net.lines if l.id == line_id_ctg), None)
                if line_to_remove: ctg_net.lines.remove(line_to_remove)
                
                solver_ctg = LinearDispatch(ctg_net)
                status_ctg, final_cost, _ = solver_ctg.solve_loss()
                
                if status_ctg == 'Optimal':
                    all_costs.append(final_cost)
                    
                    # CÁLCULO E ACUMULAÇÃO DE DUAIS DE FLUXO PARA AS LTs REMANESCENTES
                    duais = extract_line_duals(solver_ctg, ctg_net)
                    
                    # Acumula o dual apenas nas LTs que *permaneceram* no sistema
                    for rem_line in ctg_net.lines: # Itera sobre as LTs REMANESCENTES em ctg_net
                        rem_line_id = rem_line.id
                        dual_value = duais.get(rem_line_id, 0.0) # Usa o ID da LT da rede remanescente
                        
                        sum_line_duals[rem_line_id] += dual_value
                        count_line_duals[rem_line_id] += 1
                        
                    # Outros cálculos
                    deficit_ctg = 0
                    for load in ctg_net.loads:
                        deficit_ctg += load.p_shed_var.value()
                    all_deficits.append(deficit_ctg)

                    curtailment_ctg = 0
                    for wnd_gen in ctg_net.wind_generators:
                        curtailment_ctg += wnd_gen.p_max_pu - wnd_gen.p_var.value()
                    all_curtailment.append(curtailment_ctg)
                else:
                    print(f"    AVISO: Contingência para o cenário {scen} e ctg da linha {line_id_ctg} não convergiu.")

        else:
            print(f"    AVISO: Caso Base para o cenário {scen} não convergiu, contingências não rodadas.")


    # --- 7. Cálculo e Retorno (f) ---
    print("\n--- Resultados Finais ---")

    # Média de Custos
    if all_costs:
        mean_operational_cost = np.mean(all_costs)
        print(f"Mean Operational Cost: {mean_operational_cost:.2f}")

    if all_curtailment:
        mean_curtailment = np.mean(all_curtailment)
        print(f"Mean Curtailment: {mean_curtailment:.2f}")

    if all_deficits:
        mean_deficits = np.mean(all_deficits)
        print(f"Mean Deficits: {mean_deficits:.2f}")

    # --- CÁLCULO DAS MÉDIAS DOS DUAIS DE LT ---
    mean_line_duals = {}
    print("\n--- Média dos Multiplicadores de Lagrange (Fluxo) por LT ---")
    
    # A base de cálculo agora inclui N_{scen} casos-base + N_{scen} * (N_{linhas} - 1) contingências.
    for line_id in line_ids:
        total_dual = sum_line_duals[line_id]
        count = count_line_duals[line_id]
        
        if count > 0:
            mean_dual = total_dual / count
            mean_line_duals[line_id] = mean_dual
            print(f"LT {line_id}: {mean_dual:.4f} $/MWh (Baseado em {count} amostras)")
        else:
            mean_line_duals[line_id] = 0.0
            print(f"LT {line_id}: 0.0000 $/MWh (Sem amostras)")
            
    # return (mean_operational_cost + investimento_cost), mean_line_duals
    
if __name__ == "__main__":
    main()