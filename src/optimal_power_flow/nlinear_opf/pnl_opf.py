from power import Network, ThermalGenerator, BusType
import numpy as np
import pandas as pd
import pulp as pl

class OptimizationError(RuntimeError):
    """Raised when the LP/MIP solver does not find an optimal solution within an iteration."""
    pass

class ConvergenceError(RuntimeError):
    """Raised when the outer fixed-point iteration on losses does not converge within the maximum number of iterations."""
    pass

class PNLOPF:
    def __init__(self, net: Network):
        """
        Inicializa e constrói o problema de despacho econômico linear para uma dada rede.
        """
        self.net = net
        self.problem = None

        # RNG da classe
        self.rng = np.random.default_rng(seed=42)
    # ----------------------------------------------------------------OBJECTIVE FUNCTIONS------------------------------------------------------------------------------------#
    def _fob_pnl_econ_dispatch(self):
        """Define a função objetivo do problema (minimizar custo total)."""
        thermal_cost = pl.lpSum([g.cost_b_pu * g.p_var for g in self.net.thermal_generators])
        shedding_cost = pl.lpSum([l.cost_shed_pu * l.p_shed_var for l in self.net.loads if hasattr(l, 'p_shed_var')])
        battery_out = pl.lpSum([b.cost_discharge_pu * b.p_out_var for b in self.net.batteries if hasattr(b, 'p_out_var')])
        battery_in = pl.lpSum([b.cost_charge_pu * b.p_in_var for b in self.net.batteries if hasattr(b, 'p_in_var')])
        self.problem += thermal_cost + shedding_cost + battery_out + battery_in, "Min_Total_System_Cost"
    
    def _fob_min_loss(self):
        self.problem += pl.lpSum([g.p_var for g in self.net.generators]), "Min_Loss"

    # ----------------------------------------------------------------CREATE VARIABLES------------------------------------------------------------------------------------#
    def _create_theta_variable(self):
        # Ângulo das Barras
        for b in self.net.buses:
                if b.btype == BusType.SLACK:
                    b.theta_var = pl.LpVariable(f"Theta{b.id}")
                    self.problem += b.theta_var <=  0, f"Constraint_Theta_{b.id}_Upper"
                    self.problem += b.theta_var >= 0, f"Constraint_Theta_{b.id}_Lower"
                    b.theta_var.setInitialValue(0)   
                else:
                    b.theta_var = pl.LpVariable(f"Theta{b.id}")
                    self.problem += b.theta_var <=  np.pi, f"Constraint_Theta_{b.id}_Upper"
                    self.problem += b.theta_var >= -np.pi, f"Constraint_Theta_{b.id}_Lower"
                    b.theta_var.setInitialValue(0)   

    def _create_flow_variable(self):
        for line in self.net.lines:
            line.flow_var = pl.LpVariable(f"Flow_{line.id}")
            self.problem += line.flow_var <=  line.flow_max_pu, f"Constraint_Flow_{line.id}_Upper"
            self.problem += line.flow_var >= -line.flow_max_pu, f"Constraint_Flow_{line.id}_Lower"
            self.problem += line.flow_var == ((line.from_bus.theta_var - line.to_bus.theta_var) / line.x_pu), f"Constraint_Flow_{line.id}"
    
    def _create_generation_variable(self):
        for g in self.net.thermal_generators:
            g.p_var = pl.LpVariable(f"P{g.id}")
            self.problem += g.p_var <= g.p_max_pu, f"Constraint_P{g.id}_Upper"
            self.problem += g.p_var >= g.p_min_pu, f"Constraint_P{g.id}_Lower"
        
        for g in self.net.wind_generators:
            g.p_var = pl.LpVariable(f"P{g.id}")
            self.problem += g.p_var <= g.p_max_pu, f"Constraint_P{g.id}_Upper"
            self.problem += g.p_var >= g.p_min_pu, f"Constraint_P{g.id}_Lower"


    def _create_load_shed_variable(self):
        for l in self.net.loads:
            l.p_shed_var = pl.LpVariable(f"L_shed{l.id}")
            self.problem += l.p_shed_var <= l.p_pu, f"Constraint_P_Shed{l.id}_Upper"
            self.problem += l.p_shed_var >= 0,      f"Constraint_P_Shed{l.id}_Lower"

    def _create_battery_variable(self):
        for b in self.net.batteries:
            # Battery Discharge Variable
            b.p_out_var = pl.LpVariable(f"P_Out{b.id}")
            # Discharge limits
            self.problem += b.p_out_var <= b.p_max_pu, f"Constraint_P_Out{b.id}_Upper"
            self.problem += b.p_out_var >= 0,          f"Constraint_P_Out{b.id}_Lower"

            # Battery Charge Variable
            b.p_in_var = pl.LpVariable(f"P_In{b.id}")
            # Charge limits
            self.problem += b.p_in_var <= -b.p_min_pu, f"Constraint_P_In{b.id}_Upper"
            self.problem += b.p_in_var >= 0,           f"Constraint_P_In{b.id}_Lower"

            # Battery SOC Constraint
            self.problem += b.p_in_var + b.soc_pu <= b.capacity_pu, f"Constraint_SOC_{b.id}_Upper"
            self.problem += b.soc_pu - b.p_out_var >= 0,            f"Constraint_SOC_{b.id}_Lower"

    # ----------------------------------------------------------------CREATE CONSTRAINTS------------------------------------------------------------------------------------#
    def _nodal_power_balance(self):
        for b in self.net.buses:
            thermal_generation = pl.lpSum([g.p_var for g in b.thermal_generators])
            wind_generation = pl.lpSum([g.p_var for g in b.wind_generators])
            bat_generation = pl.lpSum([ (batt.p_out_var) for batt in b.batteries])
            bat_charge = pl.lpSum([ (batt.p_in_var) for batt in b.batteries])
            generation = thermal_generation + wind_generation + bat_generation - bat_charge
            load_shed = pl.lpSum([l.p_shed_var for l in b.loads])
            flow_in = pl.lpSum([(l.from_bus.theta_var - b.theta_var) / l.x_pu for l in self.net.lines if l.to_bus == b])
            flow_out = pl.lpSum([(b.theta_var - l.to_bus.theta_var) / l.x_pu for l in self.net.lines if l.from_bus == b])
            load = sum([l.p_pu for l in b.loads]) + b.loss
            self.problem += generation + load_shed + flow_in - flow_out == load, f"B{b.id}_Power_Balance"

    # ----------------------------------------------------------------UTILS------------------------------------------------------------------------------------------------#
    def _update_losses(self):
        """
        Calcula as perdas com base nos ângulos da solução atual e as atualiza nas barras.
        Retorna o valor total das perdas calculadas.
        """
        current_total_loss = 0
        # 1. Zera as perdas da iteração anterior em todas as barras
        for b in self.net.buses:
            b.loss = 0

        # 2. Calcula e distribui as novas perdas
        for l in self.net.lines:
            r = l.r_pu
            x = l.x_pu
            g_series = r / (r**2 + x**2) if (r**2 + x**2) > 0 else 0
            dtheta = l.from_bus.theta_var.value() - l.to_bus.theta_var.value()
            line_loss = g_series * (dtheta ** 2)
            l.loss = line_loss
            current_total_loss += line_loss

            # Atribui metade da perda para cada barra da linha
            l.from_bus.loss += line_loss / 2
            l.to_bus.loss += line_loss / 2

        return current_total_loss

    def _update_flow_sign(self):
        for line in self.net.lines:
            if line.from_bus.theta_var.value() > line.to_bus.theta_var.value(): # Fluxo de "FROM" para "TO"
                line.flow_sign = 1
            elif line.from_bus.theta_var.value() < line.to_bus.theta_var.value(): #Fluxo de "TO" para "FROM"
                line.flow_sign = -1
            elif line.from_bus.theta_var.value() == line.to_bus.theta_var.value(): #Fluxo 0
                line.flow_sign = 0
            else:
                raise ValueError(f"Fluxo não foi corretamente calculado, o sentido do fluxo não é negativo, nem positivo, nem zero")
            
    def _extract_results(self, FOB_value: float = None) -> dict:
        """Extrai os resultados das variáveis de decisão após a resolução do problema."""
        #Variáveis primais e duais dos geradores térmicos:
        thermal_gen_results = {g.name: {
            "P_MW": g.p_var.value() * self.net.sb_mva,
            "Dual_Lower_Cost": self.problem.constraints[f"Constraint_P{g.id}_Lower"].pi,
            "Dual_Upper_Cost": self.problem.constraints[f"Constraint_P{g.id}_Upper"].pi
        } for g in self.net.thermal_generators}

        # Variáveis Primais e duais dos geradores eólicos:
        wind_gen_results = {g.name: {
            "Avaible_MW": g.p_max_pu * self.net.sb_mva,
            "P_MW": g.p_var.value() * self.net.sb_mva,
            "Curtailment_MW": (g.p_max_pu - g.p_var.value()) * self.net.sb_mva,
            "Dual_Lower_Cost": self.problem.constraints[f"Constraint_P{g.id}_Lower"].pi,
            "Dual_Upper_Cost": self.problem.constraints[f"Constraint_P{g.id}_Upper"].pi
        } for g in self.net.wind_generators}

        # Variáveis Primais e duais das baterias:
        battery_results = {b.name: {
            "P_Out_MW": b.p_out_var.value() * self.net.sb_mva,
            "P_In_MW": b.p_in_var.value() * self.net.sb_mva,
            "Initial_SOC_MWh": b.soc_mwh,
            "Final_SOC_MWh": b.soc_mwh + (b.p_in_var.value() - b.p_out_var.value()) * self.net.sb_mva,
            "Dual_Lower_Out": self.problem.constraints[f"Constraint_P_Out{b.id}_Lower"].pi,
            "Dual_Upper_Out": self.problem.constraints[f"Constraint_P_Out{b.id}_Upper"].pi,
            "Dual_Lower_In": self.problem.constraints[f"Constraint_P_In{b.id}_Lower"].pi,
            "Dual_Upper_In": self.problem.constraints[f"Constraint_P_In{b.id}_Upper"].pi,
            "Dual_Lower_SOC": self.problem.constraints[f"Constraint_SOC_{b.id}_Lower"].pi,
            "Dual_Upper_SOC": self.problem.constraints[f"Constraint_SOC_{b.id}_Upper"].pi,
        } for b in self.net.batteries}

        # Variáveis Primais e duais dos cortes de carga:
        load_shed_results = {l.name: {
            "P_MW": l.p_pu * self.net.sb_mva,
            "P_Shed_MW": l.p_shed_var.value() * self.net.sb_mva,
            "Dual_Lower_Cost": self.problem.constraints[f"Constraint_P_Shed{l.id}_Lower"].pi,
            "Dual_Upper_Cost": self.problem.constraints[f"Constraint_P_Shed{l.id}_Upper"].pi,
        } for l in self.net.loads}

        # Variáveis Primais e duais das linhas:
        line_results = {f"Line {l.id} ({l.from_bus.id}->{l.to_bus.id})": {
            "Flow_MW": l.flow_var.value() * self.net.sb_mva,
            "Losses_MW": l.loss * self.net.sb_mva,
            "Dual_Lower_Cost": self.problem.constraints[f"Constraint_Flow_{l.id}_Lower"].pi,
            "Dual_Upper_Cost": self.problem.constraints[f"Constraint_Flow_{l.id}_Upper"].pi,
        } for l in self.net.lines}

        # Variáveis Primais e duais das barras:
        bus_results = {b.name: {
            "Theta_deg": float(np.rad2deg(b.theta_var.value())),
            "Local_Marginal_Price": self.problem.constraints[f"B{b.id}_Power_Balance"].pi,
            "Losses_MW": b.loss * self.net.sb_mva,
            "Dual_Lower_Angle": self.problem.constraints[f"Constraint_Theta_{b.id}_Lower"].pi,
            "Dual_Upper_Angle": self.problem.constraints[f"Constraint_Theta_{b.id}_Upper"].pi,
        } for b in self.net.buses}

        # Retorna todos os dados em um dicionário com DataFrames separados
        results = {
            "Thermal_Generation": pd.DataFrame(thermal_gen_results).T if thermal_gen_results else pd.DataFrame(),
            "Wind_Generation": pd.DataFrame(wind_gen_results).T if wind_gen_results else pd.DataFrame(),
            "Battery": pd.DataFrame(battery_results).T if battery_results else pd.DataFrame(),
            "Load_Shed": pd.DataFrame(load_shed_results).T if load_shed_results else pd.DataFrame(),
            "Line": pd.DataFrame(line_results).T if line_results else pd.DataFrame(),
            "Bus": pd.DataFrame(bus_results).T if bus_results else pd.DataFrame(),
            "FOB_Value": FOB_value
        }

        return results
    
    # ----------------------------------------------------------------SOLVING----------------------------------------------------------------------------------------------#
    def solve_min_loss(self, verbose=False, detailed_output=False):
        self.problem = pl.LpProblem("Min_Loss", pl.LpMinimize)
        self._create_theta_variable()
        self._create_flow_variable()
        self._create_generation_variable()
        self._create_load_shed_variable()
        self._fob_min_loss()
        self._nodal_power_balance() 
        self.problem.solve(pl.PULP_CBC_CMD(msg=False)) 
        if self.problem.status == pl.LpStatusOptimal:
            results = self._extract_results(pl.value(self.problem.objective))
            if verbose:
                print("Solução encontrada.")
                print("Custo Total do Sistema: {:.4f}".format(pl.value(self.problem.objective)))
                if getattr(self.net, 'wind_generators', []):
                    print(f"Curtailment Total: {sum((g.p_max_pu - g.p_var.value()) * self.net.sb_mva for g in self.net.wind_generators):.4f} MW")
                print(f"Shed Total: {sum(l.p_shed_var.value() * self.net.sb_mva for l in self.net.loads):.4f} MW")
                if detailed_output:
                    if not results["Thermal_Generation"].empty:
                        print("\n--- Geradores Térmicos ---")
                        print(results["Thermal_Generation"])
                    if not results["Wind_Generation"].empty:
                        print("\n--- Geradores Eólicos ---")
                        print(results["Wind_Generation"])
                    if not results["Load_Shed"].empty:
                        print("\n--- Cortes de Carga ---")
                        print(results["Load_Shed"])
                    if not results["Line"].empty:
                        print("\n--- Linhas ---")
                        print(results["Line"])
                    if not results["Bus"].empty:
                        print("\n--- Barras ---")
                        print(results["Bus"])
            return results
        else:
            raise OptimizationError(
                f"Solução ótima não encontrada em solve_min_loss. Status: {pl.LpStatus[self.problem.status]}"
            )

    def solve_econ_dispatch(self, verbose=False, detailed_output=False):
        self.problem = pl.LpProblem("Economic_Dispatch", pl.LpMinimize)
        self._create_theta_variable()
        self._create_flow_variable()
        self._create_generation_variable()
        self._create_load_shed_variable()
        self._fob_linear_econ_dispatch()
        self._nodal_power_balance() 
        self.problem.solve(pl.PULP_CBC_CMD(msg=False))
        if self.problem.status == pl.LpStatusOptimal:
            results = self._extract_results(pl.value(self.problem.objective))
            if verbose:
                print("Solução encontrada.")
                print("Custo Total do Sistema: {:.4f}".format(pl.value(self.problem.objective)))
                if getattr(self.net, 'wind_generators', []):
                    print(f"Curtailment Total: {sum((g.p_max_pu - g.p_var.value()) * self.net.sb_mva for g in self.net.wind_generators):.4f} MW")
                print(f"Shed Total: {sum(l.p_shed_var.value() * self.net.sb_mva for l in self.net.loads):.4f} MW")
                if detailed_output:
                    if not results["Thermal_Generation"].empty:
                        print("\n--- Geradores Térmicos ---")
                        print(results["Thermal_Generation"])
                    if not results["Wind_Generation"].empty:
                        print("\n--- Geradores Eólicos ---")
                        print(results["Wind_Generation"])
                    if not results["Load_Shed"].empty:
                        print("\n--- Cortes de Carga ---")
                        print(results["Load_Shed"])
                    if not results["Line"].empty:
                        print("\n--- Linhas ---")
                        print(results["Line"])
                    if not results["Bus"].empty:
                        print("\n--- Barras ---")
                        print(results["Bus"])
            return results
        else:
            raise OptimizationError(
                f"Solução ótima não encontrada em solve_min_loss. Status: {pl.LpStatus[self.problem.status]}"
            )

    def solve_loss(self, iter_max=100, max_tol=1e-6, verbose=False, detailed_output=False):
        """
        Resolve o despacho econômico de forma iterativa para incluir as perdas da rede.
        """
        self.problem = pl.LpProblem("Linear_Economic_Dispatch", pl.LpMinimize)
        self._create_theta_variable()
        self._create_flow_variable()
        self._create_generation_variable()
        self._create_load_shed_variable()
        self._create_battery_variable()
        self._fob_linear_econ_dispatch()
        self._nodal_power_balance() 
        prev_total_loss = 0
        for i in range(1, iter_max + 1):
            self.problem.solve(pl.PULP_CBC_CMD(msg=False))
            if self.problem.status != pl.LpStatusOptimal:
                raise OptimizationError(
                    f"Solução ótima não encontrada durante a iteração {i} do solver com perdas. Status: {pl.LpStatus[self.problem.status]}"
                )
            current_total_loss = self._update_losses()
            loss_diff = abs(current_total_loss - prev_total_loss)
            if loss_diff <= max_tol:
                break    
            prev_total_loss = current_total_loss
            for b in self.net.buses:
                constraint_name = f"B{b.id}_Power_Balance"
                self.problem.constraints.pop(constraint_name)
            self._nodal_power_balance()
        else: 
            raise ConvergenceError(
                f"Convergência não atingida após {iter_max} iterações."
            )
        
        perdas_totais = sum(b.loss for b in self.net.buses) * self.net.sb_mva
        curtailment_total = sum((g.p_max_pu - g.p_var.value()) * self.net.sb_mva for g in self.net.wind_generators) if getattr(self.net, 'wind_generators', []) else 0.0
        shed_total = sum(l.p_shed_var.value() * self.net.sb_mva for l in self.net.loads) if getattr(self.net, 'loads', []) else 0.0    
        df_resumo = pd.DataFrame({
            "Total_Cost_System": [pl.value(self.problem.objective)],
            "Total_Losses_MW": [perdas_totais],
            "Total_Curtailment_MW": [curtailment_total],
            "Total_Shed_MW": [shed_total]
        })
        results = self._extract_results(pl.value(self.problem.objective))
        results["Resumo"] = df_resumo

        if verbose:
            # Imprime resultado na tela:
            print("FOB: {:.4f}".format(pl.value(self.problem.objective)))
            print ("Solução encontrada após {} iterações.".format(i))
            print ("Perdas Totais do Sistema: {:.4f} MW".format(perdas_totais))
            print ("Curtailment Total: {:.4f} MW".format(curtailment_total))
            print ("Shed Total: {:.4f} MW".format(shed_total))

            if detailed_output:
                # Imprime resultados detalhados dos geradores térmicos
                if not results["Thermal_Generation"].empty:
                    print("\n--- Geradores Térmicos ---")
                    print(results["Thermal_Generation"])
                # Imprime resultados detalhados dos geradores eólicos
                if not results["Wind_Generation"].empty:
                    print("\n--- Geradores Eólicos ---")
                    print(results["Wind_Generation"])
                # Imprime resultados detalhados dos cortes de carga
                if not results["Load_Shed"].empty:
                    print("\n--- Cortes de Carga ---")
                    print(results["Load_Shed"])
                # Imprime resultados detalhados das linhas
                if not results["Line"].empty:
                    print("\n--- Linhas ---")
                    print(results["Line"])
                # Imprime resultados detalhados das barras
                if not results["Bus"].empty:
                    print("\n--- Barras ---")
                    print(results["Bus"])
        return results

if __name__ == "__main__":
    from power.systems.b6l8 import B6L8
    from power.systems.ieee118 import IEEE118
    print("oi")
    net = IEEE118()
    solver = LinearDispatch(net)
    print(solver.solve_loss())


