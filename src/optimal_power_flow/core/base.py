from pyomo.environ import *
from power import Network

class OPFBaseModel:
    """
    Pyomo base model for Optimal Power Flow (OPF) problems.
    This class sets up the fundamental structure for OPF models, including:
    - Initializing the Pyomo model.
    - Defining sets for buses, generators, branches
    """

    def __init__(self, network: Network):

        self.net       = network
        self.model     = ConcreteModel()

        # Generators maps
        self.generators         = {g.name: g for g in self.net.generators}
        self.thermal_generators = {g.name: g for g in self.net.thermal_generators}
        self.wind_generators    = {g.name: g for g in self.net.wind_generators}
        self.bess               = {g.name: g for g in self.net.batteries}
        self.hydro_generators   = {g.name: g for g in self.net.hydro_generators}

        self.buses = {b.name: b for b in self.net.buses}    # Bus maps 
        self.lines = {l.name: l for l in self.net.lines}    # Branch maps
        self.loads = {ld.name: ld for ld in self.net.loads} # Load maps

        self._is_base_built = False

    def _build_base_model(self):
        """
        Constructs the base Pyomo model with sets and parameters.
        """
        if self._is_base_built:
            return
        
        self._create_sets()
        self._is_base_built = True

    def _create_sets(self):
        """
        Defines the sets for the Pyomo model.
        """
        model = self.model

        #Network Sets
        model.BUSES = Set(initialize=self.buses.keys()) 
        model.LINES = Set(initialize=self.lines.keys())        

        # Gen and Load Sets
        model.GENERATORS         = Set(initialize=self.generators.keys())
        model.THERMAL_GENERATORS = Set(initialize=self.thermal_generators.keys(), within=model.GENERATORS)
        model.WIND_GENERATORS    = Set(initialize=self.wind_generators.keys(), within=model.GENERATORS)
        model.HYDRO_GENERATORS   = Set(initialize=self.hydro_generators.keys(), within=model.GENERATORS)
        model.BESS               = Set(initialize=self.bess.keys(), within=model.GENERATORS)
        model.LOADS              = Set(initialize=self.loads.keys())