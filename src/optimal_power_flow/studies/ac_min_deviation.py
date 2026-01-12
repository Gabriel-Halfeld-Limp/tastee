from pyomo.environ import *
import pandas as pd
import numpy as np
from optimal_power_flow.core.ac_physics import OPFAC
from power import Network

class ACMinDeviation(OPFAC):
    """
    Pyomo model for AC Minimum Deviation from operating point problems.
    This class extends the OPFAC to include minimum deviation specific components.
    """

    def __init__(self, network: Network):
        super().__init__(network)
        self.build_physics()
        self.build_objective()


    def build_objective(self):
        """
        Define a função objetivo: Minimizar Desvios de Geração e Bateria
        """
        m = self.model
        
        # Desvio Geração Térmica
        deviation_thermal = sum(
            (m.p_thermal[g] - self.thermal_generators[g].p_pu)**2
            for g in m.THERMAL_GENERATORS
        )
        
        # Desvio Operacional de Bateria
        deviation_bess = sum(
            (m.p_bess_out[g] - self.bess[g].p_pu)**2 +
            (m.p_bess_in[g] - self.bess[g].p_pu)**2
            for g in m.BESS
        )

        deviation_eolic = sum(
            (m.p_wind[g] - self.wind_generators[g].p_pu)**2
            for g in m.WIND_GENERATORS
        )

        m.obj = Objective(expr=deviation_thermal + deviation_bess + deviation_eolic, sense=minimize)