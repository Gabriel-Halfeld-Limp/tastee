from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from power.systems import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from power import Network, Bus, Load, Battery
import numpy as np


b6 = B6L8Charged()
solver = LinearDispatch(b6)
results = solver.solve_loss()
bus_df = results["Bus"]  # DataFrame com índice = nome da barra
lmp_series = bus_df["Local_Marginal_Price"]

# Nome (string) da barra com maior e menor LMP
bus_name_max = lmp_series.idxmax()
bus_name_min = lmp_series.idxmin()

# Valores de LMP
lmp_max = lmp_series.loc[bus_name_max]
lmp_min = lmp_series.loc[bus_name_min]

# Criar dicionário nome -> id
name_to_id = {b.name: b.id for b in b6.buses}

b6_id_max = name_to_id[bus_name_max]
b6_id_min = name_to_id[bus_name_min]

print(f"Maior LMP: barra {bus_name_max} (id={b6_id_max}) = {lmp_max:.4f}")
print(f"Menor LMP: barra {bus_name_min} (id={b6_id_min}) = {lmp_min:.4f}")


b118 = IEEE118Charged()
solver = LinearDispatch(b118)
results = solver.solve_loss()

# Nome (string) da barra com maior e menor LMP
bus_name_max = lmp_series.idxmax()
bus_name_min = lmp_series.idxmin()

# Valores de LMP
lmp_max = lmp_series.loc[bus_name_max]
lmp_min = lmp_series.loc[bus_name_min]

# Criar dicionário nome -> id
name_to_id = {b.name: b.id for b in b118.buses}

b118_id_max = name_to_id[bus_name_max]
b118_id_min = name_to_id[bus_name_min]

print(f"Maior LMP: barra {bus_name_max} (id={b118_id_max}) = {lmp_max:.4f}")
print(f"Menor LMP: barra {bus_name_min} (id={b118_id_min}) = {lmp_min:.4f}")

# Alocando duas baterias, uma na barra de maior LMP e outra na de menor LMP
bat1_b6 = Battery(id=9999, bus=b6.buses[b6_id_max-1], p_max_mw=10000, p_min_mw=-10000, capacity_mwh=100000)
bat2_b6 = Battery(id=10000, bus=b6.buses[b6_id_min-1], p_max_mw=10000, p_min_mw=-10000, capacity_mwh=100000)

bat1_b118 = Battery(id=9999, bus=b118.buses[b118_id_max-1], p_max_mw=10000, p_min_mw=-10000, capacity_mwh=100000)
bat2_b118 = Battery(id=10000, bus=b118.buses[b118_id_min-1], p_max_mw=10000, p_min_mw=-10000, capacity_mwh=100000)

# Function to scale a battery
def scale_battery(battery: Battery, scale_factor: float):
    battery.capacity_mwh *= scale_factor
    battery.p_max_mw *= scale_factor
    battery.p_min_mw *= scale_factor

def investiment_cost(net: Network):
    total_cost = 0
    for battery in net.batteries:
        # Assuming cost is $400 per kWh of capacity
        total_cost += battery.capacity_mwh * 5
    return total_cost

net = b6
hours = 24
battery_scaling = np.linspace(0, 1, 10)

# Loop from all scales, but backwards:
total_costs = []
for scale_b1 in battery_scaling[::-1]:
    scale_battery(net.batteries[0], scale_b1)
    for scale_b2 in battery_scaling[::-1]:
        scale_battery(net.batteries[1], scale_b2)
        for h in range(hours):
            apply_wnd_scen(net, rng=np.random.default_rng(seed=42))
            apply_load_scen(net, rng=np.random.default_rng(seed=41))
            solver = LinearDispatch(net)
            results = solver.solve_loss()
            operational_cost = float(results["FOB_Value"])
            invest_cost = investiment_cost(net)
            total_cost = operational_cost + invest_cost
            print(f"Scale B1: {scale_b1:.4f}, Scale B2: {scale_b2:.4f} => Total Cost: ${total_cost:,.2f}")
            total_costs.append((scale_b1, scale_b2, total_cost))