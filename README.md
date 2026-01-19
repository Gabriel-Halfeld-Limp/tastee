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
