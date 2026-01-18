import argparse
import numpy as np
import pandas as pd
from typing import Dict, Optional
from optimal_power_flow.studies.ac_multistep import OPFACMultiStep
from power import Network


def _sample_profile(base: float, sigma: float = 0.05) -> float:
    return max(0.0, np.random.normal(base, sigma * base))


def generate_ac_dataset(
    network: Network,
    periods: int = 24,
    n_samples: int = 100,
    load_profile_base: Optional[np.ndarray] = None,
    wind_profile_base: Optional[np.ndarray] = None,
    sigma_load: float = 0.1,
    sigma_wind: float = 0.1,
    solver_name: str = "ipopt",
    time_limit: Optional[int] = 120,
    tee: bool = False,
    out_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Gera um dataset AC resolvendo múltiplos cenários com OPFACMultiStep.

    Retorna um DataFrame com colunas de entrada (P_load, P_wind, P_thermal)
    e targets (V, theta, Q_gen, loading).
    """
    # Perfis base default (24h) se não fornecidos
    if load_profile_base is None:
        load_profile_base = np.ones(periods)
    if wind_profile_base is None:
        wind_profile_base = np.ones(periods)

    rows = []
    opf = OPFACMultiStep(network, periods=periods)
    opf.build_multistep_model()  # build once

    for sample in range(n_samples):
        # Perturba perfis
        load_profile = np.array([_sample_profile(v, sigma_load) for v in load_profile_base])
        wind_profile = np.array([_sample_profile(v, sigma_wind) for v in wind_profile_base])

        for load in network.loads:
            opf.set_load_series(load.name, load_profile * load.p_pu)
        for wnd in network.wind_generators:
            opf.set_wind_series(wnd.name, wind_profile * wnd.p_max_pu)

        # Solve (modelo já construído)
        res = opf.solve_multistep(solver_name=solver_name, time_limit=time_limit, tee=tee)
        status = getattr(res.solver[0], "termination_condition", None)
        if status and str(status).lower() not in {"optimal", "locallyoptimal", "optimalterminations"}:
            continue

        dfs = opf.extract_results_dataframe()
        gen = dfs["generation"]
        bus = dfs["bus"]
        load_df = dfs["load"]
        line = dfs["line"]

        # Merge por tempo
        for t in range(periods):
            g_t = gen[gen.time == t]
            b_t = bus[bus.time == t]
            l_t = load_df[load_df.time == t]
            ln_t = line[line.time == t]

            row: Dict[str, float] = {"sample": sample, "time": t}

            # Entradas: P_load, P_wind_max, P_thermal_decision
            for _, r in l_t.iterrows():
                row[f"load_{r.id}_p"] = r.p_load
            for _, r in g_t[g_t.type == "wind"].iterrows():
                row[f"wind_{r.id}_p"] = r.p_pu
            for _, r in g_t[g_t.type == "thermal"].iterrows():
                row[f"thermal_{r.id}_p"] = r.p_pu

            # Targets: V, theta, Q_gen, loading
            for _, r in b_t.iterrows():
                row[f"bus_{r.id}_v"] = r.v_pu
                row[f"bus_{r.id}_theta"] = r.theta_rad
            for _, r in g_t[g_t.type == "thermal"].iterrows():
                row[f"thermal_{r.id}_q"] = r.q_pu if "q_pu" in r else 0.0
            for _, r in g_t[g_t.type == "wind"].iterrows():
                row[f"wind_{r.id}_q"] = r.q_pu if "q_pu" in r else 0.0
            for _, r in g_t[g_t.type == "bess"].iterrows():
                row[f"bess_{r.id}_q"] = r.q_pu if "q_pu" in r else 0.0
            for _, r in ln_t.iterrows():
                row[f"line_{r.id}_loading"] = r.loading_percent

            rows.append(row)

    df = pd.DataFrame(rows)
    if out_path:
        if out_path.endswith(".parquet"):
            df.to_parquet(out_path, index=False)
        else:
            df.to_csv(out_path, index=False)
    return df


def _default_profiles(periods: int):
    load_profile_base = np.ones(periods)
    wind_profile_base = np.ones(periods)
    return load_profile_base, wind_profile_base


def _parse_args():
    p = argparse.ArgumentParser(description="Generate AC dataset via OPFACMultiStep")
    p.add_argument("--periods", type=int, default=24)
    p.add_argument("--samples", type=int, default=100)
    p.add_argument("--sigma-load", type=float, default=0.1)
    p.add_argument("--sigma-wind", type=float, default=0.1)
    p.add_argument("--solver", type=str, default="ipopt")
    p.add_argument("--time-limit", type=int, default=120)
    p.add_argument("--tee", action="store_true")
    p.add_argument("--out", type=str, default="data/ac_samples.parquet")
    p.add_argument("--system", type=str, default="B6L8Charged", help="power.systems class name")
    return p.parse_args()


def _load_system(system_name: str) -> Network:
    from power import systems
    if not hasattr(systems, system_name):
        raise ValueError(f"Sistema {system_name} não encontrado em power.systems")
    return getattr(systems, system_name)()


if __name__ == "__main__":
    args = _parse_args()
    net = _load_system(args.system)
    load_base, wind_base = _default_profiles(args.periods)
    df = generate_ac_dataset(
        net,
        periods=args.periods,
        n_samples=args.samples,
        load_profile_base=load_base,
        wind_profile_base=wind_base,
        sigma_load=args.sigma_load,
        sigma_wind=args.sigma_wind,
        solver_name=args.solver,
        time_limit=args.time_limit,
        tee=args.tee,
        out_path=args.out,
    )
    print(f"Geradas {len(df)} amostras e salvas em {args.out}")
