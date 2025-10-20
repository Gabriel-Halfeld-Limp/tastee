from power import Network

def extract_shedding(net: Network) -> dict:
    """
    Cria um sumário detalhado do corte de carga do sistema em MEGAWATTS (MW).

    Calcula o total de carga cortada e, para cada carga afetada, detalha a
    demanda nominal, o valor cortado e a demanda efetivamente atendida.

    Args:
        net (Network): O objeto da rede já com os resultados da otimização.

    Returns:
        dict: Um dicionário contendo os detalhes de corte de carga em MW.
    """
    try:
        # 1. Pega a base de potência do sistema (ex: 100 MVA) para a conversão.
        power_base = net.sb

        # 2. Filtra a lista para pegar apenas as cargas que tiveram um corte significativo.
        #    Isso evita poluir o resultado com valores muito pequenos (ruído numérico).
        shed_loads = [
            l for l in net.loads 
            if hasattr(l, 'p_shed_var') and l.p_shed_var.value() > 1e-6
        ]

        # 3. Calcula o total de corte de carga em p.u. a partir da lista filtrada.
        total_shedding_pu = sum(l.p_shed_var.value() for l in shed_loads)
        
        # 4. Monta o dicionário de retorno, convertendo todos os valores para MW.
        shedding_summary = {
            "corte_total_mw": total_shedding_pu * power_base,
            "corte_por_carga_mw": {
                l.id: {
                    # As chaves agora refletem a unidade (MW)
                    "demanda_nominal_mw": l.p * power_base,
                    "carga_cortada_mw": l.p_shed_var.value() * power_base,
                    "carga_atendida_mw": (l.p - l.p_shed_var.value()) * power_base
                }
                for l in shed_loads
            }
        }
        
        return shedding_summary
        
    except Exception as e:
        print(f"[ERRO] Falha ao criar o sumário de corte de carga: {e}")
        return None