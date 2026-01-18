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
        self._build_base_model()
        self.build_physics_on_container(self.model)

    def build_physics_on_container(self, container):
        """
        Build the DC-OPF physics inside the given container (e.g., scenario block).
        """
        self.create_thermal_block(container)
        self.create_wind_block(container)
        self.create_bess_block(container)
        self.create_load_block(container)
        self.create_bus_block(container)
        self.create_line_block(container)
        self.add_nodal_balance_constraints(container)

    def update_model(self, container=None):
        """
        Atualiza o modelo Pyomo com os novos parâmetros.
        """
        if container is None:
            container = self.model
        self.update_load_params(container)
        self.update_wind_params(container)
        self.update_bess_params(container)

    @property
    def base_sets(self):
        """Alias for the container where base sets (root model) live."""
        return self.model

    # ------------- Thermal Generator ---------------#
    def create_thermal_block(self, container):
        """
        Create all thermal generator-related components (variables).
        """
        self.create_thermal_variables(container)
    
    def create_thermal_variables(self, container):
        """
        Create thermal generation variables.
        """
        m0 = self.base_sets
        m = container
        m.p_thermal = Var(m0.THERMAL_GENERATORS, bounds=lambda m, g: (self.thermal_generators[g].p_min_pu, self.thermal_generators[g].p_max_pu), initialize=0)

    # ------------- Load ---------------#
    def create_load_block(self, container):
        """
        Create all load-related components (params, variables, constraints).
        """
        self.create_load_params(container)
        self.create_load_shed_variables(container)

    def create_load_params(self, container):
        """
        Create active load parameters.
        """
        m0 = self.base_sets
        m = container
        m.load_p_pu = Param(m0.LOADS, initialize=lambda m, l: self.loads[l].p_pu, within=NonNegativeReals, mutable=True)

    def create_load_shed_variables(self, container):
        """
        Create load shedding variables and constraints.
        """
        m0 = self.base_sets
        m = container
        m.p_shed = Var(m0.LOADS, bounds=lambda m, l: (0, m.load_p_pu[l]), initialize=0)
        # Constraint: load shed cannot exceed load
        m.Shed_Max_Constraint = Constraint(m0.LOADS, rule=lambda m, l: m.p_shed[l] <= m.load_p_pu[l])

    def update_load_params(self, container=None):
        """
        Update load parameters in the Pyomo model.
        """
        if container is None:
            container = self.model
        m0 = self.base_sets
        m = container
        for l in m0.LOADS:
            m.load_p_pu[l] = self.loads[l].p_pu

    # ------------- Wind Generators ---------------#
    def create_wind_block(self, container):
        """
        Cria todos os componentes relacionados à geração eólica (parâmetros, variáveis, restrições).
        """
        self.create_wind_params(container)
        self.create_wind_variables(container) 

    def create_wind_params(self, container):
        """
        Create wind generation max parameters.
        """
        m0 = self.base_sets
        m = container
        m.wind_max_p_pu = Param(m0.WIND_GENERATORS, initialize=lambda m, g: self.wind_generators[g].p_max_pu, within=NonNegativeReals, mutable=True)

    def create_wind_variables(self, container):
        """
        Create wind generation variables and constraints.
        """
        m0 = self.base_sets
        m = container
        m.p_wind = Var(m0.WIND_GENERATORS, bounds=(0, None), initialize=0)
        # Constraint: wind generation cannot exceed available wind
        m.Wind_Max_Constraint = Constraint(m0.WIND_GENERATORS, rule=lambda m, g: m.p_wind[g] <= m.wind_max_p_pu[g])

    def update_wind_params(self, container=None):
        """
        Atualiza os parâmetros de Geração Eólica Máxima no modelo Pyomo.
        """
        if container is None:
            container = self.model
        m0 = self.base_sets
        m = container
        for g in m0.WIND_GENERATORS:
            m.wind_max_p_pu[g] = self.wind_generators[g].p_max_pu
    
    # ------------- Battery (BESS) ---------------#
    def create_bess_block(self, container):
        """
        Cria todos os componentes relacionados à bateria (parâmetros, variáveis, restrições).
        """
        self.create_bess_params(container)
        self.create_bess_variables(container)
        self.add_bess_constraints(container)

    def create_bess_params(self, container):
        """
        Create battery SOC parameters.
        """
        m0 = self.base_sets
        m = container
        m.bess_soc_pu = Param(m0.BESS, initialize=lambda m, g: self.bess[g].soc_pu, within=NonNegativeReals, mutable=True)

    def create_bess_variables(self, container):
        """
        Create battery (BESS) operation variables.
        """
        m0 = self.base_sets
        m = container
        def charge_bounds_rule(m,g): return (0, self.bess[g].dc_max_charge_rate_pu)
        def discharge_bounds_rule(m,g): return (0, self.bess[g].dc_max_discharge_rate_pu)
        m.p_bess_out = Var(m0.BESS, bounds=discharge_bounds_rule, initialize=0)
        m.p_bess_in = Var(m0.BESS, bounds=charge_bounds_rule, initialize=0)

    def add_bess_constraints(self, container):
        """
        Adiciona restrições operacionais para baterias.
        """
        m0 = self.base_sets
        m = container

        def net_energy(m, g):
            batt = self.bess[g]
            charge = m.p_bess_in[g] * batt.efficiency_charge
            discharge = m.p_bess_out[g] / batt.efficiency_discharge
            return charge - discharge
        
        def bess_soc_max_rule(m, g):
            batt = self.bess[g]
            return m.bess_soc_pu[g] + net_energy(m, g) <= batt.capacity_pu
        m.BESS_SOC_Max_Constraint = Constraint(m0.BESS, rule=bess_soc_max_rule)

        def bess_soc_min_rule(m, g):
            return m.bess_soc_pu[g] + net_energy(m, g) >= 0
        m.BESS_SOC_Min_Constraint = Constraint(m0.BESS, rule=bess_soc_min_rule)

    def update_bess_params(self, container=None):
        """
        Atualiza os parâmetros de Bateria no modelo Pyomo.
        """
        if container is None:
            container = self.model
        m0 = self.base_sets
        m = container
        for g in m0.BESS:
            m.bess_soc_pu[g] = self.bess[g].soc_pu
    # ------------- Bus ---------------#
    def create_bus_block(self, container):
        """
        Create all bus-related components (variables, constraints).
        """
        self.create_bus_params(container)
        self.create_bus_angle_variables(container)

    def create_bus_params(self, container):
        """
        Create bus-related parameters if needed.
        """
        m0 = self.base_sets
        m = container
        m.bus_loss_pu = Param(m0.BUSES, initialize=0, within=Reals, mutable=True)

    def create_bus_angle_variables(self, container):
        """
        Create bus angle (theta_rad) variables for DC-OPF.
        """
        m0 = self.base_sets
        m = container
        m.theta_rad = Var(m0.BUSES, bounds=(-np.pi, np.pi), initialize=0)
        # Fix slack bus angle to 0
        for b in self.buses.values():
            if b.btype == BusType.SLACK:
                m.theta_rad[b.name].setlb(0)
                m.theta_rad[b.name].setub(0)

    def add_nodal_balance_constraints(self, container):
        """
        Adiciona restrições de balanço nodal para cada barra.
        """
        m0 = self.base_sets
        m = container
        def nodal_balance_rule(m, b):
            # Soma das gerações (térmica, eólica, bateria) - cargas + shed + soma dos fluxos
            gen_thermal = sum(m.p_thermal[g] for g in m0.THERMAL_GENERATORS if self.thermal_generators[g].bus.name == b)
            gen_wind = sum(m.p_wind[g] for g in m0.WIND_GENERATORS if self.wind_generators[g].bus.name == b)
            gen_bess_out = sum(m.p_bess_out[g] for g in m0.BESS if self.bess[g].bus.name == b)
            gen_bess_in = sum(m.p_bess_in[g] for g in m0.BESS if self.bess[g].bus.name == b)
            load = sum(m.load_p_pu[l] for l in m0.LOADS if self.loads[l].bus.name == b)
            shed = sum(m.p_shed[l] for l in m0.LOADS if self.loads[l].bus.name == b)
            loss = m.bus_loss_pu[b]
            flow_in = sum(m.flow[l] for l in m0.LINES if self.lines[l].to_bus.name == b)
            flow_out = sum(m.flow[l] for l in m0.LINES if self.lines[l].from_bus.name == b)
            # geração total + shed + fluxo líquido = carga
            return gen_thermal + gen_wind + gen_bess_out - gen_bess_in + shed + flow_in - flow_out == load + loss
        m.NodalBalanceConstraint = Constraint(m0.BUSES, rule=nodal_balance_rule)
    
    def update_bus_params(self, container=None):
        """
        Update bus parameters in the Pyomo model if needed.
        """
        if container is None:
            container = self.model
        m0 = self.base_sets
        m = container
        for b in m0.BUSES:
            m.bus_loss_pu[b] = self.buses[b].loss
    
    # ------------ Lines ---------------#
    def create_line_block(self, container):
        """
        Create all line-related components (variables, constraints).
        """
        self.create_flow_variables(container)
        self.add_dc_flow_constraints(container)

    def create_flow_variables(self, container):
        """
        Create line flow variables for DC-OPF.
        """
        m0 = self.base_sets
        m = container
        m.flow = Var(m0.LINES, bounds=lambda m, l: (-self.lines[l].flow_max_pu, self.lines[l].flow_max_pu), initialize=0)
    
    def add_dc_flow_constraints(self, container):
        """
        Adiciona restrições de fluxo DC para cada linha.
        """
        m0 = self.base_sets
        m = container
        def dc_flow_rule(m, l):
            line = self.lines[l]
            return m.flow[l] == (m.theta_rad[line.from_bus.name] - m.theta_rad[line.to_bus.name]) / line.x_pu
        m.DCFlowConstraint = Constraint(m0.LINES, rule=dc_flow_rule)
    
    # ------------- Model Update ---------------#
    def update_network_with_results(self, container=None):
        """
        Update the network object with results from the Pyomo model.
        """
        m = container if container is not None else self.model
        m0 = self.base_sets
        for g in m0.THERMAL_GENERATORS:
            self.thermal_generators[g].p_pu = value(m.p_thermal[g])
        
        for g in m0.WIND_GENERATORS:
            self.wind_generators[g].p_pu = value(m.p_wind[g])

        for g in m0.BESS:
            self.bess[g].p_pu = value(m.p_bess_out[g]) - value(m.p_bess_in[g])
        
        for l in m0.LOADS:
            self.loads[l].p_shed_pu = value(m.p_shed[l])
        
        for b in m0.BUSES:
            self.buses[b].theta_rad = value(m.theta_rad[b])
        
        for l in m0.LINES:
            self.lines[l].p_flow_out_pu = value(m.flow[l])
            self.lines[l].p_flow_in_pu  = -value(m.flow[l])