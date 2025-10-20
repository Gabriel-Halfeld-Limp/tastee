from power import Network

def extract_losses(net: Network) -> dict:
    """
    Cria um sumário detalhado das perdas do sistema em MEGAWATTS (MW).

    Extrai o total de perdas, as perdas individuais por linha e a alocação
    de perdas por barra.

    Args:
        net (Network): O objeto da rede já resolvido.

    Returns:
        dict: Um dicionário contendo os detalhes das perdas em MW.
    """
    try:
        # 1. Pega a base de potência do sistema (ex: 100 MVA) para a conversão.
        power_base = net.sb

        # 2. Calcula o total de perdas a partir da soma das perdas das linhas.
        #    Isso evita contar em dobro, já que as perdas das barras são a soma de metades das perdas das linhas.
        total_loss_pu = sum(l.loss for l in net.lines if hasattr(l, 'loss'))

        # 3. Monta o dicionário de retorno, convertendo todos os valores para MW.
        loss_summary = {
            # O total de perdas do sistema
            "perdas_totais_mw": total_loss_pu * power_base,
            
            # O detalhamento de perdas em cada linha
            "perdas_por_linha_mw": {
                l.id: l.loss * power_base
                for l in net.lines if hasattr(l, 'loss') and l.loss > 1e-9 # Filtra valores insignificantes
            },
            
            # O detalhamento da alocação de perdas em cada barra
            "perdas_por_barra_mw": {
                b.id: b.loss * power_base
                for b in net.buses if hasattr(b, 'loss') and b.loss > 1e-9 # Filtra valores insignificantes
            }
        }
        
        return loss_summary
        
    except Exception as e:
        print(f"[ERRO] Falha ao criar o sumário de perdas detalhado: {e}")
        return None