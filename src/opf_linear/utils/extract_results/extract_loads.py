from power import Network

def extract_loads(net: Network) -> dict:
    """
    Cria um sumário detalhado com a demanda nominal de cada carga em MW.

    Args:
        net (Network): O objeto da rede.

    Returns:
        dict: Um dicionário contendo as cargas individuais do sistema em MW.
    """
    try:
        power_base = net.sb

        # A chave principal 'cargas_individuais_mw' já descreve o conteúdo
        return {
            'cargas_individuais_mw': {
                load.id: load.p_pu * power_base
                for load in net.loads
            }
        }
        
    except Exception as e:
        print(f"[ERRO] Falha ao criar o sumário de cargas detalhado: {e}")
        return None