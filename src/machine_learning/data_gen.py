import pandas as pd
import numpy as np
from tqdm import tqdm
from pyomo.environ import value, SolverFactory

# Importa o sistema e o estudo AC
from power.systems import B6L8Charged 
from optimal_power_flow.studies.ac_multistep import OPFACMultiStep

def generate_dataset(n_scenarios=1000, output_path="dataset_ac.parquet"):
    """
    Gera dados sintéticos rodando o AC OPF Multistep.
    Recria o objeto de estudo a cada iteração para garantir independência dos cenários.
    """
    
    # Perfis Base
    load_profile = np.array([0.7, 0.65, 0.6, 0.65, 0.75, 0.85, 0.95, 1.0, 1.05, 1.1, 1.08, 1.05, 1.02, 1.0, 0.98, 1.05, 1.15, 1.2, 1.18, 1.1, 1.0, 0.9, 0.8, 0.75])
    wind_profile = np.array([0.9, 0.95, 0.98, 0.92, 0.85, 0.8, 0.7, 0.6, 0.45, 0.3, 0.25, 0.35, 0.4, 0.3, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.8, 0.85, 0.88, 0.92])

    data_rows = []
    periods = 24

    print(f"--- Iniciando Geração de {n_scenarios} Cenários AC ---")
    
    # Loop de Cenários
    for i in tqdm(range(n_scenarios), desc="Simulando"):
        try:
            # 1. SETUP LIMPO POR ITERAÇÃO (A CORREÇÃO PRINCIPAL)
            # Instanciamos o modelo do zero para evitar sujeira de memória do solver
            net = B6L8Charged()
            study = OPFACMultiStep(net, periods=periods)
            
            # --- A. Estocasticidade ---
            scale_load = np.random.uniform(0.8, 1.2)
            scale_wind = np.random.uniform(0.0, 1.0)
            
            noise_load = np.random.normal(1.0, 0.05, periods)
            noise_wind = np.random.normal(1.0, 0.10, periods)

            # Cargas
            current_loads = {}
            for load in net.loads:
                # Importante: Garantir tipos numéricos python/numpy padrão
                series = load_profile * load.p_pu * scale_load * noise_load
                study.set_load_series(load.name, series)
                current_loads[load.name] = series

            # Ventos
            current_winds = {}
            for wnd in net.wind_generators:
                series = wind_profile * wnd.p_max_pu * scale_wind * noise_wind
                series = np.clip(series, 0, wnd.p_max_pu)
                study.set_wind_series(wnd.name, series)
                current_winds[wnd.name] = series

            # --- B. Resolve ---
            # Constrói o modelo JÁ COM OS DADOS NOVOS injetados na criação se possível, 
            # ou constrói e o solver aplica os dados via _apply_time_series_data internamente.
            study.build_multistep_model()
            
            res = study.solve_multistep(solver_name='ipopt', tee=False)
            
            # Verificação de status robusta
            status = str(res.solver.termination_condition)
            if status != 'optimal':
                # Descomente para ver o erro específico se precisar
                # print(f"Cenário {i} não convergiu: {status}") 
                continue 

            # --- C. Extração ---
            m = study.model
            for t in range(periods):
                blk = m.period[t]
                row = {'scenario': i, 'hour': t}

                # Inputs (X)
                for l in net.loads:
                    row[f'input_Pd_{l.name}'] = current_loads[l.name][t]
                
                for w in net.wind_generators:
                    row[f'input_Pwind_{w.name}'] = current_winds[w.name][t]

                for g in net.thermal_generators:
                    row[f'input_Pg_{g.name}'] = value(blk.p_thermal[g.name])
                
                for b in net.batteries:
                    p_inj = value(blk.p_bess_out[b.name]) - value(blk.p_bess_in[b.name])
                    row[f'input_Pg_{b.name}'] = p_inj

                # Outputs (Y)
                for b in net.buses:
                    row[f'target_V_{b.name}'] = value(blk.v_pu[b.name])
                    row[f'target_Th_{b.name}'] = value(blk.theta_rad[b.name])

                for g in net.thermal_generators:
                    row[f'target_Qg_{g.name}'] = value(blk.q_thermal[g.name])
                
                for ln in net.lines:
                    p = value(blk.p_flow_out[ln.name])
                    q = value(blk.q_flow_out[ln.name])
                    s = (p**2 + q**2)**0.5
                    limit = ln.flow_max_pu
                    loading = (s / limit * 100) if limit and limit > 0 else 0.0
                    row[f'target_Loading_{ln.name}'] = loading

                data_rows.append(row)

        except Exception as e:
            print(f"Erro crítico no cenário {i}: {e}")
            continue

    if not data_rows:
        print("Nenhum cenário convergiu! Verifique se o Ipopt está instalado corretamente.")
        return None

    df = pd.DataFrame(data_rows)
    df.to_parquet(output_path)
    
    print(f"\nSucesso! Dataset salvo em: {output_path}")
    print(f"Cenários válidos: {len(df) / periods:.0f} de {n_scenarios}")
    
    return df

if __name__ == "__main__":
    generate_dataset(n_scenarios=1000, output_path="teste_dataset.parquet")