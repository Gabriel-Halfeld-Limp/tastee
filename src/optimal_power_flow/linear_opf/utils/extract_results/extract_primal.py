from power import Network
import numpy as np

def extract_primal(net: Network) -> dict:
    """
    Extrai os valores das variáveis primais do problema resolvido e os converte
    para unidades físicas (MW, MVA, graus).
    """
    try:
        # Pega a base de potência do sistema (ex: 100 MVA) para a conversão
        power_base = net.sb

        return {
            # As chaves agora refletem as novas unidades
            'geracao_mw': {
                gen.id: gen.p_var.value() * power_base 
                for gen in net.generators
            },
            'corte_carga_mw': {
                load.id: load.p_shed_var.value() * power_base 
                for load in net.loads if hasattr(load, 'p_shed_var')
            },
            'thetas_deg': {
                bus.id: np.rad2deg(bus.theta_var.value()) 
                for bus in net.buses
            },
            'fluxo_mva': { # Fluxo de potência é tipicamente em MVA
                line.id: line.flow_var.value() * power_base 
                for line in net.lines
            }
        }
    except AttributeError as e:
        print(f"[ERRO] Falha ao extrair variáveis primais: {e}")
        return None