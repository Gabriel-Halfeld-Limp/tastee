from power import Network
import pulp as pl

def extract_summary(net: Network, problem: pl.LpProblem) -> dict:
    """
    Cria um sumário de alto nível com os totais do sistema em MW.
    Inclui o status do solver e o valor final da função objetivo.
    """
    try:
        # 1. Pega a base de potência do sistema (ex: 100 MVA)
        power_base = net.sb

        # 2. Calcula todos os totais em p.u. primeiro
        total_generation_pu = sum(g.p_var.value() for g in net.generators)
        total_load_pu = sum(l.p for l in net.loads)
        total_loss_pu = sum(b.loss for b in net.buses if hasattr(b, "loss"))
        total_shedding_pu = sum(l.p_shed_var.value() for l in net.loads if hasattr(l, 'p_shed_var'))

        # 3. Faz a verificação do balanço ainda em p.u.
        balance_check_pu = (total_generation_pu + total_shedding_pu) - (total_load_pu + total_loss_pu)

        # 4. Monta o dicionário final, convertendo cada total para MW
        overview_summary = {
            # Informações do Solver
            "status_solucao": pl.LpStatus[problem.status],
            "funcao_objetivo_total": problem.objective.value(),

            # Valores de Potência convertidos para MW
            "geracao_total_mw": total_generation_pu * power_base,
            "carga_total_mw": total_load_pu * power_base,
            "perdas_totais_mw": total_loss_pu * power_base,
            "corte_total_mw": total_shedding_pu * power_base,
            
            # Verificação do balanço, também convertida para MW
            "balanco_potencia_residual_mw": balance_check_pu * power_base
        }
        
        return overview_summary

    except Exception as e:
        print(f"[ERRO] Falha ao criar o sumário de overview: {e}")
        return None