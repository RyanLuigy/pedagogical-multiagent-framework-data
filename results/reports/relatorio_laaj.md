# Relatório LAAJ Consolidado

Gerado em: 2026-08-01T16:37:15.619092

## Escore global ponderado (Passo A) por artefato/juiz

| Artefato | deepseek-r1:14b | qwen2.5:14b |
|---|---|---|
| banco_de_dados:ferramenta | 3.6 | 3.2 |
| banco_de_dados:humano | 4.8 | 4.0 |
| desenvolvimento_full_cycle:ferramenta | 4.8 | 4.0 |
| desenvolvimento_full_cycle:humano | 3.6 | 3.8 |
| estatistica_data_science:ferramenta | 3.8 | 4.0 |
| estatistica_data_science:humano | 4.0 | 4.0 |
| estatistica_geral:ferramenta | 3.6 | 3.4 |
| estatistica_geral:humano | 4.2 | 4.0 |
| ferramentas_propriedade_industrial:ferramenta | 3.6 | 3.6 |
| ferramentas_propriedade_industrial:humano | 4.6 | 4.0 |
| modelagem_matematica:ferramenta | 4.0 | 3.6 |
| modelagem_matematica:humano | 4.2 | 4.0 |
| resistencia_materiais:ferramenta | 3.4 | 4.0 |
| resistencia_materiais:humano | 4.0 | 4.0 |

## Viés de posição residual (Passo B)

Medida de robustez do protocolo: proporção de combinações (disciplina, juiz) em que os 4 votos batem exatamente com a assinatura determinística 'sempre escolhe o rótulo A' ou 'sempre escolhe o rótulo B' nas execuções balanceadas (AB, BA, AB, BA). O balanceamento de ordem neutraliza o viés de posição transformando-o em empate (2-2); a taxa abaixo documenta o quanto desse comportamento residual ainda aparece. Não é indicador de sucesso/falha — é um resultado do experimento.

- Taxa geral de suspeita de viés de posição: **0.143** (2 de 14 combinações)
- Por juiz:

| Juiz | Suspeitos | Total | Taxa |
|---|---|---|---|
| qwen2.5:14b | 0 | 7 | 0.0 |
| deepseek-r1:14b | 2 | 7 | 0.286 |

| Disciplina | Juiz | Suspeito |
|---|---|---|
| estatistica_data_science | deepseek-r1:14b | False |
| estatistica_data_science | qwen2.5:14b | False |
| banco_de_dados | deepseek-r1:14b | False |
| banco_de_dados | qwen2.5:14b | False |
| desenvolvimento_full_cycle | deepseek-r1:14b | False |
| desenvolvimento_full_cycle | qwen2.5:14b | False |
| modelagem_matematica | deepseek-r1:14b | False |
| modelagem_matematica | qwen2.5:14b | False |
| estatistica_geral | deepseek-r1:14b | True |
| estatistica_geral | qwen2.5:14b | False |
| ferramentas_propriedade_industrial | deepseek-r1:14b | False |
| ferramentas_propriedade_industrial | qwen2.5:14b | False |
| resistencia_materiais | deepseek-r1:14b | True |
| resistencia_materiais | qwen2.5:14b | False |

## Concordância holística entre juízes (Passo B)

- Percentual de concordância: 0.286
- Total de disciplinas: 7

| Disciplina | Juiz 1 | Juiz 2 | Concordam |
|---|---|---|---|
| estatistica_data_science | paa_2 | paa_1 | False |
| banco_de_dados | paa_1 | paa_1 | True |
| desenvolvimento_full_cycle | paa_1 | paa_2 | False |
| modelagem_matematica | paa_2 | tie | False |
| estatistica_geral | tie | paa_2 | False |
| ferramentas_propriedade_industrial | paa_1 | tie | False |
| resistencia_materiais | tie | tie | True |

## Vitórias/Empates/Derrotas do framework vs humano (Passo B)

| Juiz | Vitórias (gerado) | Vitórias (humano) | Empates |
|---|---|---|---|
| deepseek-r1:14b | 2 | 3 | 2 |
| qwen2.5:14b | 2 | 2 | 3 |

## Padrão bruto de votos por disciplina/juiz (Passo B)

| Disciplina | Juiz | Padrão | Votos (4 exec.) | Preferência |
|---|---|---|---|---|
| banco_de_dados | deepseek-r1:14b | 1-3 humano | paa_1; paa_1; paa_1; paa_2 | paa_1 |
| banco_de_dados | qwen2.5:14b | 0-4 humano | paa_1; paa_1; paa_1; paa_1 | paa_1 |
| desenvolvimento_full_cycle | deepseek-r1:14b | 1-3 humano | paa_1; paa_1; paa_1; paa_2 | paa_1 |
| desenvolvimento_full_cycle | qwen2.5:14b | 3-1 gerado | paa_1; paa_2; paa_2; paa_2 | paa_2 |
| estatistica_data_science | deepseek-r1:14b | 4-0 gerado | paa_2; paa_2; paa_2; paa_2 | paa_2 |
| estatistica_data_science | qwen2.5:14b | 0-4 humano | paa_1; paa_1; paa_1; paa_1 | paa_1 |
| estatistica_geral | deepseek-r1:14b | 2-2 tie | paa_1; paa_2; paa_1; paa_2 | tie |
| estatistica_geral | qwen2.5:14b | 3-1 gerado | paa_1; paa_2; paa_2; paa_2 | paa_2 |
| ferramentas_propriedade_industrial | deepseek-r1:14b | 1-3 humano | paa_1; paa_1; paa_1; paa_2 | paa_1 |
| ferramentas_propriedade_industrial | qwen2.5:14b | 2-2 tie | paa_2; paa_1; paa_1; paa_2 | tie |
| modelagem_matematica | deepseek-r1:14b | 3-1 gerado | paa_2; paa_2; paa_1; paa_2 | paa_2 |
| modelagem_matematica | qwen2.5:14b | 1-2 tie | paa_1; tie; paa_1; paa_2 | tie |
| resistencia_materiais | deepseek-r1:14b | 2-2 tie | paa_1; paa_2; paa_1; paa_2 | tie |
| resistencia_materiais | qwen2.5:14b | 1-2 tie | paa_2; tie; paa_1; paa_1 | tie |
