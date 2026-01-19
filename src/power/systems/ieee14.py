from power.electricity_models import Bus, BusType, Line, ThermalGenerator, Load, Network

class IEEE14(Network):
    """
    Class to represent the IEEE 14 bus system.
    """
    def __init__(self):
        super().__init__(name="IEEE 14 Bus System")
        self.sb_mva = 100.0
        self._create_buses()
        self._create_lines()
        self._create_generators()
        self._create_loads()

    def _create_buses(self):                                    
        Bus(self, id= 1, btype=   BusType.SLACK, v_pu=1.060, theta_deg=0.0)
        Bus(self, id= 2, btype=   BusType.PV,    v_pu=1.045, theta_deg=0.0)
        Bus(self, id= 3, btype=   BusType.PV,    v_pu=1.010, theta_deg=0.0)
        Bus(self, id= 4, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0)
        Bus(self, id= 5, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0)
        Bus(self, id= 6, btype=   BusType.PV,    v_pu=1.070, theta_deg=0.0)
        Bus(self, id= 7, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0)
        Bus(self, id= 8, btype=   BusType.PV,    v_pu=1.090, theta_deg=0.0)
        Bus(self, id= 9, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0, q_shunt_mvar=19) 
        Bus(self, id=10, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0)
        Bus(self, id=11, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0)
        Bus(self, id=12, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0)
        Bus(self, id=13, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0) 
        Bus(self, id=14, btype=   BusType.PQ,    v_pu=1.000, theta_deg=0.0) 


    def _create_lines(self):                                                                                             
        Line(id= 1, from_bus=self.buses[ 0], to_bus=self.buses[ 1], r_pu=0.01938, x_pu=0.05917, shunt_half_pu=0.0264)                 
        Line(id= 2, from_bus=self.buses[ 0], to_bus=self.buses[ 4], r_pu=0.05403, x_pu=0.22304, shunt_half_pu=0.0246)                 
        Line(id= 3, from_bus=self.buses[ 1], to_bus=self.buses[ 2], r_pu=0.04699, x_pu=0.19797, shunt_half_pu=0.0219)                 
        Line(id= 4, from_bus=self.buses[ 1], to_bus=self.buses[ 3], r_pu=0.05811, x_pu=0.17632, shunt_half_pu=0.0187)                 
        Line(id= 5, from_bus=self.buses[ 1], to_bus=self.buses[ 4], r_pu=0.05695, x_pu=0.17388, shunt_half_pu=0.0170)                 
        Line(id= 6, from_bus=self.buses[ 2], to_bus=self.buses[ 3], r_pu=0.06701, x_pu=0.17103, shunt_half_pu=0.0173)                 
        Line(id= 7, from_bus=self.buses[ 3], to_bus=self.buses[ 4], r_pu=0.01335, x_pu=0.04211, shunt_half_pu=0.0064)                 
        Line(id= 8, from_bus=self.buses[ 3], to_bus=self.buses[ 6], r_pu=0.0    , x_pu=0.20912, shunt_half_pu=0.0    ,tap_ratio=0.978)
        Line(id= 9, from_bus=self.buses[ 3], to_bus=self.buses[ 8], r_pu=0.0    , x_pu=0.55618, shunt_half_pu=0.0    ,tap_ratio=0.969)
        Line(id=10, from_bus=self.buses[ 4], to_bus=self.buses[ 5], r_pu=0.0    , x_pu=0.25202, shunt_half_pu=0.0    ,tap_ratio=0.932)
        Line(id=11, from_bus=self.buses[ 5], to_bus=self.buses[10], r_pu=0.09498, x_pu=0.19890, shunt_half_pu=0.0)                    
        Line(id=12, from_bus=self.buses[ 5], to_bus=self.buses[11], r_pu=0.12291, x_pu=0.25581, shunt_half_pu=0.0)                    
        Line(id=13, from_bus=self.buses[ 5], to_bus=self.buses[12], r_pu=0.06615, x_pu=0.13027, shunt_half_pu=0.0)                    
        Line(id=14, from_bus=self.buses[ 6], to_bus=self.buses[ 7], r_pu=0.0    , x_pu=0.17615, shunt_half_pu=0.0)                   
        Line(id=15, from_bus=self.buses[ 6], to_bus=self.buses[ 8], r_pu=0.0    , x_pu=0.11001, shunt_half_pu=0.0)                   
        Line(id=16, from_bus=self.buses[ 8], to_bus=self.buses[ 9], r_pu=0.03181, x_pu=0.08450, shunt_half_pu=0.0)                   
        Line(id=17, from_bus=self.buses[ 8], to_bus=self.buses[13], r_pu=0.12711, x_pu=0.27038, shunt_half_pu=0.0)                   
        Line(id=18, from_bus=self.buses[ 9], to_bus=self.buses[10], r_pu=0.08205, x_pu=0.19207, shunt_half_pu=0.0)                    
        Line(id=19, from_bus=self.buses[11], to_bus=self.buses[12], r_pu=0.22092, x_pu=0.19988, shunt_half_pu=0.0)                    
        Line(id=20, from_bus=self.buses[12], to_bus=self.buses[13], r_pu=0.17093, x_pu=0.34802, shunt_half_pu=0.0)                    

    def _create_generators(self):                                                
        ThermalGenerator(id=1, bus=self.buses[0], p_mw=232.39)                           
        ThermalGenerator(id=2, bus=self.buses[1], p_mw=40.00)     
        ThermalGenerator(id=3, bus=self.buses[2])                           
        ThermalGenerator(id=4, bus=self.buses[4])                            
        ThermalGenerator(id=5, bus=self.buses[5])                            
        ThermalGenerator(id=6, bus=self.buses[7]) 

    def _create_loads(self):                            
        Load(id= 1, bus=self.buses[ 1], p_mw=21.70, q_mvar=12.70)
        Load(id= 2, bus=self.buses[ 2], p_mw=94.20, q_mvar=19.00)
        Load(id= 3, bus=self.buses[ 3], p_mw=47.80, q_mvar=-3.90)
        Load(id= 4, bus=self.buses[ 4], p_mw= 7.60, q_mvar= 1.60)
        Load(id= 5, bus=self.buses[ 5], p_mw=11.20, q_mvar= 7.50)
        Load(id= 6, bus=self.buses[ 8], p_mw=29.50, q_mvar=16.60)
        Load(id= 7, bus=self.buses[ 9], p_mw= 9.00, q_mvar= 5.80)
        Load(id= 8, bus=self.buses[10], p_mw= 3.50, q_mvar= 1.80)
        Load(id= 9, bus=self.buses[11], p_mw= 6.10, q_mvar= 1.60)
        Load(id=10, bus=self.buses[12], p_mw=13.50, q_mvar= 5.80)
        Load(id=11, bus=self.buses[13], p_mw=14.90, q_mvar= 5.00)




