def collect_ctg_results(results: dict, run_keys: dict, data_lists: dict):
    """
    Desmonta um dicionário de resultados de uma única simulação e anexa os dados
    em formato tabular ao dicionário de listas `data_lists`.

    Args:
        results (dict): O dicionário de resultados retornado pelo orquestrador.
        run_keys (dict): As chaves que identificam a simulação (sistema, cenário, etc.).
        data_lists (dict): O dicionário de listas que será preenchido.
    """
    if not results:
        return

    # 1. Sumário Geral (1 linha por simulação)
    data_lists['sumario_geral'].append({**run_keys, **results['sumario_geral']})
    
    # 2. Resultados Primais (Múltiplas linhas por simulação)
    for gen_id, val in results['resultados_primais']['geracao_mw'].items():
        data_lists['geracao'].append({**run_keys, 'gerador_id': gen_id, 'geracao_mw': val})
    for load_id, val in results['resultados_primais']['corte_carga_mw'].items():
        data_lists['corte_carga'].append({**run_keys, 'carga_id': load_id, 'corte_mw': val})
    for line_id, val in results['resultados_primais']['fluxo_mva'].items():
        data_lists['fluxo'].append({**run_keys, 'linha_id': line_id, 'fluxo_mva': val})
    for bus_id, val in results['resultados_primais']['thetas_deg'].items():
        data_lists['angulos'].append({**run_keys, 'barra_id': bus_id, 'theta_deg': val})

    # 3. Resultados Duais (Múltiplas linhas por simulação) - COM AS CHAVES CORRIGIDAS
    for bus_id, val in results['resultados_duais']['preco_marginal_energia'].items():
        data_lists['lmp'].append({**run_keys, 'barra_id': bus_id, 'lmp_dol_mwh': val})
    
    # CORREÇÃO: Nome da chave atualizado
    for line_id, vals in results['resultados_duais']['limites_fluxo'].items():
        data_lists['limites_fluxo'].append({**run_keys, 'linha_id': line_id, **vals})
        
    # CORREÇÃO: Nome da chave atualizado
    for gen_id, vals in results['resultados_duais']['limites_geracao'].items():
        data_lists['limites_geracao'].append({**run_keys, 'gerador_id': gen_id, **vals})
        
    # CORREÇÃO: Nome da chave atualizado
    for load_id, vals in results['resultados_duais']['limites_corte_carga'].items():
        data_lists['limites_corte'].append({**run_keys, 'carga_id': load_id, **vals})
        
    # CORREÇÃO: Nome da chave atualizado
    for bus_id, vals in results['resultados_duais']['limites_theta'].items():
        data_lists['limites_angulo'].append({**run_keys, 'barra_id': bus_id, **vals})

    # 4. Detalhes de Cargas e Perdas
    for load_id, val in results['detalhes_cargas']['cargas_individuais_mw'].items():
        data_lists['cargas_individuais'].append({**run_keys, 'carga_id': load_id, 'carga_mw': val})
    for line_id, val in results['detalhes_perdas']['perdas_por_linha_mw'].items():
        data_lists['perdas_linha'].append({**run_keys, 'linha_id': line_id, 'perda_mw': val})
    for bus_id, val in results['detalhes_perdas']['perdas_por_barra_mw'].items():
        data_lists['perdas_barra'].append({**run_keys, 'barra_id': bus_id, 'perda_mw': val})

    # 5. Detalhes de Curtailment e Corte de Carga
    for gen_id, vals in results['detalhes_curtailment']['curtailment_por_gerador'].items():
        data_lists['curtailment_detalhado'].append({**run_keys, 'gerador_id': gen_id, **vals})
    for load_id, vals in results['detalhes_corte_carga']['corte_por_carga_mw'].items():
        data_lists['corte_carga_detalhado'].append({**run_keys, 'carga_id': load_id, **vals})