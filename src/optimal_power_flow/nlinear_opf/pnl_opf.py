from pyomo.environ import *
from power import *
import numpy as np
import pandas as pd

class Economic_Dispatch:
    def __init__(self, network: Network):
        self.net = network

        #thermal_generators:
        self.thermal_generators = self.net.thermal_generators

        #Loads:
        self.loads = self.net.loads

        #Buses:
        self.buses = self.net.buses

        #Lines:
        self.lines = self.net.lines

        #Pyomo Model:
        self.model = ConcreteModel()
        self.model.name = 'Economic Dispatch'

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
    
    def _create_sets(self):    
        self.model.thermal_generators = Set(initialize=[g.name for g in self.thermal_generators], doc="Conjunto de geradores") # Cria conjunto de geradores com os nomes
        self.model.loads = Set(initialize=[l.name for l in self.loads], doc="Conjunto de cargas") # Cria conjunto de cargas
        self.model.buses = Set(initialize=[b.name for b in self.buses], doc="Conjunto de barras")  # Cria conjunto de barras
        self.model.lines = Set(initialize=[ln.name for ln in self.lines], doc="Conjunto de linhas") # Cria conjunto de linhas


    def _create_parameters(self):
        #thermal_generators
        m = self.model
        m.generator_bus = Param(m.thermal_generators, initialize={g.name: g.bus.name for g in self.thermal_generators})
        m.generator_pmax = Param(m.thermal_generators, initialize={g.name: g.p_max_pu for g in self.thermal_generators})
        m.generator_pmin = Param(m.thermal_generators, initialize={g.name: g.p_min_pu for g in self.thermal_generators})
        m.generator_qmax = Param(m.thermal_generators, initialize={g.name: g.q_max_pu for g in self.thermal_generators})
        m.generator_qmin = Param(m.thermal_generators, initialize={g.name: g.q_min_pu for g in self.thermal_generators})
        m.generator_cost_a = Param(m.thermal_generators, initialize={g.name: g.cost_a_pu for g in self.thermal_generators})
        m.generator_cost_b = Param(m.thermal_generators, initialize={g.name: g.cost_b_pu for g in self.thermal_generators})
        m.generator_cost_c = Param(m.thermal_generators, initialize={g.name: g.cost_c_pu for g in self.thermal_generators})

        #Loads
        m.load_bus = Param(m.loads, initialize={l.name: l.bus.name for l in self.loads})
        m.load_p= Param(m.loads, initialize={l.name: l.p_pu for l in self.loads})
        m.load_q = Param(m.loads, initialize={l.name: l.q_pu for l in self.loads})

        #Lines
        m.line_from = Param(m.lines, initialize={ln.name: ln.from_bus.name for ln in self.lines})
        m.line_to = Param(m.lines, initialize={ln.name: ln.to_bus.name for ln in self.lines})
        g_bus = self.net.g_bus()
        b_bus = self.net.b_bus()
        bus_names = [b.name for b in self.buses]
        g_dict = {(bus_names[i], bus_names[j]): g_bus[i, j] for i in range(len(bus_names)) for j in range(len(bus_names))}
        b_dict = {(bus_names[i], bus_names[j]): b_bus[i, j] for i in range(len(bus_names)) for j in range(len(bus_names))}

        m.G = Param(m.buses, m.buses, initialize=g_dict)
        m.B = Param(m.buses, m.buses, initialize=b_dict)
        m.flow_max = Param(m.lines, initialize={ln.name: ln.flow_max_pu for ln in self.lines})

        #Bus
        m.b_type = Param(m.buses, initialize={b.name: b.b_type for b in self.buses})

    def _create_variables(self):
        m = self.model

        #thermal_generators
        m.p_pu = Var(m.thermal_generators, domain=NonNegativeReals, doc="Active Power Generation (pu)")
        m.q_pu = Var(m.thermal_generators, domain=Reals, doc="Reactive Power Generation (pu)")

        #Buses
        m.v = Var(m.buses, domain=NonNegativeReals, doc="Bus Voltage Magnitude (pu)")
        m.theta = Var(m.buses, domain=Reals, doc="Bus Voltage Angle (rad)")

        #Lines
        m.p_flow_out = Var(m.lines, domain=Reals, doc="Flow: From_bus to To_bus (pu)")
        m.p_flow_in = Var(m.lines, domain=Reals, doc="Flow: To_bus to From_bus (pu)")
        m.q_flow_out = Var(m.lines, domain=Reals, doc="Flow: From_bus to To_bus (pu)")
        m.q_flow_in = Var(m.lines, domain=Reals, doc="Flow: To_bus to From_bus (pu)")

    def _create_constraints(self):
        m = self.model

        #thermal_generators
        slack_bus = next(b for b in m.buses if m.b_type[b] == BusType.SLACK) # Bus type = Slack - Fixing theta = 0
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
            cost = sum(m.generator_cost_a[g] * m.p_pu[g] for g in m.thermal_generators)
            return cost
        m.objective = Objective(rule=objective_rule, sense=minimize, doc="Objective Function")

    
    def _create_results(self):
        m = self.model
        self.results = {}
        self.results['objective'] = value(m.objective)
        self.results['p_pu'] = {g: value(m.p_pu[g]) for g in m.thermal_generators}
        self.results['q_pu'] = {g: value(m.q_pu[g]) for g in m.thermal_generators}
        self.results['v'] = {b: value(m.v[b]) for b in m.buses}
        self.results['theta'] = {b: value(m.theta[b]) for b in m.buses}
        self.results['p_flow_out'] = {ln: value(m.p_flow_out[ln]) for ln in m.lines}
        self.results['p_flow_in'] = {ln: value(m.p_flow_in[ln]) for ln in m.lines}
        self.results['q_flow_out'] = {ln: value(m.q_flow_out[ln]) for ln in m.lines}
        self.results['q_flow_in'] = {ln: value(m.q_flow_in[ln]) for ln in m.lines}
    
    def solve(self, solver_name='ipopt', tee=False):
        solver = SolverFactory('ipopt', teee=tee)
        solver.solve(self.model)
        self._create_results()
        return self.results
    
if __name__ == "__main__":
        #14bus
    net = Network()


    buses = [                                                 
        Bus(net, id= 1, b_type=BusType.SLACK),
        Bus(net, id= 2, b_type=   BusType.PQ)
    ]

    loads = [
        Load(id= 1, bus=buses[ 0], pb=100, p_input=21.70, q_input=12.70),
        Load(id= 2, bus=buses[ 1], pb=100, p_input=94.20, q_input=19.00)
    ]

    generators = [
        Generator(id= 1, bus=buses[ 0], pb=100, p_max_input=5000, q_max_input=50, cost_a_input=1),
        Generator(id= 2, bus=buses[ 1], pb=100, p_max_input=200, q_max_input=200, cost_a_input=2),
    ]

    lines = [
        Line(id= 1, from_bus=buses[ 0], to_bus=buses[ 1], r=0.01938, x=0.05917, b_half=0.0264, flow_max=99),     
        Line(id= 2, from_bus=buses[ 1], to_bus=buses[ 0], r=0.01938, x=0.05917, b_half=0.0264, flow_max=99),        
    ]