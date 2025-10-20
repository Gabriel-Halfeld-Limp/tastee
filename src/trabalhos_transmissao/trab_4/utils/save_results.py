from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import Dict, List

# A função agora recebe o 'output_dir' já pronto.
def save_ctg_results(data_lists: Dict[str, List[dict]], output_dir: Path) -> None:
    """
    Salva um dicionário de listas de dados em arquivos Parquet em um diretório específico.

    Args:
        data_lists (Dict[str, List[dict]]): O dicionário com os dados coletados.
        output_dir (Path): O caminho completo para a pasta onde os arquivos serão salvos.
    """
    print(f"\n{'='*20} SIMULAÇÕES CONCLUÍDAS. SALVANDO RESULTADOS. {'='*20}")
    
    # A criação da pasta agora é responsabilidade de quem chama a função,
    # mas garantimos que ela exista.
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Salvando resultados em: '{output_dir.resolve()}'")

    # O resto da função continua exatamente igual...
    for name, data_list in data_lists.items():
        if data_list:
            try:
                df = pd.DataFrame(data_list)
                if 'contingencia' in df.columns:
                    df['contingencia'] = df['contingencia'].astype(str)
                
                output_path = output_dir / f"{name}.parquet"
                df.to_parquet(output_path, engine='pyarrow')
                
                print(f"-> Tabela '{name}' salva com {len(df)} registros.")
            
            except Exception as e:
                print(f"[ERRO] Falha ao salvar a tabela '{name}': {e}")
                
        else:
            print(f"- Tabela '{name}' estava vazia, não foi salva.")

    print(f"\n✅ Processo finalizado! Seus arquivos Parquet estão prontos para análise em '{output_dir.resolve()}'.")