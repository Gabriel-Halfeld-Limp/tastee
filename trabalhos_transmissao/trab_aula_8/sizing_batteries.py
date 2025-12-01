
from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from power.systems import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch
from power import Network,  Battery
import numpy as np
from copy import deepcopy

b6 = B6L8Charged()
b118 = IEEE118Charged()

# Alocando duas baterias, uma na barra de maior LMP e outra na de menor LMP (definidos em defining_battery_place.py)
bat1_b6 = Battery(id=9999, bus=b6.buses[4], p_max_mw=10, p_min_mw=-10, capacity_mwh=100, soc_mwh=50, cost_charge_mw=-1, cost_discharge_mw=350)
bat2_b6 = Battery(id=10000, bus=b6.buses[0], p_max_mw=10, p_min_mw=-10, capacity_mwh=100, soc_mwh=50, cost_charge_mw=-1, cost_discharge_mw=350)

bat1_b118 = Battery(id=9999, bus=b118.buses[55], p_max_mw=10, p_min_mw=-10, capacity_mwh=100, soc_mwh=50, cost_charge_mw=-1, cost_discharge_mw=350)
bat2_b118 = Battery(id=10000, bus=b118.buses[23], p_max_mw=10, p_min_mw=-10, capacity_mwh=100, soc_mwh=50, cost_charge_mw=-1, cost_discharge_mw=350)

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

nets = [b6, b118]
hours = 24
battery_scaling = np.linspace(0, 1, 10)

# Best results from each network
best_results = {}
for net in nets:
    # Snapshot de parâmetros originais da bateria para escala
    baseline = [{
        'capacity_pu': b.capacity_pu,
        'p_max_pu': b.p_max_pu,
        'p_min_pu': b.p_min_pu
    } for b in net.batteries]

    all_daily_costs = []
    all_hourly_costs = []
    min_daily_cost = float('inf')
    min_hourly_cost = float('inf')
    max_daily_cost = float('-inf')
    max_hourly_cost = float('-inf')
    # Loop from all scales, but backwards:
    for scale_b1 in battery_scaling:
        # Reset bateria 1 para baseline e aplicar escala
        net.batteries[0].capacity_pu = baseline[0]['capacity_pu'] * scale_b1
        net.batteries[0].p_max_pu =     baseline[0]['p_max_pu'] * scale_b1
        net.batteries[0].p_min_pu =     baseline[0]['p_min_pu'] * scale_b1
        for scale_b2 in battery_scaling:
            # Reset bateria 2 para baseline e aplicar escala
            net.batteries[1].capacity_pu = baseline[1]['capacity_pu'] * scale_b2
            net.batteries[1].p_max_pu =     baseline[1]['p_max_pu'] * scale_b2
            net.batteries[1].p_min_pu =     baseline[1]['p_min_pu'] * scale_b2

            # Reset nos RNGs para rodar sempre as mesmas 24 horas pra cada combinaçao de escalas de baterias    
            rng1 = np.random.default_rng(seed=42)
            rng2 = np.random.default_rng(seed=41)
            invest_cost = investiment_cost(net)
            daily_cost = invest_cost
            #Setar o SOC inicial das baterias como 50% da capacidade no início do dia
            for battery in net.batteries:
                battery.soc_pu = 0.5 * battery.capacity_pu
            
            #Loop das 24 horas
            for h in range(hours):
                net_hour = deepcopy(net)
                apply_wnd_scen(net_hour, rng=rng1)
                apply_load_scen(net_hour, rng=rng2)
                solver = LinearDispatch(net_hour)
                results = solver.solve_loss()
                hourly_cost = float(results["FOB_Value"])
                daily_cost += hourly_cost
                all_daily_costs.append(daily_cost)

                # Atualizar o SOC das baterias para a próxima hora
                for i, battery in enumerate(net_hour.batteries):
                    # Usar acesso seguro ao DataFrame por índice e coluna
                    if not results["Battery"].empty and battery.name in results["Battery"].index:
                        p_in = results["Battery"].loc[battery.name, "P_In_MW"] / net.sb_mva
                        p_out = results["Battery"].loc[battery.name, "P_Out_MW"] / net.sb_mva
                        battery.soc_pu += (p_in - p_out)
                    else:
                        pass
                    # Garantir que o SOC não exceda os limites
                    if battery.soc_pu > battery.capacity_pu:
                        raise ValueError("SOC da bateria excedeu a capacidade máxima.")
                    elif battery.soc_pu < 0:
                        raise ValueError("SOC da bateria ficou abaixo de zero.")
                print(f"Scale B1: {scale_b1:.4f}, Scale B2: {scale_b2:.4f} => Custo Operativo Hora {h}: ${hourly_cost:,.2f}")
            all_daily_costs.append(daily_cost)
            print(f"Scale B1: {scale_b1:.4f}, Scale B2: {scale_b2:.4f} => Custo Diário Total: ${daily_cost:,.2f}")
            if daily_cost < min_daily_cost:
                min_daily_cost = daily_cost
                melhor_scale_b1 = scale_b1
                melhor_scale_b2 = scale_b2
    best_results[net.name] = {
        "melhor_scale_b1": melhor_scale_b1,
        "melhor_scale_b2": melhor_scale_b2,
        "min_daily_cost": min_daily_cost
    }
for net in nets:
    print(f"\nResultados para o sistema {net.name}:")
    print(f"\nMelhor configuração encontrada:")
    print(f"Scale Bateria 1 (barra {net.batteries[0].bus.name}): {best_results[net.name]['melhor_scale_b1']:.4f}")
    print(f"Scale Bateria 2 (barra {net.batteries[1].bus.name}): {best_results[net.name]['melhor_scale_b2']:.4f}")
    print(f"Custo Total Mínimo: ${best_results[net.name]['min_daily_cost']:,.2f}")
