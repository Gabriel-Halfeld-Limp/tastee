# --- Imports necessários (mantidos como absolutos, para robustez) ---
import copy
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd
import pulp as pl
from power import Network, ThermalGenerator, WindGenerator # Classes de Geradores
from power.systems import B3EOL, IEEE118EOL, B6L8EOL
from opf_linear.opf_loss import LinearDispatch
from opf_linear.utils.extract_results.extract_all import extract_all # Orquestrador
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.trab_aula_4.utils.collect_results import collect_ctg_results
from trabalhos_transmissao.trab_aula_4.utils.save_results import save_ctg_results


nets = [B6L8EOL(), IEEE118EOL(), B3EOL()]
seed = 42
rng = np.random.default_rng(seed=seed)
nscen = 100

# Dicionário de listas para coletar resultados (sem as colunas CTG no loop interno)
data_lists = {
    "sumario_geral": [], "geracao": [], "corte_carga": [], "fluxo": [], "angulos": [],
    "lmp": [], "limites_fluxo": [], "limites_geracao": [], "limites_corte": [],
    "limites_angulo": [], "cargas_individuais": [], "perdas_linha": [],
    "perdas_barra": [], "curtailment_detalhado": [], "corte_carga_detalhado": [],
}

# =============================================================================
# FASE 2: EXECUÇÃO DA SIMULAÇÃO CRONOLÓGICA (RAMPA)
# =============================================================================
for net in nets:
    print(f"\n{'='*20} INICIANDO SIMULAÇÃO CRONOLÓGICA PARA: {net.name} {'='*20}")
    
    # CRITICAL: Armazenar os limites originais e o despacho anterior
    limites_originais = {g.id: (g.p_min_pu, g.p_max_pu) for g in net.generators}
    prev_dispatch = None # Memória da potência despachada no cenário anterior

    for scen in range(nscen):
        print(f"\n--- Processando Cenário {scen} ---")
        
        # 1. PREPARAÇÃO DA REDE
        net_scen = copy.deepcopy(net)
        apply_wnd_scen(net=net_scen, rng=rng)
        apply_load_scen(net=net_scen, rng=rng)

        # 2. APLICAÇÃO DA RESTRIÇÃO DE RAMPA CRONOLÓGICA
        if prev_dispatch:
            print("  Aplicando limites de rampa cronológicos...")
            for g in net_scen.generators:
                # Filtrar para geradores TÉRMICOS, que são os únicos com rampas físicas
                if not isinstance(g, ThermalGenerator):
                    continue
                
                p_anterior = prev_dispatch.get(g.id)
                
                if p_anterior is not None:
                    p_min_fisico, p_max_fisico = limites_originais[g.id]
                    
                    # CÁLCULO DA RESTRIÇÃO: min(P_físico, P_anterior + MVu)
                    novo_p_max = min(p_max_fisico, p_anterior + g.mvu)
                    novo_p_min = max(p_min_fisico, p_anterior - g.mvd)
                    
                    g.p_max_pu = novo_p_max
                    g.p_min_pu = novo_p_min

        # 3. RESOLUÇÃO
        solver = LinearDispatch(net_scen)
        status, _, _ = solver.solve_loss()

        # 4. COLETA DE DADOS
        if status == 'Optimal':
            results = extract_all(solver.problem, solver.net)
            
            # Aqui, a contingência é sempre o ID do cenário (para fins de ordenação)
            run_keys = {'sistema': net.name, 'cenario': scen, 'contingencia': scen} 
            collect_ctg_results(results, run_keys, data_lists)
            
            # CRUCIAL: Atualiza a memória para o PRÓXIMO cenário (i+1)
            prev_dispatch = {g.id: g.p_var.value() for g in net_scen.generators}
        else:
            print(f"  ERROR: NO OPTIMAL SOLUTION FOR SCENARIO {scen}. Quebrando a cadeia cronológica.")
            prev_dispatch = None # Quebra a cadeia para o próximo cenário
            continue

# =============================================================================
# FASE 3: FINALIZAÇÃO (Salvamento dos Resultados)
# =============================================================================
script_dir = Path(__file__).parent
base_output_dir = script_dir / "results_ramping" # SALVA EM UMA PASTA NOVA
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
final_output_dir = base_output_dir / timestamp

# A função de salvamento é chamada com os dados coletados
save_ctg_results(data_lists, output_dir=final_output_dir)