# Análise dos sistemas B6L8 e IEEE-118

Este repositório contém um pequeno framework em Python para modelagem de redes de potência (barras, linhas, geradores, cargas), solução de despacho econômico linear (OPF linear) com inclusão iterativa de perdas, geração de cenários (eólica e demanda) e ferramentas para extrair resultados (primal e dual) em formato JSON.

Objetivo do trabalho

Fazer uma análise comparativa e estatística dos sistemas B6L8 e IEEE-118 considerando cenários de geração eólica e de demanda. Em particular, produzir as respostas e dados que permitam responder a três perguntas centrais:

1. Qual o valor médio do corte de carga e do curtailment (energia não aproveitada) nos cenários?
2. Qual a linha de transmissão (LT) que mais influenciou o acréscimo no custo total (FOB), avaliada pelo lagrange médio (dual médio das restrições de fluxo)?
3. Avaliar MVu e MVd de cada gerador (valor marginal para subida/descida, a partir dos duais das restrições de limite de geração).

Ferramentas incluidas

- `src/power/` — modelos de rede: `Network`, `Bus`, `Line`, `Generator`, `WindGenerator`, `Load` e classes que instanciam sistemas (`b6l8.py`, `b6l8_eolic.py`, `ieee118.py`, `ieee118_eolic.py`).
- `src/opf_linear/opf_loss.py` — formulador e resolvedor de despacho econômico linear com inclusão iterativa de perdas (usa PuLP).
- `src/opf_linear/utils/extr_and_save.py` — utilitário que extrai primais e duais do problema resolvido e salva um JSON estruturado (contém resumo de perdas, curtailment por gerador, fluxo, e duais relevantes).
- Notebooks: `B6L8_cenarios.ipynb`, `IEEE118_cenarios.ipynb` — exemplos de uso e geração de cenários.

Formato de saída relevante

O utilitário `extract_and_save_results` gera JSON com seções que são úteis para as três perguntas acima:

- `sumario_curtailment` — inclui `curtailment_total_pu` e `curtailment_por_gerador` (para detectar curtailment eólico).
- `sumario_perdas` — contém `perdas_totais_pu` e `perdas_por_barra_pu` (para calcular corte de carga e perdas).
- `dual_results['congestionamento_de_fluxo']` — duais por linha (`limite_superior` e `limite_inferior`) que permitem obter o lagrange médio por linha.
- `dual_results['limites_de_geracao']` — duais por gerador (`limite_superior`, `limite_inferior`) para calcular MVu (dual do limite superior) e MVd (dual do limite inferior).

Como rodar (PowerShell — Windows)

Recomendação: use o ambiente criado pelo Poetry. Execute os notebooks a partir da raiz do repositório e exporte os resultados para JSON usando as funções já fornecidas.

1) Instalar dependências e entrar no shell do Poetry:

```powershell
poetry install
poetry env activate
```

3) Rodar os notebooks

- Abra `B6L8_cenarios.ipynb` e `IEEE118_cenarios.ipynb`. Eles contêm células que geram cenários (eólica e demanda), chamam `LinearDispatch.solve_loss()` e usam `extract_and_save_results()` para salvar por-cenário JSONs em `results_b6l8/` ou `results_ieee118/`.
```

Como calcular as métricas pedidas a partir dos JSONs salvos

1) Corte de carga (load shedding) e curtailment médio

- Para cada cenário, `extract_and_save_results` inclui somatórios de carga e perdas, além do `curtailment_por_gerador` para geradores eólicos. O corte de carga implementado no modelo aparece como geradores de déficit (custos altos) — some a potência despachada desses geradores para obter o corte por cenário.
- Média dos cenários: faça a média aritmética do `curtailment_total_pu` (e do corte de carga em MW convertendo por `sb`) sobre todos os cenários.

2) LT que mais influenciou o acréscimo na FOB — lagrange médio

- Para cada cenário, os duais das restrições de fluxo por linha estão em `dual_results['congestionamento_de_fluxo'][line_id]` (limite_superior / limite_inferior). Use o valor absoluto ou o sinal conforme sua interpretação (tipicamente toma-se o valor da multiplicador associado ao limite que estiver ativo).
- Calcule a média desses duais por linha ao longo de todos os cenários. A linha com maior valor médio em módulo é a que mais influenciou o aumento do custo.


Pipeline sugerida para reproduzir a análise completa

1. Gerar N cenários (por exemplo, N=100) de vento e demanda; os notebooks de cenários fazem isso e salvam resultados.
2. Para cada cenário, rodar `LinearDispatch.solve_loss()` para obter solution primal/dual e salvar o JSON com `extract_and_save_results`.
3. Rodar uma rotina de pós-processamento (script ou notebook) que consume a pasta `results_b6l8/` e `results_ieee118/` e calcula:
	 - Média e total de curtailment e corte de carga (MW e %), por cenário e agregadas.
	 - Médias dos duais de linha → identificar a linha com maior influência.
	 - Médias e distribuições de MVu / MVd por gerador.

