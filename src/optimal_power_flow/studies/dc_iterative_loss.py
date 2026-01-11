from pyomo.environ import *
import pandas as pd
import numpy as np
from optimal_power_flow.core.dc_physics import OPFDC
from power.systems.b3 import B3  # Supondo que você salvou a anterior aqui

class OPFIterativeLoss(OPFDC):
    """
    Estudo de Fluxo de Potência DC com Perdas Iterativas.
    Herda a física da rede de OPFDC e adiciona a lógica de iteração de perdas.
    """

    def __init__(self, network):
        super().__init__(network)
        # 1. Constrói a física (Variáveis e Restrições)
        self.build_physics()
        
        # 2. Constrói a Função Objetivo (Minimizar Custo)
        self.build_objective()

    def build_objective(self):
        """
        Define a função objetivo: Minimizar Custos Operativos (Geração + Shedding + Bateria)
        """
        m = self.model
        
        # Custo Geração Térmica
        cost_thermal = sum(m.p_thermal[g] * self.thermal_generators[g].cost_b_pu 
                           for g in m.THERMAL_GENERATORS)
        
        # Custo de Déficit (Shedding) - Penalidade alta
        cost_shed = sum(m.p_shed[l] * self.loads[l].cost_shed_pu 
                        for l in m.LOADS)
        
        # Custo Operacional de Bateria (Degradação/Ciclo)
        # Assumindo que cost_discharge_pu existe no objeto bateria
        cost_bess = sum(m.p_bess_out[g] * self.bess[g].cost_discharge_pu + 
                        m.p_bess_in[g] * self.bess[g].cost_charge_pu
                        for g in m.BESS)

        m.obj = Objective(expr=cost_thermal + cost_shed + cost_bess, sense=minimize)

    def _calculate_current_losses(self):
        """
        Calcula as perdas baseadas nos ângulos (theta) da solução ATUAL.
        Retorna:
            - new_bus_losses: dict {bus_name: loss_val}
            - total_loss: float
        """
        m = self.model
        new_bus_losses = {b: 0.0 for b in m.BUSES}
        total_loss = 0.0

        for l_name in m.LINES:
            line = self.lines[l_name]
            r = line.r_pu
            x = line.x_pu
            
            # Condutância série: g = r / (r^2 + x^2)
            denom = (r**2 + x**2)
            if denom == 0: continue
            
            g_series = r / denom
            
            # Pega valor numérico atual dos ângulos
            theta_from = value(m.theta[line.from_bus.name])
            theta_to = value(m.theta[line.to_bus.name])
            
            # Fórmula da Perda Ativa: P_loss = g * (theta_i - theta_j)^2
            p_loss = g_series * (theta_from - theta_to)**2
            
            # Distribui 50% para cada barra
            new_bus_losses[line.from_bus.name] += p_loss / 2.0
            new_bus_losses[line.to_bus.name]   += p_loss / 2.0
            total_loss += p_loss

        return new_bus_losses, total_loss

    def solve(self, solver_name='glpk', max_iter=20, tol=1e-4, verbose=True):
        """
        Executa o loop iterativo para convergência das perdas.
        """
        m = self.model
        opt = SolverFactory(solver_name)
        
        prev_total_loss = -1.0
        converged = False
        
        print(f"--- Iniciando DC-OPF com Perdas (Max Iter: {max_iter}) ---")

        for i in range(1, max_iter + 1):
            # 1. Resolver o problema
            results = opt.solve(m, tee=False) # tee=False para não poluir o terminal
            
            if (results.solver.status != SolverStatus.ok) and (results.solver.termination_condition != TerminationCondition.optimal):
                print(f"Iteração {i}: Falha no solver. Status: {results.solver.status}")
                break

            # 2. Calcular Perdas Reais baseadas no fluxo físico (Theta)
            bus_losses_map, current_total_loss = self._calculate_current_losses()
            
            # 3. Verificar Convergência
            diff = abs(current_total_loss - prev_total_loss)
            if verbose:
                cost = value(m.obj)
                print(f"Iter {i}: Custo=${cost:,.2f} | Perdas={current_total_loss*self.net.sb_mva:.2f} MW | Diff={diff:.2e}")

            if diff < tol:
                converged = True
                if verbose: print(">> Convergência atingida!")
                break
            
            # 4. Atualizar o Parâmetro (Aqui está a mágica do mutable=True)
            for b in m.BUSES:
                m.bus_loss_pu[b] = bus_losses_map[b]
                
            prev_total_loss = current_total_loss

        return self._extract_results(converged)

    def _extract_results(self, converged):
        """
        Formata os resultados em DataFrames amigáveis (Similar ao seu código antigo).
        """
        m = self.model
        base_mva = self.net.sb_mva
        
        def v(var): return value(var) if var is not None else 0.0

        # 1. Geração Térmica
        therm_data = []
        for g in m.THERMAL_GENERATORS:
            therm_data.append({
                "Name": g,
                "Bus": self.thermal_generators[g].bus.name,
                "P_Gen_MW": v(m.p_thermal[g]) * base_mva,
                "P_Max_MW": self.thermal_generators[g].p_max_pu * base_mva,
                "Cost": self.thermal_generators[g].cost_b_pu
            })
        df_thermal = pd.DataFrame(therm_data)

        # 2. Baterias
        bess_data = []
        for g in m.BESS:
            bess_data.append({
                "Name": g,
                "Bus": self.bess[g].bus.name,
                "P_Out_MW": v(m.p_bess_out[g]) * base_mva,
                "P_In_MW": v(m.p_bess_in[g]) * base_mva,
                "SOC_Final_MWh": (self.bess[g].soc_pu + v(m.p_bess_in[g]) - v(m.p_bess_out[g])) * base_mva, # Simplificado (dt=1h)
                "SOC_Initial_MWh": self.bess[g].soc_pu * base_mva
            })
        df_bess = pd.DataFrame(bess_data)

        # 3. Shed (corte de carga)
        shed_data = []
        total_shed = 0.0
        for l in m.LOADS:
            shed_val = v(m.p_shed[l]) * base_mva
            total_shed += shed_val
            shed_data.append({
                "Load": l,
                "Bus": self.loads[l].bus.name,
                "P_Shed_MW": shed_val,
                "P_Load_MW": v(m.load_p_pu[l]) * base_mva,
                "Cost_Shed": self.loads[l].cost_shed_pu
            })
        df_shed = pd.DataFrame(shed_data)

        # 4. Barras (CMO e Perdas)
        bus_data = []
        for b in m.BUSES:
            try:
                lmp = m.dual[m.NodalBalanceConstraint[b]] if hasattr(m, 'dual') else 0.0
            except:
                lmp = 0.0
            bus_data.append({
                "Bus": b,
                "Angle_Deg": np.rad2deg(v(m.theta[b])),
                "Loss_Allocated_MW": v(m.bus_loss_pu[b]) * base_mva,
                "CMO": lmp
            })
        df_bus = pd.DataFrame(bus_data)

        # 5. Linhas
        line_data = []
        for l in m.LINES:
            line_obj = self.lines[l]
            flow_val = v(m.flow[l])
            pct_load = (abs(flow_val) / line_obj.flow_max_pu) * 100 if line_obj.flow_max_pu > 0 else 0
            # Perda na linha (igual ao cálculo do _calculate_current_losses)
            r = line_obj.r_pu
            x = line_obj.x_pu
            denom = (r**2 + x**2)
            g_series = r / denom if denom > 0 else 0
            theta_from = v(m.theta[line_obj.from_bus.name])
            theta_to = v(m.theta[line_obj.to_bus.name])
            line_loss = g_series * (theta_from - theta_to) ** 2 * base_mva
            line_data.append({
                "Line": l,
                "From": line_obj.from_bus.name,
                "To": line_obj.to_bus.name,
                "Flow_MW": flow_val * base_mva,
                "Max_MW": line_obj.flow_max_pu * base_mva,
                "Loading_%": pct_load,
                "Loss_MW": line_loss
            })
        df_line = pd.DataFrame(line_data)

        # 6. Wind (se houver)
        wind_data = []
        for g in m.WIND_GENERATORS:
            wind_val = v(m.p_wind[g]) * base_mva
            wind_max = self.wind_generators[g].p_max_pu * base_mva
            wind_data.append({
                "Name": g,
                "Bus": self.wind_generators[g].bus.name,
                "P_Wind_MW": wind_val,
                "P_Max_MW": wind_max,
                "Curtailment_MW": wind_max - wind_val
            })
        df_wind = pd.DataFrame(wind_data)
        total_curtailment = df_wind["Curtailment_MW"].sum() if not df_wind.empty else 0.0

        # 7. Resumo
        total_loss = df_bus["Loss_Allocated_MW"].sum()
        resumo = pd.DataFrame({
            "Total_Cost_System": [value(m.obj)],
            "Total_Losses_MW": [total_loss],
            "Total_Curtailment_MW": [total_curtailment],
            "Total_Shed_MW": [total_shed]
        })

        return {
            "status": "Optimal" if converged else "Not Converged",
            "objective": value(m.obj),
            "thermal": df_thermal,
            "bess": df_bess,
            "wind": df_wind,
            "shed": df_shed,
            "bus": df_bus,
            "line": df_line,
            "Resumo": resumo
        }

# Exemplo de uso no seu script main:
if __name__ == "__main__":

    from power.systems import B3
    from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
    from power import *

    # Sistema Bateria e Eolico
    net = Network(sb_mva=100)
    bus1 = Bus(net, id=1, name="Bus 1")
    bus2 = Bus(net, id=2, name="Bus 2")
    line = Line(id=1, from_bus=bus1, to_bus=bus2, x_pu=0.1, flow_max_pu=90)
    wnd = WindGenerator(id=1, bus=bus2, p_max_mw=80)
    bat = Battery(id=1, bus=bus1, p_max_mw=100, p_min_mw=-100, capacity_mwh=100, soc_mwh=20, cost_charge_mw=-0.1, cost_discharge_mw=399)

    
    # --- Pyomo OPFIterativeLoss ---
    study = OPFIterativeLoss(net)
    study.model.dual = Suffix(direction=Suffix.IMPORT)
    results_pyomo = study.solve(verbose=True)
    print("\n==== Resultados Pyomo (OPFIterativeLoss) ====")
    for k, df in results_pyomo.items():
        if isinstance(df, pd.DataFrame):
            print(f"\n[{k}]\n{df}")

    # --- LinearDispatch (Pulp) ---
    solver = LinearDispatch(net)
    results_pulp = solver.solve_loss(verbose=True)
    print("\n==== Resultados Pulp (LinearDispatch) ====")
    for k, df in results_pulp.items():
        if isinstance(df, pd.DataFrame):
            print(f"\n[{k}]\n{df}")

    # --- Comparação ---
    print("\n--- COMPARAÇÃO PYOMO x PULP ---")
    # Custo total
    custo_pyomo = results_pyomo['Resumo']["Total_Cost_System"].iloc[0] if "Resumo" in results_pyomo else None
    custo_pulp = results_pulp["Resumo"]["Total_Cost_System"].iloc[0] if "Resumo" in results_pulp else None
    print(f"Custo Total Pyomo: {custo_pyomo:.4f}" if custo_pyomo is not None else "Custo Total Pyomo: N/A")
    print(f"Custo Total Pulp:  {custo_pulp:.4f}" if custo_pulp is not None else "Custo Total Pulp: N/A")

    # Perdas totais
    perdas_pyomo = results_pyomo['Resumo']["Total_Losses_MW"].iloc[0] if "Resumo" in results_pyomo else None
    perdas_pulp = results_pulp["Resumo"]["Total_Losses_MW"].iloc[0] if "Resumo" in results_pulp else None
    print(f"Perdas Totais Pyomo: {perdas_pyomo:.4f} MW" if perdas_pyomo is not None else "Perdas Totais Pyomo: N/A")
    print(f"Perdas Totais Pulp:  {perdas_pulp:.4f} MW" if perdas_pulp is not None else "Perdas Totais Pulp: N/A")

    # Despacho térmico
    print("\nDespacho Térmico Pyomo:")
    if not results_pyomo['thermal'].empty:
        print(results_pyomo['thermal'][["Name", "P_Gen_MW"]])
    else:
        print("Nenhum gerador térmico despachado.")

    print("\nDespacho Térmico Pulp:")
    if "Thermal_Generation" in results_pulp and not results_pulp["Thermal_Generation"].empty:
        print(results_pulp["Thermal_Generation"][["P_MW"]])
    else:
        print("Nenhum gerador térmico despachado.")

    # Shed (corte de carga)
    shed_pyomo = results_pyomo['Resumo']["Total_Shed_MW"].iloc[0] if "Resumo" in results_pyomo else None
    shed_pulp = results_pulp["Resumo"]["Total_Shed_MW"].iloc[0] if "Resumo" in results_pulp else None
    print(f"\nShed Pyomo: {shed_pyomo:.4f} MW" if shed_pyomo is not None else "Shed Pyomo: N/A")
    print(f"Shed Pulp:  {shed_pulp:.4f} MW" if shed_pulp is not None else "Shed Pulp: N/A")
