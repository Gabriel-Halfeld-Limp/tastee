# Projeto de Análise de Sistemas de Transmissão

## Visão Geral do Projeto

Este repositório contém uma série de estudos e análises de sistemas de energia elétrica, com foco em otimização do fluxo de potência, análise de contingências e planejamento da expansão da transmissão. O projeto utiliza uma combinação de programação linear e metaheurísticas para avaliar e otimizar o desempenho de redes elétricas sob diferentes cenários de geração e carga.

## Estrutura do Projeto

O repositório está organizado da seguinte forma:

- **`src/`**: Contém o código-fonte principal do projeto, dividido em:
    - **`metaheuristic/`**: Implementação de algoritmos de metaheurística, como o AOA (Arithmetic Optimization Algorithm).
    - **`optimal_power_flow/`**: Modelos de otimização de fluxo de potência, incluindo o despacho linear com perdas.
    - **`power/`**: Modelos de componentes de sistemas de energia, como barramentos, linhas, geradores e cargas, bem como as definições dos sistemas de teste (B3, B6L8, IEEE118, etc.).
    - **`power_flow/`**: Implementações de algoritmos de fluxo de potência AC e DC.
- **`trabalhos_transmissao/`**: Contém os trabalhos práticos da disciplina de transmissão, incluindo:
    - **`trab_aula_3/`**: Análise de sistemas elétricos (B6L8 e IEEE118) sob múltiplos cenários de geração eólica e de carga.
    - **`trab_aula_6/`**: Avaliação do sistema sem reforço e otimização do planejamento da expansão da transmissão usando metaheurística.
- **`pyproject.toml`**: Arquivo de configuração do projeto, que define as dependências e outros metadados.

## Trabalhos de Transmissão

Esta seção detalha os trabalhos práticos contidos no diretório `trabalhos_transmissao/`.

### `trab_aula_3`: Análise de Cenários

Neste trabalho, foram realizadas simulações em múltiplos cenários para os sistemas B6L8 e IEEE118, ambos com a inclusão de geração eólica. Os notebooks `B6L8_cenarios.ipynb` e `IEEE118_cenarios.ipynb` executam um despacho econômico linear com perdas para 100 cenários diferentes, gerados aleatoriamente, e salvam os resultados em formato JSON.

O objetivo desta análise é avaliar o impacto da variabilidade da geração eólica e da carga no fluxo de potência e nos custos operacionais do sistema.

### `trab_aula_6`: Planejamento da Expansão da Transmissão

Este trabalho aborda o problema do planejamento da expansão da transmissão, dividido em duas partes:

1.  **`avaliar_sem_reforco.py`**: Este script avalia o desempenho do sistema `B3EOLCharged` sem qualquer reforço na rede. Ele calcula o custo operacional, o corte de geração (curtailment) e o déficit de carga para múltiplos cenários, incluindo a análise de contingências N-1. Além disso, extrai os multiplicadores de Lagrange (variáveis duais) associados aos limites de fluxo das linhas, que indicam o nível de congestionamento da rede.

2.  **`main_ctg.py`**: Este script utiliza o algoritmo de otimização metaheurística AOA (Arithmetic Optimization Algorithm) para encontrar o plano de reforço ótimo para as linhas de transmissão do sistema `B3EOL`. A função objetivo a ser minimizada é o custo total, que consiste no custo de investimento (reforço das linhas) somado ao custo operacional médio, considerando múltiplos cenários e contingências. O algoritmo determina a redução ótima de reatância para cada linha candidata, visando minimizar o custo total.

## Como Executar o Projeto

Para clonar e executar este projeto, siga os passos abaixo.

### Pré-requisitos

- [Poetry](https://python-poetry.org/) instalado.

### Instalação

1.  Clone o repositório:

    ```bash
    git clone https://github.com/g-halfeld/tastee.git
    cd tastee
    ```

2.  Instale as dependências usando o Poetry:

    ```bash
    poetry install
    ```

3.  Ative o ambiente virtual do Poetry:

    ```bash
    poetry shell
    ```

### Executando os Trabalhos

Para executar os trabalhos, navegue até o diretório correspondente e execute o script Python ou o notebook Jupyter.

**Exemplo: Executando o `trab_aula_6`**

```bash
cd trabalhos_transmissao/trab_aula_6
python main_ctg.py
```

Para executar os notebooks, você precisará ter o Jupyter Notebook ou o JupyterLab instalado.