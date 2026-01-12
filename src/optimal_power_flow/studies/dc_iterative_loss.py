from pyomo.environ import *
import pandas as pd
import numpy as np
from optimal_power_flow.core.dc_physics import OPFDC
from power import Network
class OPFIterativeLoss(OPFDC):
    """
    Estudo de Fluxo de Potência DC com Perdas Iterativas.
    Herda a física da rede de OPFDC e adiciona a lógica de iteração de perdas.
    """

    def __init__(self, network: Network):
        super().__init__(network)
        # 1. Constrói a física (Variáveis e Restrições)
        self.build_physics()
        # 2. Constrói a Função Objetivo (Minimizar Custo)
        self.build_objective()
        
        # 3. IMPORTANTE: Prepara o container para receber os Multiplicadores de Lagrange (Duals)
        self.model.dual = Suffix(direction=Suffix.IMPORT)
        self.model.rc = Suffix(direction=Suffix.IMPORT) # Reduced Costs (para limites de variáveis)

    def build_objective(self):
        m = self.model
        
        # Custo Geração Térmica
        cost_thermal = sum(m.p_thermal[g] * self.thermal_generators[g].cost_b_pu 
                           for g in m.THERMAL_GENERATORS)
        
        # Custo de Déficit (Shedding)
        cost_shed = sum(m.p_shed[l] * self.loads[l].cost_shed_pu 
                        for l in m.LOADS)
        
        # Custo Operacional de Bateria
        cost_bess = sum(m.p_bess_out[g] * self.bess[g].cost_discharge_pu + 
                        m.p_bess_in[g] * self.bess[g].cost_charge_pu
                        for g in m.BESS)

        m.obj = Objective(expr=cost_thermal + cost_shed + cost_bess, sense=minimize)

    def _calculate_current_losses(self):
        """
        Calcula as perdas baseadas nos ângulos (theta) da solução ATUAL.
        """
        m = self.model
        new_bus_losses = {b: 0.0 for b in m.BUSES}
        total_loss = 0.0

        for l_name in m.LINES:
            line = self.lines[l_name]
            r = line.r_pu
            x = line.x_pu
            denom = (r**2 + x**2)
            if denom == 0: continue
            
            g_series = r / denom
            theta_from = value(m.theta[line.from_bus.name])
            theta_to = value(m.theta[line.to_bus.name])
            
            p_loss = g_series * (theta_from - theta_to)**2
            
            new_bus_losses[line.from_bus.name] += p_loss / 2.0
            new_bus_losses[line.to_bus.name]   += p_loss / 2.0
            total_loss += p_loss

        return new_bus_losses, total_loss

    def solve(self, solver_name='ipopt', max_iter=20, tol=1e-4, verbose=True):
        m = self.model
        opt = SolverFactory(solver_name)
        
        prev_total_loss = -1.0
        converged = False
        
        print(f"--- Iniciando DC-OPF com Perdas (Max Iter: {max_iter}) ---")

        for i in range(1, max_iter + 1):
            # Resolve
            results = opt.solve(m, tee=False)
            
            if (results.solver.status != SolverStatus.ok) and (results.solver.termination_condition != TerminationCondition.optimal):
                print(f"Iteração {i}: Falha no solver. Status: {results.solver.status}")
                break

            # Calcula Perdas Reais
            bus_losses_map, current_total_loss = self._calculate_current_losses()
            
            # Verifica Convergência
            diff = abs(current_total_loss - prev_total_loss)
            if verbose:
                cost = value(m.obj)
                print(f"Iter {i}: Custo=${cost:,.2f} | Perdas={current_total_loss*self.net.sb_mva:.2f} MW | Diff={diff:.2e}")

            if diff < tol:
                converged = True
                if verbose: print(">> Convergência atingida!")
                break
            
            # Atualiza Perdas (mutable param)
            for b in m.BUSES:
                m.bus_loss_pu[b] = bus_losses_map[b]
                
            prev_total_loss = current_total_loss

        return self._extract_results(converged)

    def _extract_results(self, converged):
        """
        Extrai resultados detalhados (Primal + Dual) em DataFrames.
        Versão corrigida com acesso seguro a Duals e Reduced Costs.
        """
        m = self.model
        sb = self.net.sb_mva
        
        # Helper para pegar valor seguro de variável
        def v(var): return value(var) if var is not None else 0.0
        
        # Helper SEGURO para pegar Dual (Constraint)
        # Ipopt às vezes não retorna dual se a restrição for inativa/redundante
        def get_dual(constraint):
            if hasattr(m, 'dual') and constraint in m.dual:
                return m.dual[constraint]
            return 0.0

        # Helper SEGURO para pegar Reduced Cost (Variable)
        # Essencial para evitar KeyError com Ipopt
        def get_rc(variable):
            if hasattr(m, 'rc') and variable in m.rc:
                return m.rc[variable]
            return 0.0

        # --- 1. GERAÇÃO TÉRMICA ---
        therm_data = []
        for g in m.THERMAL_GENERATORS:
            # CORREÇÃO AQUI: Usando get_rc()
            rc = get_rc(m.p_thermal[g])
            
            therm_data.append({
                "Name": g,
                "Bus": self.thermal_generators[g].bus.name,
                "P_MW": v(m.p_thermal[g]) * sb,
                "P_Max_MW": self.thermal_generators[g].p_max_pu * sb,
                "Cost": self.thermal_generators[g].cost_b_pu,
                "Reduced_Cost": rc 
            })
        df_thermal = pd.DataFrame(therm_data)

        # --- 2. EÓLICA ---
        wind_data = []
        for g in m.WIND_GENERATORS:
            p_val = v(m.p_wind[g])
            p_max = self.wind_generators[g].p_max_pu
            dual_max = get_dual(m.Wind_Max_Constraint[g])
            
            wind_data.append({
                "Name": g,
                "Bus": self.wind_generators[g].bus.name,
                "Available_MW": p_max * sb,
                "P_MW": p_val * sb,
                "Curtailment_MW": (p_max - p_val) * sb,
                "Dual_Max_Wind": dual_max
            })
        df_wind = pd.DataFrame(wind_data)

        # --- 3. BATERIAS ---
        bess_data = []
        for g in m.BESS:
            p_out = v(m.p_bess_out[g])
            p_in = v(m.p_bess_in[g])
            dual_soc_max = get_dual(m.BESS_SOC_Max_Constraint[g])
            dual_soc_min = get_dual(m.BESS_SOC_Min_Constraint[g])
            
            bess_data.append({
                "Name": g,
                "Bus": self.bess[g].bus.name,
                "P_Out_MW": p_out * sb,
                "P_In_MW": p_in * sb,
                "Final_SOC_MWh": (self.bess[g].soc_pu + p_in - p_out) * sb,
                "Dual_SOC_Max": dual_soc_max,
                "Dual_SOC_Min": dual_soc_min
            })
        df_bess = pd.DataFrame(bess_data)

        # --- 4. CORTES DE CARGA (SHEDDING) ---
        shed_data = []
        total_shed = 0.0
        for l in m.LOADS:
            shed_val = v(m.p_shed[l])
            total_shed += shed_val
            dual_shed_max = get_dual(m.Shed_Max_Constraint[l])
            
            shed_data.append({
                "Load": l,
                "Bus": self.loads[l].bus.name,
                "P_Shed_MW": shed_val * sb,
                "P_Load_MW": v(m.load_p_pu[l]) * sb,
                "Cost_Shed": self.loads[l].cost_shed_pu,
                "Dual_Shed_Limit": dual_shed_max
            })
        df_shed = pd.DataFrame(shed_data)

        # --- 5. BARRAS (LMP / CMO) ---
        bus_data = []
        for b in m.BUSES:
            lmp = get_dual(m.NodalBalanceConstraint[b])
            
            bus_data.append({
                "Bus": b,
                "Theta_deg": np.rad2deg(v(m.theta[b])),
                "LMP": lmp, 
                "Loss_Allocated_MW": v(m.bus_loss_pu[b]) * sb
            })
        df_bus = pd.DataFrame(bus_data)

        # --- 6. LINHAS ---
        line_data = []
        for l in m.LINES:
            line_obj = self.lines[l]
            flow_val = v(m.flow[l])
            
            # Perdas
            r = line_obj.r_pu
            x = line_obj.x_pu
            denom = r**2 + x**2
            g_series = r / denom if denom > 0 else 0
            theta_diff = v(m.theta[line_obj.from_bus.name]) - v(m.theta[line_obj.to_bus.name])
            loss_val = g_series * (theta_diff**2) * sb

            # Loading
            max_flow = line_obj.flow_max_pu
            loading = (abs(flow_val) / max_flow * 100) if max_flow > 0 else 0.0
            
            # CORREÇÃO AQUI: Usando get_rc() para fluxo
            rc_flow = get_rc(m.flow[l])

            line_data.append({
                "Line": l,
                "From": line_obj.from_bus.name,
                "To": line_obj.to_bus.name,
                "Flow_MW": flow_val * sb,
                "Max_MW": max_flow * sb,
                "Loading_%": loading,
                "Loss_MW": loss_val,
                "Congestion_Shadow_Price": rc_flow 
            })
        df_line = pd.DataFrame(line_data)

        # --- 7. RESUMO ---
        total_loss = df_bus["Loss_Allocated_MW"].sum()
        total_curtailment = df_wind["Curtailment_MW"].sum() if not df_wind.empty else 0.0
        
        resumo = pd.DataFrame({
            "Total_Cost": [value(m.obj)],
            "Total_Loss_MW": [total_loss],
            "Total_Curtailment_MW": [total_curtailment],
            "Total_Shed_MW": [total_shed * sb],
            "Status": ["Optimal" if converged else "Not Converged"]
        })

        return {
            "Resumo": resumo,
            "Thermal_Generation": df_thermal,
            "Wind_Generation": df_wind,
            "Battery": df_bess,
            "Load_Shed": df_shed,
            "Bus": df_bus,
            "Line": df_line,
            "Objective_Value": value(m.obj)
        }

if __name__ == "__main__":
    import pandas as pd
    from power import Network
    from power.systems.b3 import B3
    from power.systems.ieee14 import IEEE14

    # Configuração do Pandas para mostrar todas as colunas no terminal
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.4f}'.format)
    net = IEEE14()

    # 2. Instancia e Resolve
    print("\n>>> 2. Rodando OPF Iterativo (Perdas DC)...")
    study = OPFIterativeLoss(net)
    results = study.solve(solver_name='ipopt', verbose=True, max_iter=10)

    # 3. Print Resultados
    print("\n" + "="*100)
    print(f"RELATÓRIO FINAL - Status: {results['Resumo']['Status'].iloc[0]}")
    print("="*100)

    # Ordem lógica de impressão
    tables = [
        ("RESUMO DO SISTEMA", "Resumo"),
        ("BARRAS (LMP & Ângulos)", "Bus"),
        ("LINHAS (Fluxos, Perdas & Carregamento)", "Line"),
        ("GERAÇÃO TÉRMICA", "Thermal_Generation"),
        ("GERAÇÃO EÓLICA", "Wind_Generation"),
        ("BATERIAS", "Battery"),
        ("CORTE DE CARGA", "Load_Shed"),
    ]

    for title, key in tables:
        df = results.get(key)
        if df is not None and not df.empty:
            print(f"\n--- {title} ---")
            # Hackzinho pra formatar float no to_string
            print(df.to_string(float_format=lambda x: "{:.4f}".format(x) if isinstance(x, (float, int)) else str(x)))
        else:
            print(f"\n--- {title} ---\n(Sem dados)")

    print("\n" + "="*100)