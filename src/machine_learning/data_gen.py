from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from tqdm import tqdm
from pyomo.environ import value, SolverFactory
from optimal_power_flow.studies.ac_multistep import OPFACMultiStep
from power.systems import *
from power import *

def generate_dataset_118(network: Network, n_scenarios=550, output_prefix="dataset_118", output_dir: str | Path | None = None):
    """
    Gera 550 cenários (24h cada).
    500 para Treino (dataset_118_train.parquet)
    50 para Teste (dataset_118_test.parquet)
    """
    
    # Perfis Base
    load_profile = np.array([0.7, 0.65, 0.6, 0.65, 0.75, 0.85, 0.95, 1.0, 1.05, 1.1, 1.08, 1.05, 1.02, 1.0, 0.98, 1.05, 1.15, 1.2, 1.18, 1.1, 1.0, 0.9, 0.8, 0.75])
    wind_profile = np.array([0.9, 0.95, 0.98, 0.92, 0.85, 0.8, 0.7, 0.6, 0.45, 0.3, 0.25, 0.35, 0.4, 0.3, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.8, 0.85, 0.88, 0.92])

    data_rows = []
    periods = 24

    base_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parents[2] / "trabalhos_transmissao" / "trab_aula_11_RNA"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_dir / f"{output_prefix}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"--- Iniciando Simulação {network.name} ({n_scenarios} cenários) ---")
    ipopt = SolverFactory("ipopt")
    if not ipopt.available(False):
        print("ERRO: Solver 'ipopt' não encontrado no PATH. Instale/configure o executável antes de rodar.")
        return
     
    for i in tqdm(range(n_scenarios), desc="Simulando"):
        try:
            # 1. Instancia Limpa
            net = network
            study = OPFACMultiStep(net, periods=periods)
            
            # 2. Estocasticidade (Carga e Vento Variáveis)
            scale_load = np.random.uniform(0.80, 1.20) 
            scale_wind = np.random.uniform(0.40, 1.10) 
            noise_load = np.random.normal(1.0, 0.03, periods)
            noise_wind = np.random.normal(1.0, 0.10, periods)

            # Aplica Cargas
            current_loads = {}
            for load in net.loads:
                series = load_profile * load.p_pu * scale_load * noise_load
                study.set_load_series(load.name, series)
                current_loads[load.name] = series

            # Aplica Ventos (e guarda o Disponível para calcular corte depois)
            current_winds_avail = {}
            for wnd in net.wind_generators:
                series = wind_profile * wnd.p_max_pu * scale_wind * noise_wind
                series = np.clip(series, 0, wnd.p_max_pu)
                study.set_wind_series(wnd.name, series)
                current_winds_avail[wnd.name] = series

            # 3. Resolve
            study.build_multistep_model()
            res = study.solve_multistep(solver_name='ipopt', tee=False, time_limit=60)
            
            if res is None or str(res.solver.termination_condition) != 'optimal':
                # print(f"Cenário {i} não convergiu.")
                continue 

            # 4. Extração de Dados
            m = study.model
            for t in range(periods):
                blk = m.period[t]
                row = {'scenario': i, 'hour': t}

                # --- INPUTS (O que a RNA "enxerga") ---
                # Carga (P e Q) e Vento Disponível
                for l in net.loads:
                    row[f'input_Pd_{l.name}'] = current_loads[l.name][t]
                
                for w in net.wind_generators:
                    row[f'input_PwindAvail_{w.name}'] = current_winds_avail[w.name][t]

                # Estado dos Geradores (Pg) - Slide pede Pg como input (medição)
                for g in net.thermal_generators:
                    row[f'input_Pg_{g.name}'] = value(blk.p_thermal[g.name])

                # --- TARGETS (O que a RNA prevê) ---
                
                # 1. Deficit (Total MW do sistema)
                total_shed = sum(value(blk.p_shed[l.name]) for l in net.loads)
                row['target_Deficit_Total'] = total_shed
                
                # 2. Curtailment (PCW) = Disponível - Gerado
                total_curtailment = 0
                for w in net.wind_generators:
                    avail = current_winds_avail[w.name][t]
                    gen = value(blk.p_wind[w.name])
                    cut = max(0, avail - gen)
                    row[f'target_PCW_{w.name}'] = cut
                    total_curtailment += cut
                
                row['target_PCW_Total'] = total_curtailment

                # 3. Tensão e Ângulo
                for b in net.buses:
                    row[f'target_V_{b.name}'] = value(blk.v_pu[b.name])
                    row[f'target_Th_{b.name}'] = value(blk.theta_rad[b.name])

                data_rows.append(row)

        except Exception as e:
            print(f"Erro Crítico Cenário {i}: {e}")
            continue

    df = pd.DataFrame(data_rows)
    if df.empty:
        print("Nenhum cenário viável gerado; nenhum arquivo salvo.")
        return None, None
    
    # Separação Treino (0-499) e Teste (500-549)
    # Assumindo 550 cenários
    scenarios = sorted(df['scenario'].unique())
    n_total = len(scenarios)
    n_train = int(n_total * 0.9) # Aprox 90% treino
    
    train_scenarios = scenarios[:n_train]
    test_scenarios = scenarios[n_train:]
    
    df_train = df[df['scenario'].isin(train_scenarios)]
    df_test = df[df['scenario'].isin(test_scenarios)]
    
    train_path = run_dir / f"{output_prefix}_train.parquet"
    test_path = run_dir / f"{output_prefix}_test.parquet"
    df_train.to_parquet(train_path)
    df_test.to_parquet(test_path)
    
    print(f"\nConcluído!")
    print(f"Arquivos salvos em: {run_dir}")
    print(f"Treino: {len(df_train)} amostras ({len(train_scenarios)} cenários)")
    print(f"Teste:  {len(df_test)} amostras ({len(test_scenarios)} cenários)")

    return train_path, test_path

if __name__ == "__main__":

    net = B6L8Charged()
    generate_dataset_118(network=net, n_scenarios=100, output_prefix="dataset_b6l8", output_dir=None)