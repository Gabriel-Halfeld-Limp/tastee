from pyomo.environ import *
import numpy as np
from power import Network, BusType
from optimal_power_flow.core.base import OPFBaseModel

class OPFAC(OPFBaseModel):
    """
    Pyomo model for AC Optimal Power Flow (AC-OPF) problems.
    This class extends the OPFBaseModel to include AC power flow physics,
    such as voltage magnitudes, angles, and power flow equations.
    """

    def __init__(self, network: Network):
        super().__init__(network)

    def build_physics(self):
        """
        Constructs the Pyomo model with AC power flow variables and constraints.
        """
        self._build_base_model() # Set creation
        self.build_physics_on_container(self.model)

    def build_physics_on_container(self, container):
        """
        Constructs the Pyomo within the given container for further multiple scenarios or time periods Blocks.
        """
        self.create_bus_block(container)
        self.create_thermal_block(container)
        self.create_wind_block(container)
        self.create_bess_block(container)
        self.create_load_block(container)
        self.create_line_block(container)
        self.add_nodal_balance_constraints(container)

    def update_model(self):
        """
        Atualiza o modelo Pyomo com os novos parâmetros.
        """
        self.update_load_params()
        self.update_wind_params()
        self.update_bess_params()
    
    @property
    def sets(self):
        """Returns base sets along with AC-specific sets."""
        return self.model

    # ------------- Thermal Generator ---------------#
    def create_thermal_block(self, model):
        self.create_thermal_variables(model)

    def create_thermal_variables(self, model):
        m = model
        m.p_thermal = Var(m.THERMAL_GENERATORS, bounds=lambda m, g: (self.thermal_generators[g].p_min_pu, self.thermal_generators[g].p_max_pu), initialize=0)
        m.q_thermal = Var(m.THERMAL_GENERATORS, bounds=lambda m, g: (self.thermal_generators[g].q_min_pu, self.thermal_generators[g].q_max_pu), initialize=0)

    # ------------- Load ---------------#
    def create_load_block(self, model):
        self.create_load_params(model)
        self.create_load_shed_variables(model)

    def create_load_params(self, model):
        m = model
        m.load_p_pu = Param(m.LOADS, initialize=lambda m, l: self.loads[l].p_pu, within=NonNegativeReals, mutable=True)
        m.load_q_pu = Param(m.LOADS, initialize=lambda m, l: getattr(self.loads[l], "q_pu", 0.0), within=Reals, mutable=True)

    def create_load_shed_variables(self, model):
        m = model
        m.p_shed = Var(m.LOADS, within=NonNegativeReals, bounds=lambda m, l: (0, m.load_p_pu[l]), initialize=0)
        m.Shed_Max_Constraint = Constraint(m.LOADS, rule=lambda m, l: m.p_shed[l] <= m.load_p_pu[l])
        
        m.q_shed = Var(m.LOADS, domain=Reals, initialize=0) #Infinity bounds for convergence

    def update_load_params(self, model):
        m = model
        for l in m.LOADS:
            m.load_p_pu[l] = self.loads[l].p_pu
            if hasattr(self.loads[l], "q_pu"):
                m.load_q_pu[l] = self.loads[l].q_pu

    # ------------- Wind Generators ---------------#
    def create_wind_block(self, model):
        self.create_wind_params(model)
        self.create_wind_variables(model)
        self.create_wind_constraints(model)

    def create_wind_params(self, model):
        m = model
        m.wind_max_p_pu = Param(m.WIND_GENERATORS, initialize=lambda m, g: self.wind_generators[g].p_max_pu, within=NonNegativeReals, mutable=True)

    def create_wind_variables(self, model):
        m = model
        m.p_wind = Var(m.WIND_GENERATORS, bounds=(0, None), initialize=lambda m, g: self.wind_generators[g].p_max_pu)
        m.q_wind = Var(m.WIND_GENERATORS, initialize=0)
    
    def create_wind_constraints(self, model):
        m = model
        m.Wind_Max_Constraint = Constraint(m.WIND_GENERATORS, rule=lambda m, g: m.p_wind[g] <= m.wind_max_p_pu[g])
        def wind_inverter_rule(m, g):
            s_max = self.wind_generators[g].inverter_s_max_pu
            if s_max is None:
                return m.q_wind[g] == 0
            return m.q_wind[g]**2 + m.p_wind[g]**2 <= s_max**2
        m.Wind_Inverter_Constraint = Constraint(m.WIND_GENERATORS, rule=wind_inverter_rule)

    def update_wind_params(self, model):
        m = model
        for g in m.WIND_GENERATORS:
            m.wind_max_p_pu[g] = self.wind_generators[g].p_max_pu

    # ------------- Battery (BESS) ---------------#
    def create_bess_block(self, model):
        self.create_bess_params(model)
        self.create_bess_variables(model)
        self.add_bess_constraints(model)
    def create_bess_params(self, model):
        m = model
        m.bess_soc_pu = Param(m.BESS, initialize=lambda m, g: self.bess[g].soc_pu, within=NonNegativeReals, mutable=True)

    def create_bess_variables(self, model):
        m = model
        def charge_bounds_rule(m,g): return (0, self.bess[g].max_charge_rate_pu)
        def discharge_bounds_rule(m,g): return (0, self.bess[g].max_discharge_rate_pu)
        m.p_bess_out = Var(m.BESS, bounds=discharge_bounds_rule, initialize=0)
        m.p_bess_in = Var(m.BESS, bounds=charge_bounds_rule, initialize=0)
        m.q_bess = Var(m.BESS, initialize=0)

    def add_bess_constraints(self, model):
        m = model
        def net_energy(m, g):
            batt = self.bess[g]
            charge = m.p_bess_in[g] * batt.efficiency_charge
            discharge = m.p_bess_out[g] / batt.efficiency_discharge
            return charge - discharge
        
        def bess_soc_max_rule(m, g):
            batt = self.bess[g]
            return m.bess_soc_pu[g] + net_energy(m, g) <= batt.capacity_pu
        m.BESS_SOC_Max_Constraint = Constraint(m.BESS, rule=bess_soc_max_rule)

        def bess_soc_min_rule(m, g):
            batt = self.bess[g]
            return m.bess_soc_pu[g] + net_energy(m, g) >= 0
        m.BESS_SOC_Min_Constraint = Constraint(m.BESS, rule=bess_soc_min_rule)

        def bess_inverter_rule(m, g):
            batt = self.bess[g]
            s_max = batt.inverter_s_max_pu
            if s_max is None:
                return m.q_bess[g] == 0
            return m.q_bess[g]**2 + (m.p_bess_out[g] - m.p_bess_in[g])**2 <= s_max**2
        m.BESS_Inverter_Constraint = Constraint(m.BESS, rule=bess_inverter_rule)

    def update_bess_params(self, model):
        m = model
        for g in m.BESS:
            m.bess_soc_pu[g] = self.bess[g].soc_pu

    # ------------- Bus ---------------#
    def create_bus_block(self, model):
        self.create_bus_params(model)
        self.create_bus_voltage_variables(model)

    def create_bus_params(self, model):
        m = model
        m.bus_v_min = Param(m.BUSES, initialize=lambda m, b: self.buses[b].v_min_pu, within=NonNegativeReals, mutable=True)
        m.bus_v_max = Param(m.BUSES, initialize=lambda m, b: self.buses[b].v_max_pu, within=NonNegativeReals, mutable=True)

    def create_bus_voltage_variables(self, model):
        m = model
        m.v_pu = Var(m.BUSES, bounds=lambda m, b: (m.bus_v_min[b], m.bus_v_max[b]), initialize=1.0)
        m.theta_rad = Var(m.BUSES, bounds=(-np.pi, np.pi), initialize=0)
        # Fix slack bus angle and voltage
        for b in self.buses.values():
            if b.btype == BusType.SLACK:
                m.theta_rad[b.name].fix(0)

    # ------------- Lines ---------------#
    def create_line_block(self, model):
        self.create_flow_variables(model)
        self.flow_limits_rule(model)

    def create_flow_variables(self, model):
        m = model
        m.p_flow_out = Var(m.LINES, domain=Reals, initialize=0)
        m.p_flow_in = Var(m.LINES, domain=Reals, initialize=0)
        m.q_flow_out = Var(m.LINES, domain=Reals, initialize=0)
        m.q_flow_in = Var(m.LINES, domain=Reals, initialize=0)

        # Helper para índices
        def get_idx(bus_id): return self.net.bus_idx[bus_id]

        # --- FLUXO ATIVO (P) ---
        # P geralmente ignora shunt (G_shunt ≈ 0), então Y_ij (série) basta.
        
        def flow_out_rule(m, ln):
            line = self.lines[ln]
            i_idx = get_idx(line.from_bus.id)
            j_idx = get_idx(line.to_bus.id)
            
            # Recupera a parte série da Ybus (lembrando que Y_ij = -y_serie)
            G_ij = self.net.g_bus[i_idx, j_idx]
            B_ij = self.net.b_bus[i_idx, j_idx]
            
            i = line.from_bus.name
            j = line.to_bus.name
            theta_ij = m.theta_rad[i] - m.theta_rad[j]
            
            # Equação Padrão usando Elementos da Ybus (-G_ij = g_linha)
            return m.p_flow_out[ln] == (
                -G_ij * m.v_pu[i]**2 
                + m.v_pu[i] * m.v_pu[j] * (G_ij * cos(theta_ij) + B_ij * sin(theta_ij))
            )
        m.flow_out_rule = Constraint(m.LINES, rule=flow_out_rule)

        def flow_in_rule(m, ln):
            line = self.lines[ln]
            i_idx = get_idx(line.from_bus.id)
            j_idx = get_idx(line.to_bus.id)
            
            G_ji = self.net.g_bus[j_idx, i_idx]
            B_ji = self.net.b_bus[j_idx, i_idx]
            
            i = line.from_bus.name
            j = line.to_bus.name
            theta_ji = m.theta_rad[j] - m.theta_rad[i]
            
            return m.p_flow_in[ln] == (
                -G_ji * m.v_pu[j]**2 
                + m.v_pu[j] * m.v_pu[i] * (G_ji * cos(theta_ji) + B_ji * sin(theta_ji))
            )
        m.flow_in_rule = Constraint(m.LINES, rule=flow_in_rule)

        # --- FLUXO REATIVO (Q) ---
        def flow_out_q_rule(m, ln):
            line = self.lines[ln]
            i_idx = get_idx(line.from_bus.id)
            j_idx = get_idx(line.to_bus.id)
            
            G_ij = self.net.g_bus[i_idx, j_idx]
            B_ij = self.net.b_bus[i_idx, j_idx]
            
            b_sh = line.shunt_half_pu 
            
            i = line.from_bus.name
            j = line.to_bus.name
            theta_ij = m.theta_rad[i] - m.theta_rad[j]
            
            return m.q_flow_out[ln] == (
                (B_ij - b_sh) * m.v_pu[i]**2 
                + m.v_pu[i] * m.v_pu[j] * (G_ij * sin(theta_ij) - B_ij * cos(theta_ij))
            )
        m.flow_out_q_rule = Constraint(m.LINES, rule=flow_out_q_rule)

        def flow_in_q_rule(m, ln):
            line = self.lines[ln]
            i_idx = get_idx(line.from_bus.id)
            j_idx = get_idx(line.to_bus.id)
            
            G_ji = self.net.g_bus[j_idx, i_idx]
            B_ji = self.net.b_bus[j_idx, i_idx]
            b_sh = line.shunt_half_pu
            
            i = line.from_bus.name
            j = line.to_bus.name
            theta_ji = m.theta_rad[j] - m.theta_rad[i]
            
            return m.q_flow_in[ln] == (
                (B_ji - b_sh) * m.v_pu[j]**2 
                + m.v_pu[j] * m.v_pu[i] * (G_ji * sin(theta_ji) - B_ji * cos(theta_ji))
            )
        m.flow_in_q_rule = Constraint(m.LINES, rule=flow_in_q_rule)

    def flow_limits_rule(self, model):
        m = model

        def thermal_limit_out_rule(m, ln):
            limit = self.lines[ln].flow_max_pu
            if limit is None or limit == 0:
                return Constraint.Skip
            return m.p_flow_out[ln]**2 + m.q_flow_out[ln]**2 <= limit**2
        m.thermal_limit_out = Constraint(m.LINES, rule=thermal_limit_out_rule)

        def thermal_limit_in_rule(m, ln):
            limit = self.lines[ln].flow_max_pu
            if limit is None or limit == 0:
                return Constraint.Skip
            return m.p_flow_in[ln]**2 + m.q_flow_in[ln]**2 <= limit**2
        m.thermal_limit_in = Constraint(m.LINES, rule=thermal_limit_in_rule)

    # ------------- Nodal Balance ---------------#
    def add_nodal_balance_constraints(self, model):
        m = model
        def active_power_balance_rule(m, bus):
            # 1. Geração (Sources)
            gen_thermal = sum(m.p_thermal[g] for g in m.THERMAL_GENERATORS if self.thermal_generators[g].bus.name == bus)
            gen_wind = sum(m.p_wind[g] for g in m.WIND_GENERATORS if self.wind_generators[g].bus.name == bus)
            # Bateria: P_out (Descarrega) é injeção, P_in (Carrega) é retirada
            gen_bess = sum(m.p_bess_out[g] - m.p_bess_in[g] for g in m.BESS if self.bess[g].bus.name == bus)
            
            # 2. Cargas e Shed (Sinks)
            load = sum(m.load_p_pu[l] for l in m.LOADS if self.loads[l].bus.name == bus)
            shed = sum(m.p_shed[l] for l in m.LOADS if self.loads[l].bus.name == bus)
            
            # 3. Fluxos nas Linhas (AMBOS representam potência SAINDO da barra para a linha)
            # p_flow_out: Sai da barra 'from'
            # p_flow_in: Sai da barra 'to'
            flows_leaving_bus = sum(m.p_flow_out[ln] for ln in m.LINES if self.lines[ln].from_bus.name == bus) + \
                                sum(m.p_flow_in[ln] for ln in m.LINES if self.lines[ln].to_bus.name == bus)
            
            # Equação Fundamental: (Geração + Corte) - Carga = Tudo que sai para as linhas
            return gen_thermal + gen_wind + gen_bess + shed - flows_leaving_bus == load
            
        m.active_power_balance = Constraint(m.BUSES, rule=active_power_balance_rule)

        def reactive_power_balance_rule(m, bus):
            # Geração Q
            gen_q_thermal = sum(m.q_thermal[g] for g in m.THERMAL_GENERATORS if self.thermal_generators[g].bus.name == bus)
            gen_q_wind = sum(m.q_wind[g] for g in m.WIND_GENERATORS if self.wind_generators[g].bus.name == bus)
            gen_q_bess = sum(m.q_bess[g] for g in m.BESS if self.bess[g].bus.name == bus)

            # Carga Q
            load_q = sum(m.load_q_pu[l] for l in m.LOADS if self.loads[l].bus.name == bus)
            shed_q = sum(m.q_shed[l] for l in m.LOADS if self.loads[l].bus.name == bus)

            # Fluxos Q Saindo da barra
            flows_q_leaving =   sum(m.q_flow_out[ln] for ln in m.LINES if self.lines[ln].from_bus.name == bus) + \
                                sum(m.q_flow_in[ln] for ln in m.LINES if self.lines[ln].to_bus.name == bus)
            
            return gen_q_thermal + gen_q_wind + gen_q_bess + shed_q - flows_q_leaving ==  load_q
            
        m.reactive_power_balance = Constraint(m.BUSES, rule=reactive_power_balance_rule)
    
    # ------------- Model Update ---------------#
    def update_network_with_results(self, model):
        """
        Update the network object with results from the Pyomo model.
        """
        m = model
        for g in m.THERMAL_GENERATORS:
            self.thermal_generators[g].p_pu = value(m.p_thermal[g])
            self.thermal_generators[g].q_pu = value(m.q_thermal[g])

        for g in m.WIND_GENERATORS:
            self.wind_generators[g].p_pu = value(m.p_wind[g])
            self.wind_generators[g].q_pu = value(m.q_wind[g])

        for g in m.BESS:
            self.bess[g].p_pu = value(m.p_bess_out[g]) - value(m.p_bess_in[g])
            self.bess[g].q_pu = value(m.q_bess[g])
        
        for l in m.LOADS:
            self.loads[l].p_shed_pu = value(m.p_shed[l])
            self.loads[l].q_shed_pu = value(m.q_shed[l])
        
        for b in m.BUSES:
            self.buses[b].theta_rad = value(m.theta_rad[b])
            self.buses[b].v_pu = value(m.v_pu[b])
        
        for l in m.LINES:
            self.lines[l].p_flow_out_pu = value(m.p_flow_out[l])
            self.lines[l].p_flow_in_pu = value(m.p_flow_in[l])
            self.lines[l].q_flow_out_pu = value(m.q_flow_out[l])
            self.lines[l].q_flow_in_pu = value(m.q_flow_in[l])