from pyomo.environ import *
import pandas as pd
import numpy as np
from optimal_power_flow.core.ac_physics import OPFAC
from power import Network

class ACEconDispatch(OPFAC):
    """
    Pyomo model for AC Economic Dispatch problems.
    This class extends the OPFAC to include economic dispatch specific components.
    """

    def __init__(self, network: Network):
        super().__init__(network)
        self.build_physics()
        self.build_objective()


    def build_objective(self):
        """
        Define a função objetivo: Minimizar Custos Operativos (Geração + Shedding + Bateria)
        """
        m = self.model
        
        # Custo Geração Térmica
        cost_thermal = sum(
            self.thermal_generators[g].cost_a_pu +
            self.thermal_generators[g].cost_b_pu * m.p_thermal[g] +
            self.thermal_generators[g].cost_c_pu * (m.p_thermal[g]**2)
            for g in m.THERMAL_GENERATORS
        )
        
        # Custo de Déficit (Shedding) - Penalidade alta
        cost_shed = sum(m.p_shed[l] * self.loads[l].cost_shed_pu 
                        for l in m.LOADS)
        
        cost_q_shed = sum((m.q_shed[l]**2) * 10**8
                        for l in m.LOADS)
        
        # Custo Operacional de Bateria (Degradação/Ciclo)
        cost_bess = sum(m.p_bess_out[g] * self.bess[g].cost_discharge_pu + 
                        m.p_bess_in[g] * self.bess[g].cost_charge_pu
                        for g in m.BESS)

        m.obj = Objective(expr=cost_thermal + cost_shed + cost_q_shed + cost_bess , sense=minimize)
    
    def solve(self, solver_name: str = 'ipopt', verbose: bool = False, **kwargs):
        """
        Resolve o modelo Pyomo usando o solver especificado.
        """
        solver = SolverFactory(solver_name)
        results = solver.solve(self.model, tee=verbose, **kwargs)
        return results
    
    def _extract_results(self, converged):
        """
        Extrai resultados detalhados AC (P, Q, V, Theta, S) em DataFrames.
        Inclui visualização do Q_Virtual (Slack de Tensão).
        """
        m = self.model
        sb = self.net.sb_mva
        
        # --- Helpers ---
        def v(var): return value(var) if var is not None else 0.0
        
        def get_dual(constraint):
            if hasattr(m, 'dual') and constraint in m.dual: return m.dual[constraint]
            return 0.0

        def get_rc(variable):
            if hasattr(m, 'rc') and variable in m.rc: return m.rc[variable]
            return 0.0

        # --- 1. GERAÇÃO TÉRMICA ---
        therm_data = []
        for g in m.THERMAL_GENERATORS:
            p = v(m.p_thermal[g])
            q = v(m.q_thermal[g])
            therm_data.append({
                "Name": g, "Bus": self.thermal_generators[g].bus.name,
                "P_MW": p * sb, "Q_MVAr": q * sb, "S_MVA": (p**2 + q**2)**0.5 * sb,
                "P_Max": self.thermal_generators[g].p_max_pu * sb,
                "Q_Min": self.thermal_generators[g].q_min_pu * sb, "Q_Max": self.thermal_generators[g].q_max_pu * sb,
                "Cost": self.thermal_generators[g].cost_b_pu
            })
        df_thermal = pd.DataFrame(therm_data)

        # --- 2. EÓLICA ---
        wind_data = []
        for g in m.WIND_GENERATORS:
            p = v(m.p_wind[g])
            q = v(m.q_wind[g])
            wind_data.append({
                "Name": g, "Bus": self.wind_generators[g].bus.name,
                "P_MW": p * sb, "Q_MVAr": q * sb, "S_MVA": (p**2 + q**2)**0.5 * sb,
                "Available": self.wind_generators[g].p_max_pu * sb,
                "Curtailment": (self.wind_generators[g].p_max_pu - p) * sb
            })
        df_wind = pd.DataFrame(wind_data)

        # --- 3. BATERIAS ---
        bess_data = []
        for g in m.BESS:
            p_out = v(m.p_bess_out[g]); p_in = v(m.p_bess_in[g]); q = v(m.q_bess[g])
            bess_data.append({
                "Name": g, "Bus": self.bess[g].bus.name,
                "P_Out": p_out * sb, "P_In": p_in * sb, "Q_MVAr": q * sb,
                "SOC_Final": (self.bess[g].soc_pu + p_in - p_out) * sb
            })
        df_bess = pd.DataFrame(bess_data)

        # --- 4. SHEDDING & Q VIRTUAL (Aqui está a mudança) ---
        shed_data = []
        total_p_shed = 0.0
        total_q_virtual = 0.0
        
        for l in m.LOADS:
            p_shed_val = v(m.p_shed[l])
            q_virtual_val = v(m.q_shed[l]) # Slack Variable
            
            total_p_shed += p_shed_val
            total_q_virtual += abs(q_virtual_val) # Soma módulo para ver esforço total
            
            shed_data.append({
                "Load": l,
                "Bus": self.loads[l].bus.name,
                "P_Load_MW": v(m.load_p_pu[l]) * sb,
                "P_Shed_MW": p_shed_val * sb,
                "Q_Virtual_MVAr": q_virtual_val * sb, # Se for != 0, a tensão colapsou ali
                "Cost_P": self.loads[l].cost_shed_pu
            })
        df_shed = pd.DataFrame(shed_data)

        # --- 5. BARRAS ---
        bus_data = []
        for b in m.BUSES:
            bus_data.append({
                "Bus": b,
                "V_pu": v(m.v[b]),
                "Angle_deg": np.rad2deg(v(m.theta[b])),
                "LMP_P": get_dual(m.active_power_balance[b]),
                "LMP_Q": get_dual(m.reactive_power_balance[b])
            })
        df_bus = pd.DataFrame(bus_data)

        # --- 6. LINHAS ---
        line_data = []
        for l in m.LINES:
            line_obj = self.lines[l]
            p_from = v(m.p_flow_out[l]); q_from = v(m.q_flow_out[l])
            p_to = v(m.p_flow_in[l]); q_to = v(m.q_flow_in[l])
            
            line_data.append({
                "Line": l, "From": line_obj.from_bus.name, "To": line_obj.to_bus.name,
                "P_From": p_from * sb, "Q_From": q_from * sb,
                "P_Loss": (p_from + p_to) * sb,
                "Loading_%": ((p_from**2 + q_from**2)**0.5 / line_obj.flow_max_pu * 100) if line_obj.flow_max_pu > 0 else 0
            })
        df_line = pd.DataFrame(line_data)

        # --- 7. RESUMO ---
        resumo = pd.DataFrame({
            "Total_Cost": [value(m.obj)],
            "Total_P_Shed_MW": [total_p_shed * sb],
            "Total_Q_Virtual_MVAr": [total_q_virtual * sb], # Indicador de inviabilidade de tensão
            "Status": ["Optimal" if converged else "Not Converged"]
        })

        return {
            "Resumo": resumo, "Thermal_Generation": df_thermal, "Wind_Generation": df_wind,
            "Battery": df_bess, "Load_Shed": df_shed, "Bus": df_bus, "Line": df_line
        }

if __name__ == "__main__":
    import pandas as pd
    from power import Network
    # Assuming B3 is importable. If not, use the manual creation block from before.
    from power.systems.b3 import B3
    from power.systems.ieee14 import IEEE14

    # Pandas Configuration for clean terminal output
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.4f}'.format)

    print(">>> 1. Creating System (AC Mode)...")
    # Instantiate the network
    net = IEEE14()

    # 2. Instantiate and Solve
    print("\n>>> 2. Running AC Economic Dispatch (ACEconDispatch)...")
    
    # Create the study object
    study = ACEconDispatch(net)
    try:
        # Calls the solve wrapper we defined earlier
        # Ensure extracted_results is returned by this method
        results_raw = study.solve(solver_name='ipopt', verbose=True)
        
        # Extract results into DataFrames
        # Checks solver status to determine if converged
        is_optimal = (results_raw.solver.termination_condition == 'optimal')
        results = study._extract_results(converged=is_optimal)
        
    except Exception as e:
        print(f"\n❌ Solver Error: {e}")
        print("Ensure 'ipopt' is installed and in your system PATH.")
        exit()

    # 3. Print Results
    status_str = results['Resumo']['Status'].iloc[0]
    print("\n" + "="*100)
    print(f"FINAL REPORT - Status: {status_str}")
    print("="*100)

    # Logic print order matching the DC version
    tables = [
        ("SYSTEM SUMMARY", "Resumo"),
        ("BUSES (Voltage, Angle, LMPs)", "Bus"),
        ("LINES (Active/Reactive Flow, Losses, Loading)", "Line"),
        ("THERMAL GENERATION", "Thermal_Generation"),
        ("WIND GENERATION", "Wind_Generation"),
        ("BATTERIES", "Battery"),
        ("LOAD SHEDDING", "Load_Shed"),
    ]

    for title, key in tables:
        df = results.get(key)
        # Check if df is valid and not empty
        if df is not None and isinstance(df, pd.DataFrame) and not df.empty:
            print(f"\n--- {title} ---")
            # Using to_string with float formatter for clean alignment
            print(df.to_string(float_format=lambda x: "{:.4f}".format(x) if isinstance(x, (float, int)) else str(x)))
        else:
            print(f"\n--- {title} ---\n(No data)")

    print("\n" + "="*100)
    
    # Quick Health Check for AC Voltage
    if "Bus" in results and not results["Bus"].empty:
        v_min = results["Bus"]["V_pu"].min()
        v_max = results["Bus"]["V_pu"].max()
        print(f"Voltage Profile: Min {v_min:.4f} pu | Max {v_max:.4f} pu")
        
        if v_min < 0.94 or v_max > 1.05:
            print("⚠️  WARNING: Voltages are outside the typical 0.94-1.05 range!")
        else:
            print("✅ Voltages are within healthy limits.")

    #saving .lp
    # Salva todo o modelo (variáveis, restrições e objetivo) em um txt
    with open("modelo_debug.txt", "w") as f:
        study.model.pprint(ostream=f)
    

