from power.systems import *
from power import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
import numpy as np
import copy
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from trabalhos_transmissao.utils.load_scen import apply_load_scen


BASE_NET = B3EOL()
seed = 42
rng = np.random.default_rng(seed=seed)
nscen = 2
all_costs = []

for scen in range(nscen):
    print(f"\n--- Processando Cenário {scen} ---")
    # b. Criar uma cópia profunda do sistema para não alterar o original
    net_scen = copy.deepcopy(BASE_NET)
    # c. Aplicar o reforço na cópia da rede

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
total_cost =  operational_cost
print(f"Custo Total: {total_cost:.2f}")