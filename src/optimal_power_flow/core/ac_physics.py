
from pyomo.environ import *
import numpy as np
from power import Network

class OPFAC(OPFBaseModel):
    """
    Pyomo model for AC Optimal Power Flow (AC-OPF) problems.
    This class extends the OPFBaseModel to include AC power flow physics,
    such as voltage magnitudes, angles, and power flow equations.
    """

    def __init__(self, network: Network):
        super().__init__(network)

    def _build_base_model(self):
        """
        Constructs the base Pyomo model with AC power flow variables and constraints.
        """
        super()._build_base_model()
        self._create_ac_variables()
        self._create_ac_constraints()

    def _create_ac_variables(self):
        """
        Defines the AC power flow variables for the Pyomo model.
        """
        model = self.model

        # Voltage magnitude and angle at each bus
        model.Vm = Var(model.BUSES, model.T, within=NonNegativeReals, bounds=(0.95, 1.05), initialize=1.0)
        model.Va = Var(model.BUSES, model.T, within=Reals, bounds=(-np.pi, np.pi), initialize=0.0)

        # Active and reactive power generation at each generator
        model.Pg = Var(model.GENERATORS, model.T, within=Reals, initialize=0.0)
        model.Qg = Var(model.GENERATORS, model.T, within=Reals, initialize=0.0)

    def _create_ac_constraints(self):
        """
        Defines the AC power flow constraints for the Pyomo model.
        """
        model = self.model

        # Power balance constraints at each bus
        def power_balance_rule(m, b, t):
            Pg_sum = sum(m.Pg[g, t] for g in self.generators if self.generators[g].bus == b)
            Qg_sum = sum(m.Qg[g, t] for g in self.generators if self.generators[g].bus == b)
            Pd = sum(ld.active_power for ld in self.loads.values() if ld.bus == b)
            Qd = sum(ld.reactive_power for ld in self.loads.values() if ld.bus == b)

            # Active power balance
            active_power_balance = Pg_sum - Pd - sum(
                self._calculate_line_flow_active(m, b, l, t) for l in self.lines if self.lines[l].from_bus == b or self.lines[l].to_bus == b