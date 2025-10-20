from power import Network, WindGenerator

def extract_curtailment(net: Network) -> dict:
    """
    Cria um sumário detalhado do curtailment dos geradores eólicos em MEGAWATTS (MW).

    Calcula a energia eólica disponível, a despachada e a diferença (curtailment)
    para cada gerador eólico, além do total do sistema, tudo em MW.

    Args:
        net (Network): O objeto da rede já resolvido.

    Returns:
        dict: Um dicionário contendo o curtailment total e os detalhes por gerador em MW.
    """
    try:
        # 1. Pega a base de potência do sistema (ex: 100 MVA) para a conversão.
        power_base = net.sb

        # 2. Filtra a lista para pegar apenas os geradores eólicos que tiveram curtailment.
        #    A lógica de comparação continua em p.u., pois é mais estável.
        curtailed_gens = [
            g for g in net.generators 
            if isinstance(g, WindGenerator) and (g.p_max - g.p_var.value()) > 1e-6
        ]

        # 3. Calcula o total de curtailment em p.u. primeiro.
        total_curtailment_pu = sum(g.p_max - g.p_var.value() for g in curtailed_gens)
        
        # 4. Monta o dicionário de retorno, convertendo todos os valores para MW.
        curtailment_summary = {
            "curtailment_total_mw": total_curtailment_pu * power_base,
            "curtailment_por_gerador": {
                g.id: {
                    # As chaves agora refletem a nova unidade (MW)
                    "disponivel_mw": g.p_max * power_base,
                    "despachado_mw": g.p_var.value() * power_base,
                    "curtailment_mw": (g.p_max - g.p_var.value()) * power_base
                }
                for g in curtailed_gens
            }
        }
        
        return curtailment_summary
        
    except Exception as e:
        print(f"[ERRO] Falha ao criar o sumário de curtailment: {e}")
        return None