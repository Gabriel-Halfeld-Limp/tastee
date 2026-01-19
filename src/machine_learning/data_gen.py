import json
import numpy as np
import os
from tqdm import tqdm
from pyomo.environ import value, TerminationCondition

# Imports do seu sistema (Ajuste se mudar de sistema)
# from power.systems.ieee118_eolic import IEEE118Eolic  # Exemplo: Usando o sistema menor para teste rápido
from optimal_power_flow.studies.ac_multistep import OPFACMultiStep

def clean_value(val):
    """Remove ruído numérico do solver (ex: -1e-9 vira 0.0)"""
    if abs(val) < 1e-7:
        return 0.0
    return float(val)

def generate_dataset(network, n_scenarios, output_filename, is_test_set=False):
    """
    Gera dataset. Se is_test_set=True, aplica o ruído de medição nos INPUTS
    após a simulação (conforme Slide 10), mas mantém o simulation 'clean' 
    para obter os targets reais.
    """
    periods = 24
    net = network
    
    # Perfis Típicos
    load_profile_base = np.array([0.7, 0.65, 0.62, 0.60, 0.65, 0.75, 0.85, 0.95, 1.0, 1.05, 1.1, 1.08, 1.05, 1.02, 1.0, 0.98, 1.05, 1.15, 1.2, 1.18, 1.1, 1.0, 0.9, 0.8])
    wind_profile_base = np.array([0.9, 0.95, 0.98, 0.92, 0.85, 0.8, 0.7, 0.6, 0.45, 0.3, 0.25, 0.35, 0.4, 0.3, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.8, 0.85, 0.88, 0.92])

    dataset = []
    print(f"--- Gerando {output_filename} ({n_scenarios} cenários) ---")

    for i in tqdm(range(n_scenarios)):
        study = OPFACMultiStep(net, periods=periods)
        
        # --- Variabilidade Estocástica (Cenários) ---
        scale_load = np.random.uniform(0.8, 1.2)
        scale_wind = np.random.uniform(0.5, 1.2) # Vento varia mais
        
        noise_load = np.random.uniform(0.95, 1.05, periods)
        noise_wind = np.random.uniform(0.90, 1.10, periods)

        scenario_loads_p = {}
        scenario_loads_q = {}
        scenario_wind_avail = {}

        # Configura Cargas
        for load in net.loads:
            p_series = load_profile_base * load.p_pu * scale_load * noise_load
            # Mantém FP constante
            q_base = getattr(load, 'q_pu', 0.0)
            p_base_const = load.p_pu if load.p_pu > 1e-6 else 1.0
            ratio = q_base / p_base_const
            q_series = p_series * ratio
            
            study.set_load_series(load.name, p_series)
            scenario_loads_p[load.name] = p_series
            scenario_loads_q[load.name] = q_series

        # Configura Eólicas
        for wnd in net.wind_generators:
            w_series = wind_profile_base * wnd.p_max_pu * scale_wind * noise_wind
            w_series = np.clip(w_series, 0, wnd.p_max_pu)
            study.set_wind_series(wnd.name, w_series)
            scenario_wind_avail[wnd.name] = w_series

        # Resolve OPF
        study.build_multistep_model()
        
        # Injeta Q manualmente
        m = study.model
        for t in m.TIME:
            blk = m.period[t]
            for load in net.loads:
                if load.name in blk.load_q_pu:
                    blk.load_q_pu[load.name] = scenario_loads_q[load.name][t]

        res = study.solve_multistep(solver_name='ipopt', tee=False, time_limit=100)
        
        if res is None or str(res.solver.termination_condition) != 'optimal':
            continue

        # Extrai Dados
        for t in range(periods):
            blk = m.period[t]
            
            # Valores Reais da Simulação
            real_therm = {g.name: value(blk.p_thermal[g.name]) for g in net.thermal_generators}
            real_load_p = {l.name: scenario_loads_p[l.name][t] for l in net.loads}
            real_load_q = {l.name: scenario_loads_q[l.name][t] for l in net.loads}
            real_wind_av = {w.name: scenario_wind_avail[w.name][t] for w in net.wind_generators}
            
            # --- Aplicação de Ruído de Medição (Apenas se for Teste) ---
            # Slide 10: X_test = X_real * (1 + erro), erro ~ U(-0.02, 0.02)
            def apply_noise(val_dict):
                if not is_test_set: return val_dict
                return {k: val * np.random.uniform(0.98, 1.02) for k, val in val_dict.items()}

            input_therm = apply_noise(real_therm)
            
            # Carga input precisa ser separada P e Q para o noise
            input_load_p = apply_noise(real_load_p)
            input_load_q = apply_noise(real_load_q)
            
            # Reestrutura carga pro formato do JSON
            input_load_combined = {}
            for lname in real_load_p:
                input_load_combined[lname] = {
                    "p_pu": input_load_p[lname],
                    "q_pu": input_load_q[lname]
                }
            
            input_wind = apply_noise(real_wind_av)

            sample = {
                "scenario_id": i,
                "hour": t,
                "inputs": {
                    "thermal_gen_pu": input_therm,
                    "load_required": input_load_combined,
                    "wind_available_pu": input_wind
                },
                "outputs": {
                    "wind_curtailment_pu": {},
                    "load_deficit_pu": {},
                    "bus_voltage_pu": {}
                }
            }
            
            # Outputs (Targets SEMPRE SEM RUÍDO)
            if hasattr(blk, "q_thermal"):
                thermal_q = {}
                for g in net.thermal_generators:
                    thermal_q[g.name] = clean_value(value(blk.q_thermal[g.name]))
                sample["outputs"]["thermal_gen_q_pu"] = thermal_q

            for line in net.lines:
                limit = line.flow_max_pu
                current_s = None

                if hasattr(blk, 'p_flow_out') and hasattr(blk, 'q_flow_out'):
                    p_out = value(blk.p_flow_out[line.name])
                    q_out = value(blk.q_flow_out[line.name])
                    s_out = np.sqrt(p_out**2 + q_out**2)
                    p_in = value(blk.p_flow_in[line.name])
                    q_in = value(blk.q_flow_in[line.name])
                    s_in = np.sqrt(p_in**2 + q_in**2)
                    current_s = max(s_out, s_in)
                elif hasattr(blk, 'flow'):
                    current_s = abs(value(blk.flow[line.name]))

                if current_s is not None:
                    loading = current_s / limit if limit > 1e-6 else 0.0
                    sample["outputs"][f'line_loading_{line.name}_pu'] = clean_value(loading)


            for w in net.wind_generators:
                avail = real_wind_av[w.name]
                gen = value(blk.p_wind[w.name])
                sample["outputs"]["wind_curtailment_pu"][w.name] = clean_value(max(0, avail - gen))
            
            for l in net.loads:
                sample["outputs"]["load_deficit_pu"][l.name] = clean_value(value(blk.p_shed[l.name]))
            
            for b in net.buses:
                sample["outputs"]["bus_voltage_pu"][b.name] = clean_value(value(blk.v_pu[b.name]))
            
            dataset.append(sample)

    with open(output_filename, 'w') as f:
        json.dump(dataset, f, indent=2)
    print(f"Salvo: {output_filename} com {len(dataset)} amostras.")

if __name__ == "__main__":
    # Troque para IEEE118Eolic se for rodar o grandão
    from power.systems import *

    NET = B6L8()

    # Gera Treino (Sem ruído nos inputs)
    generate_dataset(NET, n_scenarios=50, output_filename="data_train.json", is_test_set=False)

    # Gera Teste (Com ruído nos inputs para simular erro de medição)
    generate_dataset(NET, n_scenarios=10, output_filename="data_test.json", is_test_set=True)