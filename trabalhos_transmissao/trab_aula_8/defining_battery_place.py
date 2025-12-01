from power.systems import *
from optimal_power_flow.linear_opf.opf_loss import LinearDispatch


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

# Recalcular série de LMP para a rede IEEE118 (não reutilizar da B6)
bus_df_118 = results["Bus"]
lmp_series_118 = bus_df_118["Local_Marginal_Price"]
bus_name_max = lmp_series_118.idxmax()
bus_name_min = lmp_series_118.idxmin()

# Valores de LMP
lmp_max = lmp_series_118.loc[bus_name_max]
lmp_min = lmp_series_118.loc[bus_name_min]

# Criar dicionário nome -> id
name_to_id = {b.name: b.id for b in b118.buses}

b118_id_max = name_to_id[bus_name_max]
b118_id_min = name_to_id[bus_name_min]

print(f"Maior LMP: barra {bus_name_max} (id={b118_id_max}) = {lmp_max:.4f}")
print(f"Menor LMP: barra {bus_name_min} (id={b118_id_min}) = {lmp_min:.4f}")
