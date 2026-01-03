from power import WindGenerator, Network
import numpy as np

def apply_wnd_scen(net=Network, rng=np.random.default_rng(seed=42)):
    wnd_genrators = [g for g in net.generators if isinstance(g, WindGenerator)]
    num_wnd = len(wnd_genrators)
    if not wnd_genrators:
        return np.array([])
    base_wnd_p_max = np.array([g.p_max_pu for g in wnd_genrators])
    random_factors = rng.random(num_wnd)
    scenario_wnd_p = base_wnd_p_max * random_factors

    for idx, wnd_object in enumerate(wnd_genrators):
        wnd_object.p_max_pu = scenario_wnd_p[idx]


if __name__ == "__main__":
    from power.systems import B6L8EOL
    net = B6L8EOL()
    apply_wnd_scen(net, rng=np.random.default_rng(seed=42))

    print("Novos valores de p_max_pu para geradores eólicos:")
    for g in net.generators:
        if isinstance(g, WindGenerator):
            print(f"Gerador Eólico ID {g.id} na Barra {g.bus.id}: p_max_pu = {g.p_max_pu:.4f}")


    # Resetando para valores originais
    net = B6L8EOL()
    apply_wnd_scen(net, rng=np.random.default_rng(seed=42))
    print("\nValores originais de p_max_pu para geradores eólicos:")
    for g in net.generators:
        if isinstance(g, WindGenerator):
            print(f"Gerador Eólico ID {g.id} na Barra {g.bus.id}: p_max_pu = {g.p_max_pu:.4f}")