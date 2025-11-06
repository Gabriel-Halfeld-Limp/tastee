from power import WindGenerator, Network
import numpy as np

def apply_wnd_scen(net=Network, rng=np.random.default_rng(seed=42)):
    wnd_genrators = [g for g in net.generators if isinstance(g, WindGenerator)]
    num_wnd = len(wnd_genrators)
    if not wnd_genrators:
        return np.array([])
    base_wnd_p_max = np.array([g.p_max for g in wnd_genrators])
    random_factors = rng.random(num_wnd)
    scenario_wnd_p = base_wnd_p_max * random_factors

    for idx, wnd_object in enumerate(wnd_genrators):
        wnd_object.p_max = scenario_wnd_p[idx]