# Relatório - resistencia_materiais

Gerado em: 2026-08-01T16:32:03.771986

## Métricas objetivas

### Humano
| Métrica | Valor |
|---|---|
| SCI | 0.771 |
| WD  | 0.028 |
| SVR | 0.912 |
| Cobertura conteúdo | 0.921 |
| Objetivos teóricos OK | 1.000 |
| Objetivos atividade OK | 0.375 |

### Ferramenta
| Métrica | Valor |
|---|---|
| SCI | 1.000 |
| WD  | 0.000 |
| SVR | 0.833 |
| Cobertura conteúdo | 1.000 |
| Objetivos teóricos OK | 1.000 |
| Objetivos atividade OK | 0.750 |

## Minutagem por UA (Ferramenta)

| UA | Minutagem | Alvo | WD | SCI | SVR |
|---|---|---|---|---|---|
| UA1 | 300 | 300 | 0.000 | 1.000 | 0.833 |
| UA2 | 400 | 400 | 0.000 | 1.000 | 0.833 |
| UA3 | 400 | 400 | 0.000 | 1.000 | 0.833 |
| UA4 | 400 | 400 | 0.000 | 1.000 | 0.833 |
| UA5 | 400 | 400 | 0.000 | 1.000 | 0.833 |
| UA6 | 400 | 400 | 0.000 | 1.000 | 0.833 |
| UA7 | 400 | 400 | 0.000 | 1.000 | 0.833 |
| UA8 | 400 | 400 | 0.000 | 1.000 | 0.833 |

## LAAJ (LLM-as-a-Judge)

### Passo A - Escore global ponderado (5 critérios, peso 20% cada)

| Juiz | Humano | Ferramenta |
|---|---|---|
| deepseek-r1:14b | 4.0 | 3.4 |
| qwen2.5:14b | 4.0 | 4.0 |

#### Mediana por critério - humano

| Juiz | répl. válidas | falhas | curricular_alignment | learning_objectives | constructive_alignment | pedagogical_progression | activity_resource_workload_viability |
|---|---|---|---|---|---|---|---|
| deepseek-r1:14b | 3 | 0 | 4 | 4 | 4 | 5 | 3 |
| qwen2.5:14b | 3 | 0 | 4 | 4 | 4 | 4 | 4 |

#### Mediana por critério - ferramenta

| Juiz | répl. válidas | falhas | curricular_alignment | learning_objectives | constructive_alignment | pedagogical_progression | activity_resource_workload_viability |
|---|---|---|---|---|---|---|---|
| deepseek-r1:14b | 3 | 0 | 4 | 3 | 4 | 3 | 3 |
| qwen2.5:14b | 3 | 0 | 4 | 4 | 4 | 4 | 4 |

### Passo B - Preferência holística (humano vs ferramenta)

| Juiz | Padrão de votos | Votos (4 exec.) | Preferência final |
|---|---|---|---|
| deepseek-r1:14b | 2-2 tie | paa_1; paa_2; paa_1; paa_2 | tie |
| qwen2.5:14b | 1-2 tie | paa_2; tie; paa_1; paa_1 | tie |
