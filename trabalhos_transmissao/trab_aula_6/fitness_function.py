import numpy as np
import copy
from power.systems.b6l8_charged import B6L8Charged  # Importa o sistema a ser estudado
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from metaheuristic.aoa_metaheuristic.optimizer import AOA


# --- 1. Configuração do Problema ---

# Carrega o sistema base. Usaremos cópias dele na função de fitness.
BASE_NET = B6L8Charged()

# Índices das linhas que são candidatas a receber reforço.
# Para o sistema B6L8, temos 8 linhas (índices 0 a 7). Vamos supor que todas são candidatas.
REINFORCEMENT_CANDIDATES_IDX = list(range(len(BASE_NET.lines)))

# Custo do reforço: Custo = FATOR * delta_x
# Vamos assumir um fator de custo simples por unidade de reatância reduzida.
# Este valor deve ser ajustado para refletir a realidade (e.g., R$/ohm)
COST_FACTOR_PER_UNIT_REACTANCE = 100 # Custo de 10.000 por 1.0 p.u. de reatância reduzida

# --- 2. Definição da Função de Fitness ---

def fitness_function(delta_x_vector: np.ndarray) -> float:
    """
    Calcula o custo total (reforço + operação) para um dado plano de reforço.
    
    Args:
        delta_x_vector: Vetor com os valores de redução de reatância para cada linha candidata.
    
    Returns:
        O custo total.
    """
    # a. Calcular o custo de investimento (reforço)
    investment_cost = np.sum(delta_x_vector * COST_FACTOR_PER_UNIT_REACTANCE)
    
    # b. Criar uma cópia profunda do sistema para não alterar o original
    net_copy = copy.deepcopy(BASE_NET)
    
    # c. Aplicar o reforço na cópia da rede
    for i, line_idx in enumerate(REINFORCEMENT_CANDIDATES_IDX):
        original_reactance = net_copy.lines[line_idx].x_pu
        # Garante que a reatância não se torne zero ou negativa
        new_reactance = max(original_reactance - delta_x_vector[i], 0.0001)
        net_copy.lines[line_idx].x_pu = new_reactance
        
    # d. Calcular o custo operacional com a rede modificada
    try:
        solver = LinearDispatch(net_copy)
        status, operational_cost, total_loss = solver.solve_loss()
        
        # Se a solução não for ótima, penaliza com um custo muito alto
        if status != 'Optimal':
            print("Aviso: Solução não ótima encontrada. Retornando custo elevado.")
            return float('inf')
            
    except Exception as e:
        print(f"Erro ao resolver o despacho: {e}. Retornando custo elevado.")
        return float('inf')

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
    pop_size = 20
    max_iter = 25
    
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