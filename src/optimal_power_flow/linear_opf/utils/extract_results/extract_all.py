from .extract_curtailment import extract_curtailment
from .extract_shedding import extract_shedding
from .extract_summary import extract_summary
from .extract_losses import extract_losses
from .extract_primal import extract_primal
from .extract_loads import extract_loads
from .extract_dual import extract_dual

from power import Network
import numpy as np
import pulp as pl
import json

# --- Classe "Tradutora" para o JSON ---
class NpEncoder(json.JSONEncoder):
    """Lida com os tipos de dados do NumPy para a conversão para JSON."""
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        return super(NpEncoder, self).default(obj)


def extract_all(problem: pl.LpProblem, net: Network, output_filename: str = None) -> dict:
    """
    Orquestra a extração de todos os resultados da simulação chamando funções especialistas.

    Args:
        problem (pl.LpProblem): O objeto do problema PuLP já resolvido.
        net (Network): O objeto da rede contendo o estado da solução.
        output_filename (str, optional): Se fornecido, salva os resultados em um arquivo JSON.

    Returns:
        dict: Um dicionário completo com todos os resultados, ou None se a solução não for ótima.
    """
    # 1. Verificação de Status: Garante que só prosseguimos com uma solução válida.
    if problem.status != pl.LpStatusOptimal:
        print(f"\n[AVISO] A solução não é ótima ({pl.LpStatus[problem.status]}). Nenhum resultado será extraído.")
        return None

    # 2. Delegação: Chama cada função "trabalhadora" para fazer sua parte.
    system_summary = extract_summary(net, problem)
    primal_results = extract_primal(net)
    dual_results = extract_dual(problem, net)
    load_details = extract_loads(net)
    loss_details = extract_losses(net)
    curtailment_details = extract_curtailment(net)
    shedding_details = extract_shedding(net)

    # 3. Validação: Checa se alguma das extrações essenciais falhou.
    essential_results = [system_summary, primal_results, dual_results]
    if any(result is None for result in essential_results):
        print("[ERRO] Falha na extração de resultados essenciais (sumário, primais ou duais). Abortando.")
        return None

    # 4. Montagem: Reúne todos os dicionários retornados em um resultado final.
    final_results = {
        'sumario_geral': system_summary,
        'resultados_primais': primal_results,
        'resultados_duais': dual_results,
        'detalhes_cargas': load_details,
        'detalhes_perdas': loss_details,
        'detalhes_curtailment': curtailment_details,
        'detalhes_corte_carga': shedding_details,
    }
    
    # 5. Exportação Opcional: Salva um JSON para inspeção humana, se solicitado.
    if output_filename:
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(final_results, f, indent=4, ensure_ascii=False, cls=NpEncoder)
            print(f"\n[SUCESSO] Exemplo de resultado salvo em '{output_filename}'")
        except Exception as e:
            print(f"\n[ERRO] Não foi possível salvar o exemplo em JSON: {e}")

    # 6. Retorno: Entrega o dicionário completo para o próximo passo (coleta para o Parquet).
    return final_results