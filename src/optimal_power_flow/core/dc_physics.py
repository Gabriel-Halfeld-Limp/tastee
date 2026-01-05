
from pyomo.environ import *
import numpy as np
from power import Network
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
        self._create_dc_parameters()
        self._create_dc_variables()
        self._create_dc_constraints()

#------------------------------------------Create Mutable Parameters and Update Model------------------------------------------#
    def _create_mutable_parameters(self):
        """
        Cria parâmetros mutáveis para o modelo Pyomo.
        """
        self._create_load_params()
        self._create_wind_params()
        self._create_bess_params()

    def _create_load_params(self):
        """
        Cria parâmetros de Carga Ativa.
        """
        m = self.model
        
        # Parâmetro de Carga Ativa em p.u.
        def load_active_init(m, l): return self.loads[l].p_pu
        m.load_p_pu = Param(m.LOADS, initialize=load_active_init, within=NonNegativeReals, mutable=True)

    def _create_wind_params(self):
        """
        Cria parâmetros de Geração Eólica Máxima.
        """
        m = self.model
        
        # Parâmetro de Geração Eólica Máxima em p.u.
        def wind_gen_max_init(m, g): return self.wind_generators[g].p_max_pu
        m.wind_max_p_pu = Param(m.WIND_GENERATORS, initialize=wind_gen_max_init, within=NonNegativeReals, mutable=True)

    def _create_bess_params(self):
        """
        Cria parâmetros de Bateria.
        """
        m = self.model
        
        # Parâmetro de Capacidade Máxima de Bateria em p.u.
        def bess_soc_init(m, g): return self.bess[g].soc_pu
        m.bess_soc_pu = Param(m.BESS, initialize=bess_soc_init, within=NonNegativeReals, mutable=True)

    def _update_model(self):
        """
        Atualiza o modelo Pyomo com os novos parâmetros.
        """
        self._update_load_params()
        self._update_wind_params()
        self._update_bess_params()
    
    def _update_load_params(self):
        """
        Atualiza os parâmetros de Carga Ativa no modelo Pyomo.
        """
        m = self.model
        for l in m.LOADS:
            m.load_p_pu[l] = self.loads[l].p_pu
    
    def _update_wind_params(self):
        """
        Atualiza os parâmetros de Geração Eólica Máxima no modelo Pyomo.
        """
        m = self.model
        for g in m.WIND_GENERATORS:
            m.wind_max_p_pu[g] = self.wind_generators[g].p_max_pu
    
    def _update_bess_params(self):
        """
        Atualiza os parâmetros de Bateria no modelo Pyomo.
        """
        m = self.model
        for g in m.BESS:
            m.bess_soc_pu[g] = self.bess[g].soc_pu
    
#-------------------------------------------------------------Create Variables-------------------------------------------------#

    def _create_dc_variables(self):