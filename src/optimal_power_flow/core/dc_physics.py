from pyomo.environ import *
import numpy as np
from power import Network, BusType
from optimal_power_flow.core.base import OPFBaseModel

class OPFDC(OPFBaseModel):
    """
    Pyomo model for DC Optimal Power Flow (DC-OPF) problems.
    This class extends the OPFBaseModel to include DC power flow physics.
    """

    def __init__(self, network: Network):
        super().__init__(network)

    def build_physics(self):
        """
        Constructs the Pyomo model with DC power flow variables and constraints.
        """
        self.create_thermal_block()
        self.create_wind_block()
        self.create_bess_block()
        self.create_load_block()
        self.create_bus_block()
        self.create_line_block()
    
    def update_model(self):
        """
        Atualiza o modelo Pyomo com os novos parâmetros.
        """
        self.update_load_params()
        self.update_wind_params()
        self.update_bess_params()

    # ------------- Thermal Generator ---------------#
    def create_thermal_block(self):
        """
        Create all thermal generator-related components (variables).
        """
        self.create_thermal_variables()
    
    def create_thermal_variables(self):
        """
        Create thermal generation variables.
        """
        m = self.model
        m.p_thermal = Var(m.THERMAL_GENERATORS, bounds=lambda m, g: (self.thermal_generators[g].p_min_pu, self.thermal_generators[g].p_max_pu), initialize=0)

    # ------------- Load ---------------#
    def create_load_block(self):
        """
        Create all load-related components (params, variables, constraints).
        """
        self.create_load_params()
        self.create_load_shed_variables()

    def create_load_params(self):
        """
        Create active load parameters.
        """
        m = self.model
        m.load_p_pu = Param(m.LOADS, initialize=lambda m, l: self.loads[l].p_pu, within=NonNegativeReals, mutable=True)

    def create_load_shed_variables(self):
        """
        Create load shedding variables and constraints.
        """
        m = self.model
        m.p_shed = Var(m.LOADS, bounds=lambda m, l: (0, m.load_p_pu[l]), initialize=0)
        # Constraint: load shed cannot exceed load
        m.Shed_Max_Constraint = Constraint(m.LOADS, rule=lambda m, l: m.p_shed[l] <= m.load_p_pu[l])

    def update_load_params(self):
        """
        Update load parameters in the Pyomo model.
        """
        m = self.model
        for l in m.LOADS:
            m.load_p_pu[l] = self.loads[l].p_pu

    # ------------- Wind Generators ---------------#
    def create_wind_block(self):
        """
        Cria todos os componentes relacionados à geração eólica (parâmetros, variáveis, restrições).
        """
        self.create_wind_params()
        self.create_wind_variables() 

    def create_wind_params(self):
        """
        Create wind generation max parameters.
        """
        m = self.model
        m.wind_max_p_pu = Param(m.WIND_GENERATORS, initialize=lambda m, g: self.wind_generators[g].p_max_pu, within=NonNegativeReals, mutable=True)

    def create_wind_variables(self):
        """
        Create wind generation variables and constraints.
        """
        m = self.model
        m.p_wind = Var(m.WIND_GENERATORS, bounds=(0, None), initialize=0)
        # Constraint: wind generation cannot exceed available wind
        m.Wind_Max_Constraint = Constraint(m.WIND_GENERATORS, rule=lambda m, g: m.p_wind[g] <= m.wind_max_p_pu[g])

    def update_wind_params(self):
        """
        Atualiza os parâmetros de Geração Eólica Máxima no modelo Pyomo.
        """
        m = self.model
        for g in m.WIND_GENERATORS:
            m.wind_max_p_pu[g] = self.wind_generators[g].p_max_pu
    
    # ------------- Battery (BESS) ---------------#
    def create_bess_block(self):
        """
        Cria todos os componentes relacionados à bateria (parâmetros, variáveis, restrições).
        """
        self.create_bess_params()
        self.create_bess_variables()  # bess part
        self.add_bess_constraints()

    def create_bess_params(self):
        """
        Create battery SOC parameters.
        """
        m = self.model
        m.bess_soc_pu = Param(m.BESS, initialize=lambda m, g: self.bess[g].soc_pu, within=NonNegativeReals, mutable=True)

    def create_bess_variables(self):
        """
        Create battery (BESS) operation variables.
        """
        m = self.model
        m.p_bess_out = Var(m.BESS, bounds=(0, None), initialize=0)
        m.p_bess_in = Var(m.BESS, bounds=(0, None), initialize=0)

    def add_bess_constraints(self):
        """
        Adiciona restrições operacionais para baterias.
        """
        m = self.model
        def bess_soc_rule(m, g):
            return m.p_bess_in[g] + self.bess[g].soc_pu - m.p_bess_out[g] <= self.bess[g].capacity_pu
        m.BESS_SOC_Constraint = Constraint(m.BESS, rule=bess_soc_rule)
        def bess_discharge_rule(m, g):
            return self.bess[g].soc_pu - m.p_bess_out[g] >= 0
        m.BESS_Discharge_Constraint = Constraint(m.BESS, rule=bess_discharge_rule)

    def update_bess_params(self):
        """
        Atualiza os parâmetros de Bateria no modelo Pyomo.
        """
        m = self.model
        for g in m.BESS:
            m.bess_soc_pu[g] = self.bess[g].soc_pu
    # ------------- Bus ---------------#
    def create_bus_block(self):
        """
        Create all bus-related components (variables, constraints).
        """
        self.create_bus_params()
        self.create_bus_angle_variables()
        self.add_dc_flow_constraints()
        self.add_nodal_balance_constraints()
    
    def create_bus_params(self):
        """
        Create bus-related parameters if needed.
        """
        m = self.model
        m.bus_loss_pu = Param(m.BUSES, initialize=0, within=Reals, mutable=True)

    def create_bus_angle_variables(self):
        """
        Create bus angle (theta) variables for DC-OPF.
        """
        m = self.model
        m.theta = Var(m.BUSES, bounds=(-np.pi, np.pi), initialize=0)
        # Fix slack bus angle to 0
        for b in self.buses.values():
            if b.btype == BusType.SLACK:
                m.theta.setlb(b.name, 0)
                m.theta.setub(b.name, 0)

    def add_nodal_balance_constraints(self):
        """
        Adiciona restrições de balanço nodal para cada barra.
        """
        m = self.model
        def nodal_balance_rule(m, b):
            # Soma das gerações (térmica, eólica, bateria) - cargas + shed + soma dos fluxos
            gen_thermal = sum(m.p_thermal[g] for g in m.THERMAL_GENERATORS if self.thermal_generators[g].bus.name == b)
            gen_wind = sum(m.p_wind[g] for g in m.WIND_GENERATORS if self.wind_generators[g].bus.name == b)
            gen_bess_out = sum(m.p_bess_out[g] for g in m.BESS if self.bess[g].bus.name == b)
            gen_bess_in = sum(m.p_bess_in[g] for g in m.BESS if self.bess[g].bus.name == b)
            load = sum(m.load_p_pu[l] for l in m.LOADS if self.loads[l].bus.name == b)
            shed = sum(m.p_shed[l] for l in m.LOADS if self.loads[l].bus.name == b)
            loss = m.bus_loss_pu[b]
            flow_in = sum(m.flow[l] for l in m.LINES if self.lines[l].to_bus.name == b)
            flow_out = sum(m.flow[l] for l in m.LINES if self.lines[l].from_bus.name == b)
            # geração total + shed + fluxo líquido = carga
            return gen_thermal + gen_wind + gen_bess_out - gen_bess_in + shed + flow_in - flow_out == load + loss
        m.NodalBalanceConstraint = Constraint(m.BUSES, rule=nodal_balance_rule)
    
    def update_bus_params(self):
        """
        Update bus parameters in the Pyomo model if needed.
        """
        m = self.model
        for b in m.BUSES:
            m.bus_loss_pu[b] = self.buses[b].loss
    
    # ------------ Lines ---------------#
    def create_line_block(self):
        """
        Create all line-related components (variables, constraints).
        """
        self.create_flow_variables()
        self.add_dc_flow_constraints()

    def create_flow_variables(self):
        """
        Create line flow variables for DC-OPF.
        """
        m = self.model
        m.flow = Var(m.LINES, bounds=lambda m, l: (-self.lines[l].flow_max_pu, self.lines[l].flow_max_pu), initialize=0)
    
    def add_dc_flow_constraints(self):
        """
        Adiciona restrições de fluxo DC para cada linha.
        """
        m = self.model
        def dc_flow_rule(m, l):
            line = self.lines[l]
            return m.flow[l] == (m.theta[line.from_bus.name] - m.theta[line.to_bus.name]) / line.x_pu
        m.DCFlowConstraint = Constraint(m.LINES, rule=dc_flow_rule)