from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from power.systems import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from power import *
from power.systems import *

# net = B6L8Charged()

# for i, wind_generator in enumerate(net.wind_generators):
#     Battery(id=i+200, bus=wind_generator.bus, p_max_mw=200, p_min_mw=-200, capacity_mwh=400, soc_mwh=200, cost_charge_mw=-1, cost_discharge_mw=350)

# for i, bus in enumerate(net.buses):
#     Battery(id=i+300, bus=bus, p_max_mw=100, p_min_mw=-100, capacity_mwh=200, soc_mwh=100, cost_charge_mw=-1, cost_discharge_mw=399)


# solver = LinearDispatch(net=net)
# results = solver.solve_loss(verbose=True, detailed_output=True)
# print(results["Battery"])



# net = Network(sb_mva=100)
# bus1 = Bus(net, id=1, name="Bus 1")
# bus2 = Bus(net, id=2, name="Bus 2")
# l1 = Line(id=1, from_bus=bus1, to_bus=bus2, x_pu=0.1, flow_max_pu=90)
# Battery(id=1, bus=bus1, p_max_mw=90, p_min_mw=-80, capacity_mwh=100, soc_mwh=100, cost_charge_mw=0, cost_discharge_mw=399)
# Load(id=1, bus=bus2, p_mw=80, cost_shed_mw=400)

# solver = LinearDispatch(net=net)
# results = solver.solve_loss(verbose=True, detailed_output=True)
# print(results["Battery"])

# Sistema Bateria e Eolico
net = Network(sb_mva=100)
bus1 = Bus(net, id=1, name="Bus 1")
bus2 = Bus(net, id=2, name="Bus 2")
line = Line(id=1, from_bus=bus1, to_bus=bus2, x_pu=0.1, flow_max_pu=1)
wnd = WindGenerator(id=1, bus=bus2, p_max_mw=81)
# load = Load(id=1, bus=bus2, p_mw=80, cost_shed_mw=400)
bat = Battery(id=1, bus=bus2, p_max_mw=90, p_min_mw=-100, capacity_mwh=100, soc_mwh=0, cost_charge_mw=-10, cost_discharge_mw=399)
solver = LinearDispatch(net=net)
results = solver.solve_loss(verbose=True, detailed_output=True)
print(results["Battery"])
