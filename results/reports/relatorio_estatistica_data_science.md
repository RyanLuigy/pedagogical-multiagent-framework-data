# Relatório - estatistica_data_science

Gerado em: 2026-08-01T16:32:03.759337

## Métricas objetivas

### Humano
| Métrica | Valor |
|---|---|
| SCI | 0.667 |
| WD  | 0.016 |
| SVR | 0.983 |
| Cobertura conteúdo | 0.559 |
| Objetivos teóricos OK | 1.000 |
| Objetivos atividade OK | 0.000 |

### Ferramenta
| Métrica | Valor |
|---|---|
| SCI | 1.000 |
| WD  | 0.000 |
| SVR | 0.992 |
| Cobertura conteúdo | 1.000 |
| Objetivos teóricos OK | 1.000 |
| Objetivos atividade OK | 0.062 |

## Minutagem por UA (Ferramenta)

| UA | Minutagem | Alvo | WD | SCI | SVR |
|---|---|---|---|---|---|
| UA1 | 300 | 300 | 0.000 | 1.000 | 1.000 |
| UA2 | 400 | 400 | 0.000 | 1.000 | 1.000 |
| UA3 | 400 | 400 | 0.000 | 1.000 | 1.000 |
| UA4 | 400 | 400 | 0.000 | 1.000 | 1.000 |
| UA5 | 400 | 400 | 0.000 | 1.000 | 1.000 |
| UA6 | 400 | 400 | 0.000 | 1.000 | 1.000 |
| UA7 | 400 | 400 | 0.000 | 1.000 | 1.000 |
| UA8 | 400 | 400 | 0.000 | 1.000 | 0.938 |

## LAAJ (LLM-as-a-Judge)

### Passo A - Escore global ponderado (5 critérios, peso 20% cada)

| Juiz | Humano | Ferramenta |
|---|---|---|
| deepseek-r1:14b | 4.0 | 3.8 |
| qwen2.5:14b | 4.0 | 4.0 |

#### Mediana por critério - humano

| Juiz | répl. válidas | falhas | curricular_alignment | learning_objectives | constructive_alignment | pedagogical_progression | activity_resource_workload_viability |
|---|---|---|---|---|---|---|---|
| deepseek-r1:14b | 3 | 0 | 4 | 4 | 4 | 4 | 4 |
| qwen2.5:14b | 3 | 0 | 4 | 4 | 4 | 4 | 4 |

#### Mediana por critério - ferramenta

| Juiz | répl. válidas | falhas | curricular_alignment | learning_objectives | constructive_alignment | pedagogical_progression | activity_resource_workload_viability |
|---|---|---|---|---|---|---|---|
| deepseek-r1:14b | 3 | 0 | 4 | 4 | 4 | 4 | 3 |
| qwen2.5:14b | 3 | 0 | 4 | 4 | 4 | 4 | 4 |

### Passo B - Preferência holística (humano vs ferramenta)

| Juiz | Padrão de votos | Votos (4 exec.) | Preferência final |
|---|---|---|---|
| deepseek-r1:14b | 4-0 gerado | paa_2; paa_2; paa_2; paa_2 | paa_2 |
| qwen2.5:14b | 0-4 humano | paa_1; paa_1; paa_1; paa_1 | paa_1 |
