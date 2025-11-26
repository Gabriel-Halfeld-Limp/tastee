from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from power.systems import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch

solver = LinearDispatch(IEEE118EOL())

results = solver.solve_min_loss(verbose=True)