from pyomo.environ import *
import pandas as pd
import numpy as np
from optimal_power_flow.core.dc_physics import OPFDC
from power import Network
from data_models import TimeSeries

class OPFMultiStep(OPFDC):
    """
    Estudo de Fluxo de Potência DC Multiperiodo com Perdas Iterativas.
    Usa Blocks do Pyomo para criar um período por bloco, conectando-os via SOC das baterias.
    """

    def __init__(self, network: Network, periods: int = 24):
        """
        Inicializa o modelo multiperiodo.
        
        Args:
            network: Rede elétrica
            periods: Número de períodos (timesteps) do horizonte
        """
        # Chama construtor da classe pai (NÃO constrói física ainda)
        super().__init__(network)
        self.periods = periods
        
        # Armazena séries temporais (será populado depois)
        self.load_series = {}    # {load_name: TimeSeries}
        self.wind_series = {}    # {gen_name: TimeSeries}
        
        # Controla se o modelo foi construído
        self._is_multiperiod_built = False

    def set_load_series(self, load_name: str, series: TimeSeries):
        """Define série temporal de carga para uma load."""
        if len(series.values) != self.periods:
            raise ValueError(f"Load {load_name}: série deve ter {self.periods} valores")
        self.load_series[load_name] = series

    def set_wind_series(self, gen_name: str, series: TimeSeries):
        """Define série temporal de geração eólica para um gerador."""
        if len(series.values) != self.periods:
            raise ValueError(f"Wind {gen_name}: série deve ter {self.periods} valores")
        self.wind_series[gen_name] = series

    def build_multiperiod_model(self):
        """
        Constrói o modelo multiperiodo usando Blocks do Pyomo.
        Cada período é um bloco independente, mas conectados via SOC das baterias.
        """
        if self._is_multiperiod_built:
            return
        
        # 1. Constrói base (BUSES, LINES, GENERATORS, etc.)
        self._build_base_model()
        
        m = self.model
        
        # 2. Cria conjunto de períodos
        m.PERIODS = RangeSet(0, self.periods - 1)
        
        # 3. Cria um BLOCK para cada período
        # Cada bloco terá sua própria cópia das variáveis e constraints
        m.period = Block(m.PERIODS)
        
        for t in m.PERIODS:
            self._build_period_block(t)
        
        # 4. Adiciona acoplamento temporal (SOC das baterias)
        self._add_temporal_coupling()
        
        self._is_multiperiod_built = True

    def _build_period_block(self, t):
        """
        Constrói um bloco para o período t com todas as variáveis e constraints.
        Replica a estrutura do OPFDC, mas dentro de um Block.
        """
        m = self.model
        blk = m.period[t]
        
        # --- VARIÁVEIS ---
        # Geração Térmica
        blk.p_thermal = Var(m.THERMAL_GENERATORS, 
                            bounds=lambda model, g: (self.thermal_generators[g].p_min_pu, 
                                                    self.thermal_generators[g].p_max_pu), 
                            initialize=0)
        
        # Geração Eólica
        blk.p_wind = Var(m.WIND_GENERATORS, bounds=(0, None), initialize=0)
        
        # Baterias
        def charge_bounds_rule(model, g): 
            return (0, self.bess[g].dc_max_charge_rate_pu)
        def discharge_bounds_rule(model, g): 
            return (0, self.bess[g].dc_max_discharge_rate_pu)
        
        blk.p_bess_out = Var(m.BESS, bounds=discharge_bounds_rule, initialize=0)
        blk.p_bess_in = Var(m.BESS, bounds=charge_bounds_rule, initialize=0)
        blk.bess_soc = Var(m.BESS, bounds=(0, None), initialize=0)  # SOC do período
        
        # Corte de Carga
        blk.p_shed = Var(m.LOADS, bounds=(0, None), initialize=0)
        
        # Ângulos
        blk.theta_rad = Var(m.BUSES, bounds=(-np.pi, np.pi), initialize=0)
        
        # Fluxos
        blk.flow = Var(m.LINES, 
                        bounds=lambda model, l: (-self.lines[l].flow_max_pu, 
                                                self.lines[l].flow_max_pu), 
                        initialize=0)
        
        # Parâmetros mutáveis (perdas, carga, vento)
        blk.bus_loss = Param(m.BUSES, initialize=0, within=Reals, mutable=True)
        blk.load_p = Param(m.LOADS, initialize=0, within=NonNegativeReals, mutable=True)
        blk.wind_max_p = Param(m.WIND_GENERATORS, initialize=0, within=NonNegativeReals, mutable=True)
        
        # --- CONSTRAINTS ---
        
        # Fix slack bus angle
        for b in self.buses.values():
            if b.btype.name == 'SLACK':
                blk.theta_rad[b.name].setlb(0)
                blk.theta_rad[b.name].setub(0)
        
        # Limite de shed
        def shed_max_rule(model, l):
            return blk.p_shed[l] <= blk.load_p[l]
        blk.Shed_Max_Constraint = Constraint(m.LOADS, rule=shed_max_rule)
        
        # Limite de vento
        def wind_max_rule(model, g):
            return blk.p_wind[g] <= blk.wind_max_p[g]
        blk.Wind_Max_Constraint = Constraint(m.WIND_GENERATORS, rule=wind_max_rule)
        
        # Limites de SOC da bateria
        def bess_soc_max_rule(model, g):
            return blk.bess_soc[g] <= self.bess[g].capacity_pu
        blk.BESS_SOC_Max_Constraint = Constraint(m.BESS, rule=bess_soc_max_rule)
        
        def bess_soc_min_rule(model, g):
            return blk.bess_soc[g] >= 0
        blk.BESS_SOC_Min_Constraint = Constraint(m.BESS, rule=bess_soc_min_rule)
        
        # Fluxo DC
        def dc_flow_rule(model, l):
            line = self.lines[l]
            return blk.flow[l] == (blk.theta_rad[line.from_bus.name] - 
                                   blk.theta_rad[line.to_bus.name]) / line.x_pu
        blk.DCFlowConstraint = Constraint(m.LINES, rule=dc_flow_rule)
        
        # Balanço Nodal
        def nodal_balance_rule(model, b):
            gen_thermal = sum(blk.p_thermal[g] for g in m.THERMAL_GENERATORS 
                             if self.thermal_generators[g].bus.name == b)
            gen_wind = sum(blk.p_wind[g] for g in m.WIND_GENERATORS 
                          if self.wind_generators[g].bus.name == b)
            gen_bess_out = sum(blk.p_bess_out[g] for g in m.BESS 
                              if self.bess[g].bus.name == b)
            gen_bess_in = sum(blk.p_bess_in[g] for g in m.BESS 
                             if self.bess[g].bus.name == b)
            load = sum(blk.load_p[l] for l in m.LOADS 
                      if self.loads[l].bus.name == b)
            shed = sum(blk.p_shed[l] for l in m.LOADS 
                      if self.loads[l].bus.name == b)
            loss = blk.bus_loss[b]
            flow_in = sum(blk.flow[l] for l in m.LINES 
                         if self.lines[l].to_bus.name == b)
            flow_out = sum(blk.flow[l] for l in m.LINES 
                          if self.lines[l].from_bus.name == b)
            
            return (gen_thermal + gen_wind + gen_bess_out - gen_bess_in + 
                    shed + flow_in - flow_out == load + loss)
        
        blk.NodalBalanceConstraint = Constraint(m.BUSES, rule=nodal_balance_rule)

    def _add_temporal_coupling(self):
        """
        Adiciona constraints de acoplamento temporal via SOC das baterias.
        SOC[t+1] = SOC[t] + (charge[t] * eff_c - discharge[t] / eff_d)
        """
        m = self.model
        
        def soc_coupling_rule(model, g, t):
            if t == 0:
                # Período inicial: usa SOC inicial da bateria
                soc_prev = self.bess[g].soc_pu
            else:
                soc_prev = m.period[t-1].bess_soc[g]
            
            batt = self.bess[g]
            charge = m.period[t].p_bess_in[g] * batt.efficiency_charge
            discharge = m.period[t].p_bess_out[g] / batt.efficiency_discharge
            
            return m.period[t].bess_soc[g] == soc_prev + charge - discharge
        
        m.SOC_Coupling = Constraint(m.BESS, m.PERIODS, rule=soc_coupling_rule)

    def build_objective(self):
        """
        Função objetivo: minimizar custo total ao longo de todos os períodos.
        """
        m = self.model
        
        total_cost = 0
        
        for t in m.PERIODS:
            blk = m.period[t]
            
            # Custo Geração Térmica
            cost_thermal = sum(blk.p_thermal[g] * self.thermal_generators[g].cost_b_pu 
                              for g in m.THERMAL_GENERATORS)
            
            # Custo de Déficit (Shedding)
            cost_shed = sum(blk.p_shed[l] * self.loads[l].cost_shed_pu 
                           for l in m.LOADS)
            
            # Custo Operacional de Bateria
            cost_bess = sum(blk.p_bess_out[g] * self.bess[g].cost_discharge_pu + 
                           blk.p_bess_in[g] * self.bess[g].cost_charge_pu
                           for g in m.BESS)
            
            total_cost += cost_thermal + cost_shed + cost_bess
        
        m.obj = Objective(expr=total_cost, sense=minimize)

    def update_period_data(self, t):
        """
        Atualiza os parâmetros de carga e vento para o período t.
        """
        m = self.model
        blk = m.period[t]
        
        # Atualiza carga
        for l in m.LOADS:
            if l in self.load_series:
                blk.load_p[l] = self.load_series[l].values[t]
            else:
                blk.load_p[l] = self.loads[l].p_pu
        
        # Atualiza vento
        for g in m.WIND_GENERATORS:
            if g in self.wind_series:
                blk.wind_max_p[g] = self.wind_series[g].values[t]
            else:
                blk.wind_max_p[g] = self.wind_generators[g].p_max_pu

    def _calculate_period_losses(self, t):
        """
        Calcula perdas para o período t baseado nos ângulos da solução atual.
        """
        m = self.model
        blk = m.period[t]
        
        new_bus_losses = {b: 0.0 for b in m.BUSES}
        total_loss = 0.0

        for l_name in m.LINES:
            line = self.lines[l_name]
            r = line.r_pu
            x = line.x_pu
            denom = (r**2 + x**2)
            if denom == 0: 
                continue
            
            g_series = r / denom
            theta_from = value(blk.theta_rad[line.from_bus.name])
            theta_to = value(blk.theta_rad[line.to_bus.name])
            
            p_loss = g_series * (theta_from - theta_to)**2
            
            new_bus_losses[line.from_bus.name] += p_loss / 2.0
            new_bus_losses[line.to_bus.name] += p_loss / 2.0
            total_loss += p_loss

        return new_bus_losses, total_loss

    def solve(self, solver_name='ipopt', max_iter=20, tol=1e-4, verbose=False):
        """
        Resolve o problema multiperiodo com iteração de perdas.
        """
        # 1. Constrói modelo se necessário
        if not self._is_multiperiod_built:
            self.build_multiperiod_model()
            self.build_objective()
        
        # 2. Prepara sufixos para duals
        m = self.model
        m.dual = Suffix(direction=Suffix.IMPORT)
        m.rc = Suffix(direction=Suffix.IMPORT)
        
        # 3. Atualiza dados de todos os períodos
        for t in m.PERIODS:
            self.update_period_data(t)
        
        # 4. Iteração de perdas
        opt = SolverFactory(solver_name)
        prev_total_loss = -1.0
        converged = False
        
        for iteration in range(1, max_iter + 1):
            # Resolve
            results = opt.solve(m, tee=False)
            
            if (results.solver.status != SolverStatus.ok) and \
               (results.solver.termination_condition != TerminationCondition.optimal):
                print(f"Iteração {iteration}: Falha no solver. Status: {results.solver.status}")
                break
            
            # Calcula perdas totais de todos os períodos
            current_total_loss = 0.0
            for t in m.PERIODS:
                bus_losses_map, period_loss = self._calculate_period_losses(t)
                current_total_loss += period_loss
                
                # Atualiza perdas do período
                blk = m.period[t]
                for b in m.BUSES:
                    blk.bus_loss[b] = bus_losses_map[b]
            
            # Verifica convergência
            diff = abs(current_total_loss - prev_total_loss)
            if verbose:
                cost = value(m.obj)
                print(f"Iter {iteration}: Custo=${cost:,.2f} | Perdas Totais={current_total_loss*self.net.sb_mva:.2f} MW | Diff={diff:.2e}")
            
            if diff < tol:
                converged = True
                if verbose:
                    print(">> Convergência atingida!")
                break
            
            prev_total_loss = current_total_loss
        
        return self._extract_results(converged)

    def _extract_results(self, converged):
        """
        Extrai resultados detalhados em DataFrames por período.
        """
        m = self.model
        sb = self.net.sb_mva
        
        def v(var): 
            return value(var) if var is not None else 0.0
        
        def get_dual(constraint):
            if hasattr(m, 'dual') and constraint in m.dual:
                return m.dual[constraint]
            return 0.0
        
        def get_rc(variable):
            if hasattr(m, 'rc') and variable in m.rc:
                return m.rc[variable]
            return 0.0
        
        # Resultados agregados
        all_thermal = []
        all_wind = []
        all_bess = []
        all_shed = []
        all_bus = []
        all_line = []
        
        total_cost_all = value(m.obj)
        total_loss_all = 0.0
        total_shed_all = 0.0
        total_curtail_all = 0.0
        
        for t in m.PERIODS:
            blk = m.period[t]
            
            # --- TÉRMICA ---
            for g in m.THERMAL_GENERATORS:
                all_thermal.append({
                    "Period": t,
                    "Generator": g,
                    "Bus": self.thermal_generators[g].bus.name,
                    "P_MW": v(blk.p_thermal[g]) * sb,
                    "Cost_pu": self.thermal_generators[g].cost_b_pu,
                    "RC": get_rc(blk.p_thermal[g])
                })
            
            # --- EÓLICA ---
            for g in m.WIND_GENERATORS:
                p_val = v(blk.p_wind[g])
                p_max = v(blk.wind_max_p[g])
                all_wind.append({
                    "Period": t,
                    "Generator": g,
                    "Bus": self.wind_generators[g].bus.name,
                    "Available_MW": p_max * sb,
                    "P_MW": p_val * sb,
                    "Curtailment_MW": (p_max - p_val) * sb,
                    "Dual_Max": get_dual(blk.Wind_Max_Constraint[g])
                })
                total_curtail_all += (p_max - p_val) * sb
            
            # --- BATERIAS ---
            for g in m.BESS:
                all_bess.append({
                    "Period": t,
                    "Battery": g,
                    "Bus": self.bess[g].bus.name,
                    "P_Out_MW": v(blk.p_bess_out[g]) * sb,
                    "P_In_MW": v(blk.p_bess_in[g]) * sb,
                    "SOC_MWh": v(blk.bess_soc[g]) * sb,
                    "Dual_SOC_Max": get_dual(blk.BESS_SOC_Max_Constraint[g]),
                    "Dual_SOC_Min": get_dual(blk.BESS_SOC_Min_Constraint[g])
                })
            
            # --- SHED ---
            for l in m.LOADS:
                shed_val = v(blk.p_shed[l])
                all_shed.append({
                    "Period": t,
                    "Load": l,
                    "Bus": self.loads[l].bus.name,
                    "P_Shed_MW": shed_val * sb,
                    "P_Load_MW": v(blk.load_p[l]) * sb,
                    "Cost_Shed": self.loads[l].cost_shed_pu,
                    "Dual_Shed_Limit": get_dual(blk.Shed_Max_Constraint[l])
                })
                total_shed_all += shed_val * sb
            
            # --- BARRAS ---
            for b in m.BUSES:
                lmp = get_dual(blk.NodalBalanceConstraint[b])
                loss_mw = v(blk.bus_loss[b]) * sb
                total_loss_all += loss_mw
                
                all_bus.append({
                    "Period": t,
                    "Bus": b,
                    "Theta_deg": np.rad2deg(v(blk.theta_rad[b])),
                    "LMP": lmp,
                    "Loss_MW": loss_mw
                })
            
            # --- LINHAS ---
            for l in m.LINES:
                line_obj = self.lines[l]
                flow_val = v(blk.flow[l])
                
                # Perda na linha
                r = line_obj.r_pu
                x = line_obj.x_pu
                denom = r**2 + x**2
                g_series = r / denom if denom > 0 else 0
                theta_diff = v(blk.theta_rad[line_obj.from_bus.name]) - v(blk.theta_rad[line_obj.to_bus.name])
                loss_val = g_series * (theta_diff**2) * sb
                
                max_flow = line_obj.flow_max_pu
                loading = (abs(flow_val) / max_flow * 100) if max_flow > 0 else 0.0
                
                all_line.append({
                    "Period": t,
                    "Line": l,
                    "From": line_obj.from_bus.name,
                    "To": line_obj.to_bus.name,
                    "Flow_MW": flow_val * sb,
                    "Max_MW": max_flow * sb,
                    "Loading_%": loading,
                    "Loss_MW": loss_val,
                    "Congestion_Price": get_rc(blk.flow[l])
                })
        
        # DataFrames
        df_thermal = pd.DataFrame(all_thermal)
        df_wind = pd.DataFrame(all_wind)
        df_bess = pd.DataFrame(all_bess)
        df_shed = pd.DataFrame(all_shed)
        df_bus = pd.DataFrame(all_bus)
        df_line = pd.DataFrame(all_line)
        
        # Resumo
        resumo = pd.DataFrame({
            "Total_Cost": [total_cost_all],
            "Total_Loss_MW": [total_loss_all],
            "Total_Curtailment_MW": [total_curtail_all],
            "Total_Shed_MW": [total_shed_all],
            "Periods": [self.periods],
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
            "Total_Cost": total_cost_all
        }


if __name__ == "__main__":
    import pandas as pd
    from power import Network
    from power.systems.b3_eolic import B3_EOLIC
    from data_models import TimeSeries
    
    # Configuração do Pandas
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.float_format', '{:.4f}'.format)
    
    # 1. Cria rede
    print("\n>>> Criando Sistema B3 com Eólica...")
    net = B3_EOLIC()
    
    # 2. Define horizonte temporal (24 períodos = 24 horas)
    periods = 24
    
    # 3. Cria estudo multiperiodo
    print(f">>> Criando estudo multiperiodo com {periods} períodos...")
    study = OPFMultiStep(net, periods=periods)
    
    # 4. Define séries temporais (exemplo com perfil diário)
    # Perfil de carga típico (pu): baixo de madrugada, pico à tarde
    load_profile = [0.6, 0.55, 0.5, 0.5, 0.55, 0.65, 0.75, 0.85, 0.9, 0.95, 
                   1.0, 1.0, 0.95, 0.95, 1.0, 1.05, 1.1, 1.05, 0.95, 0.85,
                   0.75, 0.7, 0.65, 0.6]
    
    # Perfil de vento típico (pu): mais vento à noite
    wind_profile = [0.8, 0.85, 0.9, 0.85, 0.75, 0.65, 0.5, 0.4, 0.35, 0.3,
                   0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75,
                   0.8, 0.85, 0.85, 0.8]
    
    # Aplica perfis às cargas e geradores
    for load in net.loads:
        base_p = load.p_pu
        series = TimeSeries(values=[base_p * factor for factor in load_profile])
        study.set_load_series(load.name, series)
    
    for gen in net.wind_generators:
        base_p = gen.p_max_pu
        series = TimeSeries(values=[base_p * factor for factor in wind_profile])
        study.set_wind_series(gen.name, series)
    
    # 5. Resolve
    print(f"\n>>> Resolvendo OPF Multiperiodo ({periods} períodos)...")
    results = study.solve(solver_name='ipopt', verbose=True, max_iter=10)
    
    # 6. Print Resultados
    print("\n" + "="*100)
    print(f"RELATÓRIO MULTIPERIODO - Status: {results['Resumo']['Status'].iloc[0]}")
    print("="*100)
    
    tables = [
        ("RESUMO GERAL", "Resumo"),
        ("GERAÇÃO TÉRMICA (por período)", "Thermal_Generation"),
        ("GERAÇÃO EÓLICA (por período)", "Wind_Generation"),
        ("BATERIAS (por período)", "Battery"),
        ("CORTE DE CARGA (por período)", "Load_Shed"),
        ("BARRAS - LMP (por período)", "Bus"),
        ("LINHAS - Fluxos (por período)", "Line"),
    ]
    
    for title, key in tables:
        df = results.get(key)
        if df is not None and not df.empty:
            print(f"\n--- {title} ---")
            # Mostra apenas primeiros 50 registros para não poluir
            if len(df) > 50:
                print(df.head(50).to_string(index=False))
                print(f"... ({len(df) - 50} linhas omitidas)")
            else:
                print(df.to_string(index=False))
        else:
            print(f"\n--- {title} ---\n(Sem dados)")
    
    print("\n" + "="*100)
