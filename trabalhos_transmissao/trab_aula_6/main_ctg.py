import numpy as np
import copy
from power.systems import *  # Importa o sistema a ser estudado
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from metaheuristic.aoa_metaheuristic.optimizer import AOA
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from trabalhos_transmissao.utils.load_scen import apply_load_scen

from trabalhos_transmissao.trab_aula_4.utils.collect_results import collect_ctg_results
from trabalhos_transmissao.trab_aula_4.utils.save_results import save_ctg_results
from opf_linear.utils.extract_results.extract_all import extract_all



# --- 1. Configuração do Problema ---

# Carrega o sistema base. Usaremos cópias dele na função de fitness.
BASE_NET = B3EOL()

# Índices das linhas que são candidatas a receber reforço.
# Para o sistema B6L8, temos 8 linhas (índices 0 a 7). Vamos supor que todas são candidatas.
REINFORCEMENT_CANDIDATES_IDX = list(range(len(BASE_NET.lines)))

# Custo do reforço: Custo = FATOR * delta_x
# Vamos assumir um fator de custo simples por unidade de reatância reduzida.
# Este valor deve ser ajustado para refletir a realidade (e.g., R$/ohm)
COST_FACTOR_PER_UNIT_REACTANCE = 100 # Custo de 10.000 por 1.0 p.u. de reatância reduzida

# --- 2. Definição da Função de Fitness ---
seed = 42
rng = np.random.default_rng(seed=seed)
nscen = 2

def fitness_function(delta_x_vector: np.ndarray) -> float:
    """
    Calcula o custo total (reforço + operação) para um dado plano de reforço.
    
    Args:
        delta_x_vector: Vetor com os valores de redução de reatância para cada linha candidata.
    
    Returns:
        O custo total.
    """
    # a. Calcular o custo de investimento (reforço)
    print("Rodando Fitness Function de um novo indivíduo")

    investment_cost = np.sum(delta_x_vector * COST_FACTOR_PER_UNIT_REACTANCE)
    all_costs = []
    for scen in range(nscen):
        print(f"\n--- Processando Cenário {scen} ---")
        # b. Criar uma cópia profunda do sistema para não alterar o original
        net_scen = copy.deepcopy(BASE_NET)
        # c. Aplicar o reforço na cópia da rede
        for i, line_idx in enumerate(REINFORCEMENT_CANDIDATES_IDX):
            original_reactance = net_scen.lines[line_idx].x_pu
            # Garante que a reatância não se torne zero ou negativa
            new_reactance = max(original_reactance - delta_x_vector[i], 0.0001)
            net_scen.lines[line_idx].x_pu = new_reactance
        
        apply_wnd_scen(net=net_scen, rng=rng)
        apply_load_scen(net=net_scen, rng=rng)
        print("    - Caso base sendo resolvido")
        solve_base = LinearDispatch(net_scen)
        status_base, final_cost, _ = solve_base.solve_loss()

        if status_base != 'Optimal':
            print(f"  AVISO: Caso Base para o cenário {scen} não convergiu.")

        all_costs.append(final_cost)
        
        # Apply ctg to this specif scenario
        for line in net_scen.lines: 
            print(f"    - Simulando contingência da linha: {line.id}")
            ctg_net = copy.deepcopy(net_scen)
            line_to_remove = next((l for l in ctg_net.lines if l.id == line.id), None)
            if line_to_remove: ctg_net.lines.remove(line_to_remove)

            solver_ctg = LinearDispatch(ctg_net)
            status_ctg, final_cost, _ = solver_ctg.solve_loss()
            if status_ctg == 'Optimal':
                all_costs.append(final_cost)
            else:
                print(f"  AVISO: Contingência para o cenário {scen} e ctg da linha {line.id} não convergiu.")

    #Media dos custos
    operational_cost = np.mean(all_costs)

    # e. Retornar o custo total
    total_cost = investment_cost + operational_cost
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
    pop_size = 3
    max_iter = 20
    
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