from pyomo.environ import *
import pandas as pd
from optimal_power_flow.core.dc_physics import OPFDC
from power import Network

class OPFDCMultiStep(OPFDC):
    """
    Estudo de Fluxo de Potência Ótimo DC Multi-período (Linear).
    
    Herda de OPFDC para reutilizar a física DC (Fluxo Linearizado, Balanço de P).
    Gerencia a dimensão temporal e acoplamentos (Rampa, Bateria).
    """

    def __init__(self, network: Network, periods: int = 24):
        super().__init__(network)
        self.periods = periods
        
        # Armazenamento das séries temporais
        self.load_series = {} 
        self.wind_series = {}
        
        # Estados iniciais
        self.initial_soc = {} # {bess_id: valor_pu}

        self._is_built = False

    # --- SETUP DE DADOS ---
    def set_load_series(self, load_name: str, values: list):
        if len(values) != self.periods:
            raise ValueError(f"Série de carga {load_name} tem tamanho {len(values)}, esperado {self.periods}")
        self.load_series[load_name] = values

    def set_wind_series(self, gen_name: str, values: list):
        if len(values) != self.periods:
            raise ValueError(f"Série eólica {gen_name} tem tamanho {len(values)}, esperado {self.periods}")
        self.wind_series[gen_name] = values

    def set_initial_conditions(self, initial_soc: dict = None):
        """Define o SOC inicial das baterias (opcional)."""
        if initial_soc: self.initial_soc = initial_soc

    # --- OVERRIDES ---
    def create_bess_block(self, container):
        """
        SOBRESCREVE o método original do OPFDC.
        Criamos apenas os parâmetros e variáveis locais.
        NÃO chamamos add_bess_constraints, pois usaremos a lógica temporal global.
        """
        self.create_bess_params(container)
        self.create_bess_variables(container)

    # --- CONSTRUÇÃO DO MODELO ---
    def build_multistep_model(self):
        if self._is_built: return

        # 1. Base (Sets globais)
        self._build_base_model()
        m = self.model

        # 2. Horizonte Temporal
        m.TIME = RangeSet(0, self.periods - 1)
        
        # 3. Blocos Temporais
        m.period = Block(m.TIME)

        for t in m.TIME:
            blk = m.period[t]
            # Chama a física DC para popular este bloco. 
            # Como sobrescrevemos create_bess_block, a bateria fica "livre" para ser amarrada globalmente.
            self.build_physics_on_container(blk)

        # 4. Acoplamentos Temporais
        self._add_temporal_constraints()

        # 5. Objetivo Global
        self._build_global_objective()

        self._is_built = True

    def _add_temporal_constraints(self):
        m = self.model
        
        # --- 1. Acoplamento de Baterias (SOC Tracking) ---
        m.bess_soc_global = Var(m.BESS, m.TIME, bounds=lambda m, g, t: (0, self.bess[g].capacity_pu), initialize=0)

        def soc_dynamics_rule(m, g, t):
            # Variaveis locais dentro do bloco t
            p_in = m.period[t].p_bess_in[g]
            p_out = m.period[t].p_bess_out[g]
            
            eff_c = self.bess[g].efficiency_charge
            eff_d = self.bess[g].efficiency_discharge
            
            net_energy = (p_in * eff_c) - (p_out / eff_d)

            if t == 0:
                soc_prev = self.initial_soc.get(g, self.bess[g].soc_pu)
            else:
                soc_prev = m.bess_soc_global[g, t-1]
            
            return m.bess_soc_global[g, t] == soc_prev + net_energy

        m.SOC_Dynamics_Constraint = Constraint(m.BESS, m.TIME, rule=soc_dynamics_rule)

        # --- 2. Acoplamento de Rampa Térmica ---
        def ramp_up_rule(m, g, t):
            if t == 0: return Constraint.Skip
            
            p_prev = m.period[t-1].p_thermal[g]
            p_curr = m.period[t].p_thermal[g]
            
            ramp = self.thermal_generators[g].max_ramp_up_pu
            if ramp is None:
                ramp = self.thermal_generators[g].p_max_pu
            return p_curr - p_prev <= ramp

        def ramp_down_rule(m, g, t):
            if t == 0: return Constraint.Skip
            
            p_prev = m.period[t-1].p_thermal[g]
            p_curr = m.period[t].p_thermal[g]
            
            ramp = self.thermal_generators[g].max_ramp_down_pu
            if ramp is None:
                ramp = self.thermal_generators[g].p_max_pu
            return p_prev - p_curr <= ramp

        m.Ramp_Up_Constraint = Constraint(m.THERMAL_GENERATORS, m.TIME, rule=ramp_up_rule)
        m.Ramp_Down_Constraint = Constraint(m.THERMAL_GENERATORS, m.TIME, rule=ramp_down_rule)

    def _apply_time_series_data(self):
        """Injeta os dados das séries nos parâmetros dos blocos."""
        m = self.model
        for t in m.TIME:
            blk = m.period[t]

            # Cargas
            for load_id, values in self.load_series.items():
                if load_id in blk.load_p_pu:
                    blk.load_p_pu[load_id] = values[t]
                    # Update upper bound do shed
                    blk.p_shed[load_id].setub(values[t])

            # Eólicas
            for gen_id, values in self.wind_series.items():
                if gen_id in blk.wind_max_p_pu:
                    blk.wind_max_p_pu[gen_id] = values[t]

    def _build_global_objective(self):
        m = self.model
        total_cost = 0
        
        for t in m.TIME:
            blk = m.period[t]
            # Custo Térmica (Linear)
            total_cost += sum(blk.p_thermal[g] * self.thermal_generators[g].cost_b_pu for g in m.THERMAL_GENERATORS)
            # Custo Shedding
            total_cost += sum(blk.p_shed[l] * self.loads[l].cost_shed_pu for l in m.LOADS)
            # Custo Operação Bateria
            total_cost += sum(blk.p_bess_out[g] * self.bess[g].cost_discharge_pu + 
                              blk.p_bess_in[g] * self.bess[g].cost_charge_pu 
                                for g in m.BESS)

        m.GlobalObjective = Objective(expr=total_cost, sense=minimize)

    def solve_multistep(self, solver_name='ipopt', time_limit=None, tee=False):
        if not self._is_built:
            self.build_multistep_model()
        
        self._apply_time_series_data()
        
        opt = SolverFactory(solver_name)
        # Ajustes para solvers lineares (se usar cbc, glpk, highs) ou ipopt
        if solver_name == 'ipopt':
            opt.options['max_iter'] = 3000
            opt.options['tol'] = 1e-6
            opt.options['print_level'] = 5 if tee else 0
        
        if time_limit:
            # Opção varia conforme solver. Ipopt é max_cpu_time. Cbc é sec.
            if solver_name == 'ipopt':
                opt.options['max_cpu_time'] = time_limit
            elif solver_name in ['cbc', 'glpk']:
                opt.options['sec'] = time_limit
        results = opt.solve(self.model, tee=tee)

        term = results.solver.termination_condition
        status = results.solver.status
        if status != SolverStatus.ok or term not in {TerminationCondition.optimal, TerminationCondition.locallyOptimal, TerminationCondition.feasible}:
            raise RuntimeError(f"Solver failed: status={status}, termination={term}")

        return results

    def extract_results_dataframe(self):
        """Extrai resultados organizados por tempo."""
        import pandas as pd
        m = self.model
        
        data_gen = []
        data_load = []
        data_bus = []
        data_lines = []
        
        for t in m.TIME:
            blk = m.period[t]
            
            # Generators
            for g in m.THERMAL_GENERATORS:
                data_gen.append({'time': t, 'id': g, 'type': 'thermal', 
                                    'p_pu': value(blk.p_thermal[g])})
            for g in m.WIND_GENERATORS:
                data_gen.append({'time': t, 'id': g, 'type': 'wind', 
                                    'p_pu': value(blk.p_wind[g])})
            for g in m.BESS:
                data_gen.append({'time': t, 'id': g, 'type': 'bess', 
                                    'p_pu': value(blk.p_bess_out[g]) - value(blk.p_bess_in[g]),
                                    'soc_pu': value(m.bess_soc_global[g, t])})

            # Bus (Angles) - No DC voltage is fixed 1.0 usually
            for b in m.BUSES:
                data_bus.append({'time': t, 'id': b, 
                                    'v_pu': 1.0, 
                                    'theta_rad': value(blk.theta_rad[b])})
                
            # Load
            for l in m.LOADS:
                data_load.append({'time': t, 'id': l, 
                                    'p_load': value(blk.load_p_pu[l]), 
                                    'p_shed': value(blk.p_shed[l])})

            # Lines
            for l in m.LINES:
                flow = value(blk.flow[l])
                lim = self.lines[l].flow_max_pu
                # Loading % (abs value for DC)
                loading = (abs(flow)/lim*100) if lim and lim > 0 else 0
                data_lines.append({'time': t, 'id': l, 
                                    'p_flow_pu': flow, 
                                    'loading_percent': loading})

        return {
            'generation': pd.DataFrame(data_gen),
            'bus': pd.DataFrame(data_bus),
            'load': pd.DataFrame(data_load),
            'line': pd.DataFrame(data_lines)
        }


if __name__ == "__main__":
    import numpy as np
    from power.systems import B6L8Charged

    # Perfis de 24h utilizados no trabalho 9/10
    load_profile_base = np.array([
        0.70, 0.65, 0.62, 0.60, 0.65, 0.75,
        0.85, 0.95, 1.00, 1.05, 1.10, 1.08,
        1.05, 1.02, 1.00, 0.98, 1.05, 1.15,
        1.20, 1.18, 1.10, 1.00, 0.90, 0.80
    ])

    wind_profile_base = np.array([
        0.90, 0.95, 0.98, 0.92, 0.85, 0.80,
        0.70, 0.60, 0.45, 0.30, 0.25, 0.35,
        0.40, 0.30, 0.25, 0.35, 0.45, 0.55,
        0.65, 0.75, 0.80, 0.85, 0.88, 0.92
    ])

    periods = 24
    net = B6L8Charged()
    opf = OPFDCMultiStep(net, periods=periods)

    # Séries por carga/gerador
    for load in net.loads:
        opf.set_load_series(load.name, load_profile_base * load.p_pu)

    for wnd in net.wind_generators:
        opf.set_wind_series(wnd.name, wind_profile_base * wnd.p_max_pu)

    # Build & solve
    opf.build_multistep_model()
    res = opf.solve_multistep(solver_name="ipopt", time_limit=300, tee=False)

    total_cost = value(opf.model.GlobalObjective)
    dfs = opf.extract_results_dataframe()
    print("Solver status:", getattr(res, "solver", res))
    print("Custo total (pu):", total_cost)

    def _print_table(df, cols, title):
        if df.empty:
            return
        keep = [c for c in cols if c in df.columns]
        print(title)
        print(df[keep].to_string(index=False, float_format=lambda x: f"{x:.4f}"))

    def print_hourly_reports(dfs, periods):
        for t in range(periods):
            print(f"\n=== Hora {t} ===")

            gen = dfs['generation'][dfs['generation']['time'] == t].copy()
            _print_table(gen, ["id", "type", "p_pu", "soc_pu"], "Geração")

            load = dfs['load'][dfs['load']['time'] == t].copy()
            _print_table(load, ["id", "p_load", "p_shed"], "Cargas / Shed")

            bus = dfs['bus'][dfs['bus']['time'] == t].copy()
            _print_table(bus, ["id", "v_pu", "theta_rad"], "Barras (V, Ângulo)")

            line = dfs['line'][dfs['line']['time'] == t].copy()
            _print_table(line, ["id", "p_flow_pu", "loading_percent"], "Linhas (Fluxo e Carregamento %)")

    print_hourly_reports(dfs, periods)