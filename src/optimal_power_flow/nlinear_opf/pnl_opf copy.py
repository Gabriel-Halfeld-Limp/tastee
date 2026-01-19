from pyomo.environ import *
from power import *
import numpy as np
import pandas as pd

class Economic_Dispatch:
    def __init__(self, network: Network):
        self.net = network

        #Sets
        self._create_sets()

        #Parameters
        self._create_parameters()

        #Variables
        self._create_variables()

        #Constraints
        self._create_constraints()

        #Objective Function
        self._create_objective()
        
        #Dual
        self.model.dual = Suffix(direction=Suffix.IMPORT)

    # ----------------------------------------------------------------Create ConcreteModel------------------------------------------------------------------------------------#
    def _econ_disp_model(self):
        self.model = ConcreteModel()
    
    # ----------------------------------------------------------------Obj Functions ------------------------------------------------------------------------------------------#
    def _fob_econ_dispatch(self):
        self.model.name = 'AC Economic Dispatch'
        thermal_cost = sum(g.cost_a_pu + g.cost_b_pu * self.model.p_pu[g.name] + g.cost_c_pu * self.model.p_pu[g.name]**2 for g in self.net.thermal_generators) # Custo dos geradores térmicos
        shedding_cost = sum(l.cost_shed_pu * self.model.load_shed_pu[l.name] for l in self.net.loads) # Custo do load shedding
        battery_in = sum(b.cost_charge_pu * self.model.battery_charge_pu[b.name] for b in self.net.batteries) # Custo do carregamento das baterias
        battery_out = sum(b.cost_discharge_pu * self.model.battery_discharge_pu[b.name] for b in self.net.batteries) # Custo do descarregamento das baterias
    
    # ----------------------------------------------------------------Create Sets---------------------------------------------------------------------------------------------#
    
    def _create_sets(self):    
        self.model.thermal_generators = Set(initialize=[g.name for g in self.net.thermal_generators], doc="Conjunto de geradores") # Cria conjunto de geradores com os nomes
        self.model.wind_generators    = Set(initialize=[g.name for g in self.net.wind_generators], doc="Conjunto de geradores eólicos") # Cria conjunto de geradores eólicos
        self.model.batteries          = Set(initialize=[b.name for b in self.net.batteries], doc="Conjunto de baterias") # Cria conjunto de baterias
        self.model.loads              = Set(initialize=[l.name for l in self.net.loads], doc="Conjunto de cargas") # Cria conjunto de cargas
        self.model.buses              = Set(initialize=[b.name for b in self.net.buses], doc="Conjunto de barras")  # Cria conjunto de barras
        self.model.lines              = Set(initialize=[ln.name for ln in self.net.lines], doc="Conjunto de linhas") # Cria conjunto de linhas

    # ----------------------------------------------------------------Create Parameters---------------------------------------------------------------------------------------#
    def _create_parameters(self):
        #thermal_generators
        m = self.model
        m.generator_bus    = Param(m.thermal_generators, initialize={g.name: g.bus.name  for g in self.net.thermal_generators})
        m.generator_pmax   = Param(m.thermal_generators, initialize={g.name: g.p_max_pu  for g in self.net.thermal_generators})
        m.generator_pmin   = Param(m.thermal_generators, initialize={g.name: g.p_min_pu  for g in self.net.thermal_generators})
        m.generator_qmax   = Param(m.thermal_generators, initialize={g.name: g.q_max_pu  for g in self.net.thermal_generators})
        m.generator_qmin   = Param(m.thermal_generators, initialize={g.name: g.q_min_pu  for g in self.net.thermal_generators})
        m.generator_cost_a = Param(m.thermal_generators, initialize={g.name: g.cost_a_pu for g in self.net.thermal_generators})
        m.generator_cost_b = Param(m.thermal_generators, initialize={g.name: g.cost_b_pu for g in self.net.thermal_generators})
        m.generator_cost_c = Param(m.thermal_generators, initialize={g.name: g.cost_c_pu for g in self.net.thermal_generators})

        #Loads
        m.load_bus  = Param(m.loads, initialize={l.name: l.bus.name for l in self.net.loads})
        m.load_p    = Param(m.loads, initialize={l.name: l.p_pu for l in self.net.loads})
        m.load_q    = Param(m.loads, initialize={l.name: l.q_pu for l in self.net.loads})
        m.load_cost_shed = Param(m.loads, initialize={l.name: l.cost_shed_pu for l in self.net.loads})

        #Lines
        m.line_from = Param(m.lines, initialize={ln.name: ln.from_bus.name for ln in self.net.lines})
        m.line_to = Param(m.lines, initialize={ln.name: ln.to_bus.name for ln in self.net.lines})

        g_bus = self.net.g_bus
        b_bus = self.net.b_bus
        bus_names = [b.name for b in self.buses]
        g_dict = {(bus_names[i], bus_names[j]): g_bus[i, j] for i in range(len(bus_names)) for j in range(len(bus_names))}
        b_dict = {(bus_names[i], bus_names[j]): b_bus[i, j] for i in range(len(bus_names)) for j in range(len(bus_names))}

        m.G = Param(m.buses, m.buses, initialize=g_dict)
        m.B = Param(m.buses, m.buses, initialize=b_dict)
        m.flow_max = Param(m.lines, initialize={ln.name: ln.flow_max_pu for ln in self.lines})

        #Bus
        m.btype = Param(m.buses, initialize={b.name: b.btype for b in self.buses})

    # ----------------------------------------------------------------Create Variable Bounds---------------------------------------------------------------------------------------#

    def _theta_bounds(self, m, b):
        if b.btype == BusType.SLACK:
            return (0, 0)
        else:
            return (-np.pi, np.pi)
    
    def _thermal_p_bounds(self, m, g):
        return (m.thermal_pmin[g], m.thermal_pmax[g])
    
    def _thermal_q_bounds(self, m, g):
        return (m.thermal_qmin[g], m.thermal_qmax[g])
    
    def _wnd_p_bounds(self, m, g):
        return (0, m.wind_pmax[g])

    def _create_theta_variables(self):
        m = self.model
        m.theta = Var(m.buses, domain=Reals, doc="Bus Voltage Angle (rad)")

    def _create_variables(self):
        m = self.model

        #thermal_generators
        m.p_pu = Var(m.thermal_generators, domain=NonNegativeReals, doc="Active Power Generation (pu)")
        m.q_pu = Var(m.thermal_generators, domain=Reals, doc="Reactive Power Generation (pu)")

        #Buses
        m.v     = Var(m.buses, domain=NonNegativeReals, doc="Bus Voltage Magnitude (pu)")
        m.theta = Var(m.buses, domain=Reals, doc="Bus Voltage Angle (rad)")

        #Lines
        m.p_flow_out = Var(m.lines, domain=Reals, doc="Flow: From_bus to To_bus (pu)")
        m.p_flow_in  = Var(m.lines, domain=Reals, doc="Flow: To_bus to From_bus (pu)")
        m.q_flow_out = Var(m.lines, domain=Reals, doc="Flow: From_bus to To_bus (pu)")
        m.q_flow_in  = Var(m.lines, domain=Reals, doc="Flow: To_bus to From_bus (pu)")

    def _create_constraints(self):
        m = self.model

        #thermal_generators
        slack_bus = next(b for b in m.buses if m.btype[b] == BusType.SLACK) # Bus type = Slack - Fixing theta = 0
        m.theta[slack_bus].fix(0)
        m.v[slack_bus].fix(1)

        def p_max_rule(m, g):
            return m.p_pu[g] <= m.generator_pmax[g]
        m.p_max_pu = Constraint(m.thermal_generators, rule=p_max_rule, doc="Active Power Generation Max")

        def p_min_rule(m, g):
            return m.p_pu[g] >= m.generator_pmin[g]
        m.p_min_pu = Constraint(m.thermal_generators, rule=p_min_rule, doc="Active Power Generation Min")

        def q_max_rule(m, g):
            return m.q_pu[g] <= m.generator_qmax[g]
        m.q_max_pu = Constraint(m.thermal_generators, rule=q_max_rule, doc="Reactive Power Generation Max")

        def q_min_rule(m, g):
            return m.q_pu[g] >= m.generator_qmin[g]
        m.q_min_pu = Constraint(m.thermal_generators, rule=q_min_rule, doc="Reactive Power Generation Min")

        #Buses
        def v_max_rule(m, b):
            return m.v[b] <= 1.05
        m.v_max = Constraint(m.buses, rule=v_max_rule, doc="Bus Voltage Magnitude Max")

        def v_min_rule(m, b):
            return m.v[b] >= 0.95
        m.v_min = Constraint(m.buses, rule=v_min_rule, doc="Bus Voltage Magnitude Min")

        def theta_bounds_rule(m, b):
            return inequality(-np.pi/2, m.theta[b], np.pi/2)
        m.theta_bounds = Constraint(m.buses, rule=theta_bounds_rule, doc="Bus Voltage Angle Bounds")

        #Lines
        def flow_out_rule(m, ln):
            i = m.line_from[ln]
            j = m.line_to[ln]
            flow = m.v[i]**2 * m.G[i, j] - m.v[i] * m.v[j] * (m.G[i, j] * cos(m.theta[i] - m.theta[j]) + m.B[i, j] * sin(m.theta[i] - m.theta[j]))
            return m.p_flow_out[ln] == flow
        m.flow_out_rule = Constraint(m.lines, rule=flow_out_rule, doc="Flow Out Rule")

        def flow_out_bounds(m, ln):
            return inequality(-m.flow_max[ln], m.p_flow_out[ln], m.flow_max[ln])
        m.flow_out_bounds = Constraint(m.lines, rule=flow_out_bounds, doc="Flow Out Bounds")

        def flow_in_rule(m, ln):
            i = m.line_from[ln]
            j = m.line_to[ln]
            flow = m.v[j]**2 * m.G[j, i] - m.v[j] * m.v[i] * (m.G[j, i] * cos(m.theta[j] - m.theta[i]) + m.B[j, i] * sin(m.theta[j] - m.theta[i]))
            return m.p_flow_in[ln] == flow
        m.flow_in_rule = Constraint(m.lines, rule=flow_in_rule, doc="Flow In Rule")

        def flow_in_bounds(m, ln):
            return inequality(-m.flow_max[ln], m.p_flow_in[ln], m.flow_max[ln])
        m.flow_in_bounds = Constraint(m.lines, rule=flow_in_bounds, doc="Flow In Bounds")

        def flow_out_bounds_q(m, ln):
            i = m.line_from[ln]
            j = m.line_to[ln]
            flow = m.v[i]**2 * m.B[i, j] - m.v[i] * m.v[j] * (m.G[i, j] * sin(m.theta[i] - m.theta[j]) - m.B[i, j] * cos(m.theta[i] - m.theta[j]))
            return m.q_flow_out[ln] == flow
        m.flow_out_bounds_q = Constraint(m.lines, rule=flow_out_bounds_q, doc="Flow Out Bounds q_pu")

        def flow_in_bounds_q(m, ln):
            i = m.line_from[ln]
            j = m.line_to[ln]
            flow = m.v[j]**2 * m.B[j, i] - m.v[j] * m.v[i] * (m.G[j, i] * sin(m.theta[j] - m.theta[i]) - m.B[j, i] * cos(m.theta[j] - m.theta[i]))
            return m.q_flow_in[ln] == flow
        m.flow_in_bounds_q = Constraint(m.lines, rule=flow_in_bounds_q, doc="Flow In Bounds q_pu")

        #Power Balance
        def active_power_balance_rule(m, bus):
            active_generation = sum(m.p_pu[g] if m.generator_bus[g] == bus else 0 for g in m.thermal_generators)
            active_load = sum(m.load_p[l] if m.load_bus[l] == bus else 0 for l in m.loads)
            active_flow_out = sum(m.p_flow_out[ln] if  m.line_from[ln] == bus else 0 for ln in m.lines)
            active_flow_in = sum(m.p_flow_in[ln] if m.line_to[ln] == bus else 0 for ln in m.lines)
            return active_generation + active_flow_in - active_flow_out == active_load
        m.active_power_balance = Constraint(m.buses, rule=active_power_balance_rule, doc="Active Power Balance")

        def reactive_power_balance_rule(m, bus):
            reactive_generation = sum(m.q_pu[g] if m.generator_bus[g] == bus else 0 for g in m.thermal_generators)
            reactive_load = sum(m.load_q[l] if m.load_bus[l] == bus else 0 for l in m.loads)
            reactive_flow_out = sum(m.q_flow_out[ln] if m.line_from[ln] == bus else 0 for ln in m.lines)
            reactive_flow_in = sum(m.q_flow_in[ln] if m.line_to[ln] == bus else 0 for ln in m.lines)
            return reactive_generation + reactive_flow_in - reactive_flow_out == reactive_load
        m.reactive_power_balance = Constraint(m.buses, rule=reactive_power_balance_rule, doc="Reactive Power Balance")

    def _create_objective(self):
        m = self.model
        def objective_rule(m):
            cost = sum(m.generator_cost_b[g] * m.p_pu[g] for g in m.thermal_generators)
            return cost
        m.objective = Objective(rule=objective_rule, sense=minimize, doc="Objective Function")

    
    def _create_results(self):
        m = self.model
        # DataFrame para geradores
        gen_data = []
        for g in m.thermal_generators:
            gen_data.append({
                'Generator': g,
                'P (pu)': value(m.p_pu[g]),
                'Q (pu)': value(m.q_pu[g]),
                'Cost': value(m.generator_cost_b[g]) * value(m.p_pu[g])
            })
        self.gen_results = pd.DataFrame(gen_data)

        # DataFrame para barras
        bus_data = []
        for b in m.buses:
            bus_data.append({
                'Bus': b,
                'V (pu)': value(m.v[b]),
                'Theta (rad)': value(m.theta[b])
            })
        self.bus_results = pd.DataFrame(bus_data)

        # DataFrame para linhas
        line_data = []
        for ln in m.lines:
            line_data.append({
                'Line': ln,
                'P_out (pu)': value(m.p_flow_out[ln]),
                'P_in (pu)': value(m.p_flow_in[ln]),
                'Q_out (pu)': value(m.q_flow_out[ln]),
                'Q_in (pu)': value(m.q_flow_in[ln])
            })
        self.line_results = pd.DataFrame(line_data)

        self.objective = value(m.objective)

    def print_results(self):
        print("\n===== Economic Dispatch Results =====")
        print(f"Objective Value: {self.objective:.4f}\n")
        print("---- Generator Results ----")
        print(self.gen_results.to_string(index=False))
        print("\n---- Bus Results ----")
        print(self.bus_results.to_string(index=False))
        print("\n---- Line Results ----")
        print(self.line_results.to_string(index=False))

    def solve(self, solver_name='ipopt', tee=False):
        solver = SolverFactory('ipopt', tee=tee)
        solver.solve(self.model)
        self._create_results()
        return {
            'objective': self.objective,
            'gen_results': self.gen_results,
            'bus_results': self.bus_results,
            'line_results': self.line_results
        }
    
if __name__ == "__main__":
    from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
    #14bus
    net = Network(sb_mva=100)
    #Buses                         
    Bus(net, id= 1, btype=BusType.SLACK)
    Bus(net, id= 2, btype=BusType.PQ)
    Load(id= 1, bus=net.buses[ 0], p_mw=21.70, q_mvar=2.70)
    Load(id= 2, bus=net.buses[ 1], p_mw=94.20, q_mvar=19.00)
    ThermalGenerator(id= 1, bus=net.buses[ 0], p_max_mw=5000, q_max_mvar=50, cost_b_mw=1)
    ThermalGenerator(id= 2, bus=net.buses[ 1], p_max_mw=200, q_max_mvar=200, cost_b_mw=2)
    Line(id= 1, from_bus=net.buses[ 0], to_bus=net.buses[ 1], r_pu=0.01938, x_pu=0.05917, shunt_half_pu=0.0264, flow_max_pu=99)     
    Line(id= 2, from_bus=net.buses[ 1], to_bus=net.buses[ 0], r_pu=0.01938, x_pu=0.05917, shunt_half_pu=0.0264, flow_max_pu=99)

    #Economic Dispatch
    ed = Economic_Dispatch(net)
    ld = LinearDispatch(net)
    results = ed.solve(tee=True)
    ed.print_results()
    ld_results = ld.solve_loss(verbose=True, detailed_output=True)
    #Print Results
    # print("Objective Value AC:", results['objective'])
    # print("Objective Value Linear Dispatch:", ld_results['FOB_Value'])