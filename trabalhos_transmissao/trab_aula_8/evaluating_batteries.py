# This file uses batteries placed based on LMP results from defining_battery_place.py and sizes them in sizing_batteries.py
from copy import deepcopy
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from power import Network,  Battery
from power.systems import *
import numpy as np
from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen

B6 = B6L8Charged()
IEEE118 = IEEE118Charged()
nets = [B6, IEEE118]

# Rodando as 24 horas da simulação sem as baterias e armazenando os resultados

rng1 = np.random.default_rng(seed=42)
rng2 = np.random.default_rng(seed=41)
hours = 24

all_results = {net.name: [] for net in nets}
for net in nets:
    for h in range(hours):
        net_hour = deepcopy(net)
        apply_wnd_scen(net_hour, rng=rng1)
        apply_load_scen(net_hour, rng=rng2)
        solver = LinearDispatch(net_hour)
        results = solver.solve_loss()
        


