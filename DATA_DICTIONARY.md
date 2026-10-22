# Data Dictionary

This document defines all variables, fields, and data schemas used in the evaluation results.

---

## 1. Objective Metrics (esults/objective_metrics/)

### esultados_objetivas.json

Top-level keys are discipline slugs. Each contains humano and erramenta sub-objects:

| Field | Type | Description |
|-------|------|-------------|
| estrutura.sci | float [0,1] | Structural Composition Index (mean across UAs) |
| estrutura.wd | float [0,1] | Weighted Deviation from target timing (mean across UAs) |
| estrutura.svr | float [0,1] | Structural Variety Ratio (mean across UAs) |
| estrutura.por_ua[].indice | int | UA index (0-based) |
| estrutura.por_ua[].ua | string | UA identifier (e.g., "UA01") |
| estrutura.por_ua[].minutagem | float | Actual total minutes for the UA |
| estrutura.por_ua[].alvo | float | Target minutes for the UA |
| estrutura.por_ua[].sci | float [0,1] | SCI for this specific UA |
| estrutura.por_ua[].wd | float [0,1] | WD for this specific UA |
| estrutura.por_ua[].svr | float [0,1] | SVR for this specific UA |
| estrutura.por_ua[].num_recursos | int | Number of resources in this UA |
| conteudo.cobertura_global | float [0,1] | Fraction of curriculum content covered |
| conteudo.cobertura_por_ua[] | array | Coverage broken down by UA |
| conteudo.nao_cobertos | string[] | Curriculum items NOT covered |
| objetivos.teoricos_ok | float [0,1] | Fraction of theory resources with valid objectives |
| objetivos.atividade_ok | float [0,1] | Fraction of activity resources aligned to theory objectives |
| carga.cv | float | Coefficient of variation of minutes across UAs |
| carga.media | float | Mean minutes per UA |
| carga.min | float | Minimum UA minutes |
| carga.max | float | Maximum UA minutes |
| 	pt | float (seconds) | Total Processing Time for generation |

### esultado_consolidado_passo_a.csv

Flat CSV of Step A (pointwise) LAAJ scores:

| Column | Type | Description |
|--------|------|-------------|
| disciplina | string | Discipline slug |
| rtefato | string | "humano" or "ferramenta" |
| juiz | string | Judge model identifier |
| criterio | string | Evaluation criterion name |
| mediana | float [1,5] | Median score across replicas |
| escore_global_ponderado | float [1,5] | Weighted global score |

### esultado_consolidado_passo_b.csv

Flat CSV of Step B (holistic) LAAJ preferences:

| Column | Type | Description |
|--------|------|-------------|
| disciplina | string | Discipline slug |
| juiz | string | Judge model identifier |
| preferencia_final | string | "paa_1" (human), "paa_2" (tool), or "tie" |
| otos | string | Raw vote pattern across 4 replicas |

---

## 2. LAAJ Results (esults/laaj/)

### laaj_consolidado.json

| Field | Type | Description |
|-------|------|-------------|
| escores_globais_ponderados | dict | {artifact_id: {judge: score}} Step A global scores |
| concordancia_holistica | dict | Inter-judge agreement on Step B preferences |
| itorias_empates_derrotas | dict | Win/tie/loss counts per judge |
| esultados_holistico_por_disciplina | dict | Step B results by discipline and judge |
| position_bias_passo_b | dict | Position bias diagnostics |

### laaj_position_bias.json

| Field | Type | Description |
|-------|------|-------------|
| 	axa_geral | float [0,1] | Overall suspected position bias rate |
| suspeitos_total | int | Number of suspected bias instances |
| 	otal | int | Total discipline-judge combinations |
| por_juiz | dict | Per-judge bias rates |
| detalhe[] | array | Per-combination bias flag |

### Pointwise files (pointwise/laaj_pointwise_<disc>_<origin>.json)

| Field | Type | Description |
|-------|------|-------------|
| juizes.<judge>.criterios | dict | Per-criterion scores (median of replicas) |
| juizes.<judge>.escore_global_ponderado | float [1,5] | Weighted aggregate score |
| juizes.<judge>.replicas | int | Number of replicas executed |

### Holistic files (holistic/laaj_holistico_<disc>.json)

| Field | Type | Description |
|-------|------|-------------|
| juizes.<judge>.votos_traduzidos | string[] | 4 votes translated to paa_1/paa_2/tie |
| juizes.<judge>.preferencia_final | string | Majority vote result |
| juizes.<judge>.justificativas | string[] | LLM justification texts |
| execucoes | int | Number of balanced replicas (4) |

---

## 3. Audit Logs (esults/laaj/audit_logs/)

### laaj_log_normalizacao.json

| Field | Type | Description |
|-------|------|-------------|
| eventos[].tipo | string | "referencia_resolvida", "nao_resolvido", or "deduplicado" |
| eventos[].disciplina | string | Discipline slug |
| eventos[].origem | string | "humano" or "ferramenta" |
| eventos[].detalhe | string | Human-readable description |
| esumo.referencias_resolvidas | int | Count of resolved references |
| esumo.nao_resolvidas | int | Count of unresolved references |
| esumo.deduplicadas | int | Count of deduplicated entries |

### laaj_log_sanitizacao.json

| Field | Type | Description |
|-------|------|-------------|
| ocorrencias[] | array | Each sanitization action taken |
| 	otal_marcadores_removidos | int | Total internal markers removed |

### laaj_log_escopo_uas.json

| Field | Type | Description |
|-------|------|-------------|
| por_disciplina | dict | UAs removed per discipline (human PAAs only) |
| 	otal_uas_fora_de_escopo_removidas | int | Total UAs filtered out |

---

## 4. Key Terminology

| Term | Definition |
|------|-----------|
| **PAA** | Plano de Atividades de Aprendizagem (Learning Activity Plan) |
| **UA** | Unidade de Aprendizagem (Learning Unit) - a module within a PAA |
| **CG** | Conteudos Gerais (General Curriculum Content) - the reference syllabus |
| **SCI** | Structural Composition Index |
| **WD** | Weighted Deviation |
| **SVR** | Structural Variety Ratio |
| **LAAJ** | LLM-as-a-Judge evaluation protocol |
| **paa_1** | Label for human-authored artifact in holistic comparisons |
| **paa_2** | Label for tool-generated artifact in holistic comparisons |
| **Pointwise** | Step A: independent scoring of each artifact |
| **Holistic** | Step B: pairwise head-to-head comparison |
