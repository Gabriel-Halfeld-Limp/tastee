# --- Bibliotecas Padrão do Python ---
import copy
from datetime import datetime
from pathlib import Path

# --- Bibliotecas de Terceiros ---
import numpy as np
import pandas as pd
import pulp as pl

# --- Importações da Aplicação Local (CORRIGIDAS) ---

# Imports absolutos a partir da raiz 'src'
from power import Network, Bus, Line, Load, ThermalGenerator, WindGenerator
from power.systems import B3EOL, IEEE118EOL, B6L8EOL
from opf_linear.opf_loss import LinearDispatch
from opf_linear.utils.extract_results.extract_all import extract_all
from trabalhos_transmissao.utils.wnd_scen import apply_wnd_scen
from trabalhos_transmissao.utils.load_scen import apply_load_scen
from trabalhos_transmissao.trab_4.utils.collect_results import collect_ctg_results
from trabalhos_transmissao.trab_4.utils.save_results import save_ctg_results

nets = [B6L8EOL(), IEEE118EOL(), B3EOL()]
# nets = [B6L8EOL()]
# nets = [IEEE118EOL()]
# nets = [B3()]
# nets = [B3EOL()]
seed = 42
rng = np.random.default_rng(seed=seed)
nscen = 10


data_lists = {
    "sumario_geral": [],
    #Primais
    "geracao": [],
    "corte_carga": [],
    "fluxo": [],
    "angulos": [],
    #Duais
    "lmp": [],
    "limites_fluxo": [],
    "limites_geracao": [],
    "limites_corte": [],
    "limites_angulo": [],
    #Detalhes
    "cargas_individuais": [],
    "perdas_linha": [],
    "perdas_barra": [],
    "curtailment_detalhado": [],
    "corte_carga_detalhado": [],
}


for net in nets:
    print(f"\n{'='*20} INICIANDO SIMULAÇÃO PARA O SISTEMA: {net.name} {'='*20}")
    for scen in range(nscen):
        print(f"\n--- Processando Cenário {scen} ---")
        net_scen = copy.deepcopy(net)
        apply_wnd_scen(net=net_scen, rng=rng)
        apply_load_scen(net=net_scen, rng=rng)

        # --- a) Caso Base ---
        print(f"  Resolvendo Caso Base...")
        solver_base = LinearDispatch(net_scen)
        status_base, _, _ = solver_base.solve_loss()

        if status_base == 'Optimal':
            results = extract_all(solver_base.problem, solver_base.net)
            run_keys = {'sistema': net.name, 'cenario': scen, 'contingencia': 'BASE_CASE'}
            # UMA ÚNICA CHAMADA PARA COLETAR TODOS OS DADOS
            collect_ctg_results(results, run_keys, data_lists)
        else:
            print(f"  AVISO: Caso Base para o cenário {scen} não convergiu.")
            continue

        # --- b) Contingências (N-1) ---
        for line in net.lines: 
            print(f"    - Simulando contingência da linha: {line.id}")
            ctg_net = copy.deepcopy(net_scen)
            line_to_remove = next((l for l in ctg_net.lines if l.id == line.id), None)
            if line_to_remove: ctg_net.lines.remove(line_to_remove)
            
            solver_ctg = LinearDispatch(ctg_net)
            status_ctg, _, _ = solver_ctg.solve_loss()

            if status_ctg == 'Optimal':
                results_ctg = extract_all(solver_ctg.problem, ctg_net)
                run_keys_ctg = {'sistema': net.name, 'cenario': scen, 'contingencia': line.id}
                # UMA ÚNICA CHAMADA PARA COLETAR TODOS OS DADOS
                collect_ctg_results(results_ctg, run_keys_ctg, data_lists)

# =============================================================================
# FASE 3: FINALIZAÇÃO (Salvamento dos Resultados)
# =============================================================================
# Chama a função de salvamento que você criou, passando a "colheita" de dados.
script_dir = Path(__file__).parent
base_output_dir = script_dir / "results_parquet"
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
final_output_dir = base_output_dir / timestamp
save_ctg_results(data_lists, output_dir=final_output_dir)