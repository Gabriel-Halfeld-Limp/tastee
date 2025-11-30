from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from power.systems import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from power import *

net = Network(sb_mva=100)

b = Bus(net, id=1)

bat = Battery(id=1, bus=b, p_max_mw=10, p_min_mw=-10, capacity_mwh=100, soc_mwh=50, cost_charge_mw=-1, cost_discharge_mw=350)

bat.soc_pu = 80

print(bat.soc_mwh)


