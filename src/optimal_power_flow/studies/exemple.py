# Seu script principal

# 1. Instancia e constrói UMA VEZ
estudo = DC_EconomicDispatch(rede)
estudo.init_persistent_solver() # Carrega o HiGHS na memória

resultados = []

# Dados de entrada (Exemplo: DataFrames pandas com 24h)
# df_wind: colunas = nomes das eólicas, linhas = 0 a 23 (fator 0 a 1)
# df_load: colunas = nomes das cargas, linhas = 0 a 23 (valor pu)

for hora in range(24):
    print(f"Simulando hora {hora}...")
    
    # --- PASSO A: ATUALIZAR PARÂMETROS ---
    
    # 1. Atualiza Cargas
    for load_name in estudo.model.loads:
        novo_valor = df_load.loc[hora, load_name]
        estudo.model.load_p[load_name].value = novo_valor # .value é o segredo!

    # 2. Atualiza Vento
    for wind_gen in estudo.model.gens_wind:
        fator_vento = df_wind.loc[hora, wind_gen]
        estudo.model.wind_factor[wind_gen].value = fator_vento

    # --- PASSO B: RESOLVER ---
    # O solver percebeu que load_p e wind_factor mudaram.
    # Ele atualiza só as restrições afetadas (Balanço e Limite Eólico) e resolve.
    estudo.solver.solve(estudo.model)
    
    # --- PASSO C: GUARDAR RESULTADOS ---
    resultados.append({
        'hora': hora,
        'custo': value(estudo.model.obj),
        'geracao_total': sum(value(estudo.model.pg[g]) for g in estudo.model.gens)
    })