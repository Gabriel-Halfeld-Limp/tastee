import numpy as np
import copy
from power.systems import *  # Importa o sistema a ser estudado
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from metaheuristic.aoa_metaheuristic.optimizer import AOA
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from trabalhos_transmissao.utils.load_scen import apply_load_scen

from trabalhos_transmissao.trab_aula_4.utils.collect_results import collect_ctg_results
from trabalhos_transmissao.trab_aula_4.utils.save_results import save_ctg_results
# from opf_linear.utils.extract_results.extract_all import extract_all



# --- 1. Configuração do Problema ---

# Carrega o sistema base. Usaremos cópias dele na função de fitness.


# Índices das linhas que são candidatas a receber reforço.
# Para o sistema B6L8, temos 8 linhas (índices 0 a 7). Vamos supor que todas são candidatas.


# Custo do reforço: Custo = FATOR * delta_x
# Vamos assumir um fator de custo simples por unidade de reatância reduzida.
# Este valor deve ser ajustado para refletir a realidade (e.g., R$/ohm)
BASE_NET = B6L8Charged()
REINFORCEMENT_CANDIDATES_IDX = list(range(len(BASE_NET.lines)))
COST_FACTOR_PER_UNIT_REACTANCE = 100 # Custo de 10.000 por 1.0 p.u. de reatância reduzida

# --- 2. Definição da Função de Fitness ---
seed = 42
nscen = 3

# CÓDIGO SUGERIDO (Substituirá o conteúdo da sua função fitness_function)

def fitness_function(delta_x_vector: np.ndarray) -> float:
    """
    Calcula o custo total (reforço + operação) para um dado plano de reforço.
    """
    # print("Rodando Fitness Function de um novo indivíduo")

    rng = np.random.default_rng(seed=seed)
    
    # 1. Calcular o custo de investimento (a)
    all_costs = []
    all_curtailment = []
    all_deficits = []
    
    # Itera sobre os cenários
    for scen in range(nscen):
        # print(f"\n--- Processando Cenário {scen} ---")
        net_scen = copy.deepcopy(BASE_NET)
        for i, line in enumerate(net_scen.lines):
            delta_x = delta_x_vector[i]
            if delta_x > 0:
                new_reactance = max(line.x_pu - delta_x, 0.0001)
                line.flow_max_pu = line.flow_max_pu * line.x_pu / new_reactance 
                line.x_pu = new_reactance
        
        apply_wnd_scen(net=net_scen, rng=rng)
        apply_load_scen(net=net_scen, rng=rng)
        # print("    - Caso base sendo resolvido")
        solve_base = LinearDispatch(net_scen)
        status_base, final_cost, _ = solve_base.solve_loss()

        defict_scen = 0
        for load in net_scen.loads:
            defict_scen += load.p_shed_var.value()
        all_deficits.append(defict_scen)

        curtailment_scen = 0
        for wnd_gen in net_scen.wind_generators:
            curtailment_scen +=  wnd_gen.p_max_pu - wnd_gen.p_var.value()
        all_curtailment.append(curtailment_scen)

        if status_base != 'Optimal':
            print(f"    AVISO: Caso Base para o cenário {scen} não convergiu.")

        all_costs.append(final_cost)

        #Contingências
        for line in net_scen.lines: 
            # print(f"    - Simulando contingência da linha: {line.id}")
            ctg_net = copy.deepcopy(net_scen)    
            line_to_remove = next((l for l in ctg_net.lines if l.id == line.id), None)
            if line_to_remove: ctg_net.lines.remove(line_to_remove)
            solver_ctg = LinearDispatch(ctg_net)
            status_ctg, final_cost, _ = solver_ctg.solve_loss()
            if status_ctg == 'Optimal':
                all_costs.append(final_cost)
                deficit_ctg = 0
                for load in ctg_net.loads:
                    deficit_ctg += load.p_shed_var.value()
                all_deficits.append(deficit_ctg)

                curtailment_ctg = 0
                for wnd_gen in ctg_net.wind_generators:
                    curtailment_ctg +=  wnd_gen.p_max_pu - wnd_gen.p_var.value()
                all_curtailment.append(curtailment_ctg)
            else:
                print(f"    AVISO: Contingência para o cenário {scen} e ctg da linha {line.id} não convergiu.")

    # 7. Cálculo e Retorno (f)
    investment_cost = np.sum(delta_x_vector * COST_FACTOR_PER_UNIT_REACTANCE)
    operational_cost = np.mean(all_costs) # FOB média de todos os cenários e ctg.
    total_cost = investment_cost + operational_cost

    if all_costs:
        mean_operational_cost = np.mean(all_costs) # FOB média de todos os cenários e ctg.
        print(f"Mean Operational Cost: {mean_operational_cost:.2f}")

    if all_curtailment:
        mean_curtailment = np.mean(all_curtailment)
        print(f"Mean Curtailment: {mean_curtailment:.2f}")

    if all_deficits:
        mean_deficits = np.mean(all_deficits)
        print(f"Mean Deficits: {mean_deficits:.2f}")
    
    print(f"Custo Total: {total_cost:.2f} (Invest: {investment_cost:.2f}, Op: {operational_cost:.2f})")
    
    return total_cost

# --- 3. Configuração e Execução da Metaheurística AOA ---

if __name__ == "__main__":
    print("Iniciando a otimização de reforço de linhas de transmissão com AOA...")
    
    # Dimensão do problema: número de linhas candidatas
    dim = len(REINFORCEMENT_CANDIDATES_IDX)
    
    # Limites (bounds) para as variáveis de decisão (delta_x)
    # Limite inferior: 0 (sem reforço)
    lb = np.zeros(dim)
    # Limite superior: vamos definir como 70% da reatância original de cada linha
    ub = np.array([BASE_NET.lines[i].x_pu * 0.7 for i in REINFORCEMENT_CANDIDATES_IDX])

    # Parâmetros do AOA
    pop_size = 5
    max_iter = 15
    
    # Instanciar o otimizador
    aoa_optimizer = AOA(
        fitness_func=fitness_function,
        dim=dim,
        lb=lb,
        ub=ub,
        pop_size=pop_size,
        max_iter=max_iter
    )
    
    # Executar a otimização
    best_fitness, best_solution, convergence_curve = aoa_optimizer.solve()
    
    # --- 4. Apresentação dos Resultados ---
    
    print("\n" + "="*50)
    print("Otimização Concluída!")
    print(f"Melhor Custo Total Encontrado: {best_fitness:.2f}")
    print("="*50)
    
    print("\nPlano de Reforço Ótimo (redução de reatância):")
    for i, line_idx in enumerate(REINFORCEMENT_CANDIDATES_IDX):
        original_reactance = BASE_NET.lines[line_idx].x_pu
        reduction = best_solution[i]
        perc_reduction = (reduction / original_reactance) * 100
        print(f"  - Linha {BASE_NET.lines[line_idx].id}: Reduzir reatância em {reduction:.4f} p.u. ({perc_reduction:.2f}% do original)")

    # Plotar curva de convergência
    aoa_optimizer.plot_convergence(title="Convergência do Custo Total (Reforço + Operação)")