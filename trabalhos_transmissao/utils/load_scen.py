from power import Network
import numpy as np

def apply_load_scen(net=Network, ag=0.95, bg=1.10, ac=-0.02, bc=0.02, rng=np.random.default_rng(seed=42)):
    num_loads = len(net.loads)
    base_loads_p = np.array([load.p_pu for load in net.loads])
    rg = ag + (bg - ag) * rng.random(num_loads)  
    rc = ac + (bc - ac) * rng.random(num_loads) 

    # Calcular o fator de variação total 'r' somando os dois fatores 
    r = rg + rc
    scenario_loads = base_loads_p * r

    for idx, load_object in enumerate(net.loads):
        load_object.p_pu = scenario_loads[idx]