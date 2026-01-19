from pyomo.environ import *
import pandas as pd
import numpy as np
from optimal_power_flow.core.ac_physics import OPFAC
from power import Network

class ACMinDeviation(OPFAC):
    """
    Pyomo model for AC Minimum Deviation from operating point problems.
    Minimiza o desvio quadrático em relação a um ponto de operação pré-definido.
    """

    def __init__(self, network: Network):
        super().__init__(network)
        self.build_physics()
        self.build_objective()

    def build_objective(self):
        """
        Define a função objetivo: 
        Minimizar (Desvios de Geração)^2 + (Desvios de Bateria)^2 + Penalidade(Corte de Carga)
        """
        m = self.model
        sb = self.net.sb_mva
        
        # --- 1. Desvio Quadrático da Geração Térmica ---
        # (P_gerado - P_programado)^2
        deviation_thermal = sum(
            (m.p_thermal[g] * sb - (self.thermal_generators[g].p_mw or 0.0))**2
            for g in m.THERMAL_GENERATORS
        )
        
        # --- 2. Desvio Quadrático da Eólica ---
        # (P_gerado - P_programado)^2
        deviation_eolic = sum(
            (m.p_wind[g] * sb - (self.wind_generators[g].p_mw or 0.0))**2
            for g in m.WIND_GENERATORS
        )

        # --- 3. Desvio Quadrático da Bateria ---
        # Consideramos o fluxo líquido: (Sair - Entrar) vs (Target)
        # Se target > 0 (descarregar), se target < 0 (carregar)
        deviation_bess = 0
        if hasattr(m, 'BESS') and len(m.BESS) > 0:
            deviation_bess = sum(
                ((m.p_bess_out[b] - m.p_bess_in[b]) * sb - (self.bess[b].p_mw or 0.0))**2
                for b in m.BESS
            )

        # --- 4. Penalidade por Déficit (Corte de Carga) ---
        # Big M para garantir que só corte carga se for fisicamente impossível atender
        # Multiplicamos por 1 milhão para priorizar o atendimento da carga
        
        cost_p_shedding = sum((m.p_shed[l] * sb * self.loads[l].cost_shed_mw) 
            for l in m.LOADS
        )
        
        PENALTY_FACTOR = 1e8
        cost_q_shedding = sum(
            PENALTY_FACTOR * ((m.q_shed[l]**2 * sb)**2) 
            for l in m.LOADS
        )

        # Soma total
        m.obj = Objective(
            expr=deviation_thermal + deviation_eolic + deviation_bess + cost_p_shedding + cost_q_shedding, 
            sense=minimize
        )

    def solve(self, solver_name: str = 'ipopt', verbose: bool = False, **kwargs):
        """
        Wrapper para o solve, igual ao EconDispatch
        """
        solver = SolverFactory(solver_name)
        results = solver.solve(self.model, tee=verbose, **kwargs)
        return self.extract_results(converged=(results.solver.termination_condition == TerminationCondition.optimal))

    def extract_results(self, converged=True):
        """
        Extrai resultados detalhados AC (P, Q, V, Theta, S) em DataFrames.
        Cópia da lógica do ACEconDispatch para manter consistência.
        """
        m = self.model
        # Garante compatibilidade se a rede estiver em self.network ou self.net
        net_obj = getattr(self, 'network', getattr(self, 'net', None))
        sb = net_obj.base_mva if hasattr(net_obj, 'base_mva') else 100.0

        # --- Custo econômico reconstruído a partir do despacho final ---
        def compute_total_cost():
            cost_th = sum(
                self.thermal_generators[g].cost_a_pu
                + self.thermal_generators[g].cost_b_pu * value(m.p_thermal[g])
                + self.thermal_generators[g].cost_c_pu * (value(m.p_thermal[g]) ** 2)
                for g in m.THERMAL_GENERATORS
            )
            cost_shed = sum(
                self.loads[l].cost_shed_pu * value(m.p_shed[l])
                for l in m.LOADS
            )
            cost_bess = 0.0
            if hasattr(m, "BESS"):
                cost_bess = sum(
                    self.bess[b].cost_discharge_pu * value(m.p_bess_out[b])
                    + self.bess[b].cost_charge_pu * value(m.p_bess_in[b])
                    for b in m.BESS
                )
            return cost_th + cost_shed + cost_bess
        
        # --- Helpers ---
        def v(var): return value(var) if var is not None else 0.0
        
        def get_dual(constraint):
            if hasattr(m, 'dual') and constraint in m.dual: return m.dual[constraint]
            return 0.0

        # --- 1. GERAÇÃO TÉRMICA ---
        therm_data = []
        for g in m.THERMAL_GENERATORS:
            p = v(m.p_thermal[g])
            q = v(m.q_thermal[g])
            target = self.thermal_generators[g].p_pu or 0.0
            
            therm_data.append({
                "Name": g, 
                "Bus": self.thermal_generators[g].bus.name,
                "P_MW": p * sb, 
                "Target_MW": target * sb,
                "Deviation_MW": (p - target) * sb,
                "Q_MVAr": q * sb, 
                "S_MVA": (p**2 + q**2)**0.5 * sb,
                "P_Max": self.thermal_generators[g].p_max_pu * sb
            })
        df_thermal = pd.DataFrame(therm_data)

        # --- 2. EÓLICA ---
        wind_data = []
        for g in m.WIND_GENERATORS:
            p = v(m.p_wind[g])
            q = v(m.q_wind[g])
            target = self.wind_generators[g].p_pu or 0.0
            
            wind_data.append({
                "Name": g, 
                "Bus": self.wind_generators[g].bus.name,
                "P_MW": p * sb, 
                "Target_MW": target * sb,
                "Deviation_MW": (p - target) * sb,
                "Q_MVAr": q * sb
            })
        df_wind = pd.DataFrame(wind_data)

        # --- 3. BATERIAS ---
        bess_data = []
        if hasattr(m, 'BESS'):
            for g in m.BESS:
                p_out = v(m.p_bess_out[g])
                p_in = v(m.p_bess_in[g])
                q = v(m.q_bess[g])
                target = self.bess[g].p_pu or 0.0
                net_flow = p_out - p_in
                
                bess_data.append({
                    "Name": g, 
                    "Bus": self.bess[g].bus.name,
                    "P_Out_MW": p_out * sb, 
                    "P_In_MW": p_in * sb, 
                    "Net_Flow_MW": net_flow * sb,
                    "Target_MW": target * sb,
                    "Deviation_MW": (net_flow - target) * sb,
                    "Q_MVAr": q * sb,
                    "SOC_Final": (v(m.bess_soc_pu[g]) if hasattr(m, 'bess_soc_pu') else 0.0)
                })
        df_bess = pd.DataFrame(bess_data)

        # --- 4. SHEDDING & Q VIRTUAL ---
        shed_data = []
        total_p_shed = 0.0
        total_q_virtual = 0.0
        
        for l in m.LOADS:
            p_shed_val = v(m.p_shed[l])
            q_virtual_val = v(m.q_shed[l])
            
            total_p_shed += p_shed_val
            total_q_virtual += abs(q_virtual_val)
            
            shed_data.append({
                "Load": l,
                "Bus": self.loads[l].bus.name,
                "P_Load_MW": self.loads[l].p_pu * sb,
                "P_Shed_MW": p_shed_val * sb,
                "Q_Virtual_MVAr": q_virtual_val * sb,
                "Status": "SHEDDING" if p_shed_val > 1e-4 else "OK"
            })
        df_shed = pd.DataFrame(shed_data)

        # --- 5. BARRAS ---
        bus_data = []
        for b in m.BUSES:
            bus_data.append({
                "Bus": b,
                "V_pu": v(m.v_pu[b]),
                "Angle_deg": np.degrees(v(m.theta_rad[b])),
            })
        df_bus = pd.DataFrame(bus_data)

        # --- 6. LINHAS (CORRIGIDO: usando flow_max_pu) ---
        line_data = []
        for l in m.LINES:
            line_obj = self.lines[l]
            p_from = v(m.p_flow_out[l]); q_from = v(m.q_flow_out[l])
            p_to = v(m.p_flow_in[l]); q_to = v(m.q_flow_in[l])
            
            # Cálculo do carregamento usando flow_max_pu
            s_apparent = (p_from**2 + q_from**2)**0.5
            limit = line_obj.flow_max_pu
            loading = (s_apparent / limit * 100) if limit > 0 else 0.0
            
            line_data.append({
                "Line": l, 
                "From": line_obj.from_bus.name, 
                "To": line_obj.to_bus.name,
                "P_From_MW": p_from * sb, 
                "Q_From_MVAr": q_from * sb,
                "P_Loss_MW": (p_from + p_to) * sb,
                "Loading_%": loading
            })
        df_line = pd.DataFrame(line_data)

        # --- 7. RESUMO ---
        resumo = pd.DataFrame({
            "Total_Cost": [compute_total_cost()],
            "Total_P_Shed_MW": [total_p_shed * sb],
            "Total_Q_Virtual_MVAr": [total_q_virtual * sb],
            "Status": ["Optimal" if converged else "Not Converged"]
        })

        return {
            "Resumo": resumo, 
            "Thermal_Generation": df_thermal, 
            "Wind_Generation": df_wind,
            "Battery": df_bess, 
            "Load_Shed": df_shed, 
            "Bus": df_bus, 
            "Line": df_line
        }
    
if __name__ == "__main__":
    # Exemplo de uso
    from power.systems import *

    net = B6L8()
    study = ACMinDeviation(net)
    results = study.solve(solver_name='ipopt', verbose=True)
    
    #Agora printe na tela:
    print("\n>>> Resultados do AC Minimum Deviation <<<")
    #results ja tem os resultados extraidos:
    print(results['Resumo'])

    print(results['Thermal_Generation'])

    print(results['Bus'])

    print(results['Line'])

    print(results['Load_Shed'])

