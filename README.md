# Evaluation Data and Scripts

**Companion dataset for:**
> *A Pedagogically Oriented Multi-Agent Framework for AI-Assisted Instructional Planning with Institutional Memory and Teacher-in-the-Loop Learning*

[![DOI](https://zenodo.org/badge/1430334795.svg)](https://zenodo.org/badge/latestdoi/1430334795)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

---

## Authors

- **Ryan Luz**\* (luigyryan@gmail.com) -- [ORCID: 0009-0001-4599-3988](https://orcid.org/0009-0001-4599-3988)
- **Leonardo Cardia** (leonardo.cardia@fieb.org.br) -- [ORCID: 0000-0002-2502-7408](https://orcid.org/0000-0002-2502-7408)
- **Sanval Santos** (sanval.santos@fieb.org.br) -- [ORCID: 0000-0003-3196-6468](https://orcid.org/0000-0003-3196-6468)

*Affiliation:* SENAI CIMATEC University
*\*Corresponding author*

---

## Overview

This repository contains the **evaluation results** and **analysis scripts** used to assess the Copiloto PAA framework -- a pedagogically oriented multi-agent system for AI-assisted instructional planning. The framework generates Learning Activity Plans (PAAs) from institutional curricula and was evaluated across **7 disciplines** using both **objective metrics** and **LLM-as-a-Judge (LAAJ)** assessments.

> **Note on raw curriculum and institutional data:** The original Learning Activity Plans (both human-authored baselines and institutional inputs) contain proprietary educational and institutional content and cannot be publicly distributed. This repository provides all evaluation outputs (metrics, scores, statistical tests, reports) and the complete evaluation source code needed to understand and verify the reported results. Requests for anonymised excerpts may be directed to the corresponding author (Ryan Luz, `luigyryan@gmail.com`).

---

## Repository Structure

```
.
+-- README.md                          # This file
+-- LICENSE                            # CC-BY 4.0
+-- CITATION.cff                       # Machine-readable citation (CFF)
+-- DATA_DICTIONARY.md                 # Variable definitions and data schemas
|
+-- results/
|   +-- objective_metrics/             # Quantitative evaluation outputs
|   |   +-- resultados_objetivas.json  # Per-discipline, per-UA objective scores
|   |   +-- resultado_consolidado.json # Full consolidated results with ICC matrix
|   |   +-- resultado_consolidado_passo_a.csv  # Step A scores (flat CSV)
|   |   +-- resultado_consolidado_passo_b.csv  # Step B preferences (flat CSV)
|   |
|   +-- laaj/                          # LLM-as-a-Judge evaluation outputs
|   |   +-- laaj_consolidado.json      # Aggregated LAAJ results
|   |   +-- laaj_position_bias.json    # Position bias diagnostics
|   |   +-- laaj_<discipline>.json     # Per-discipline full LAAJ results
|   |   +-- pointwise/                 # Pointwise (Step A) scores per artifact
|   |   +-- holistic/                  # Pairwise holistic (Step B) comparisons
|   |   +-- audit_logs/                # Data integrity audit trails
|   |
|   +-- reports/                       # Human-readable markdown reports
|
+-- scripts/
|   +-- eval_pipeline/                 # Complete evaluation pipeline source code
|   |   +-- main.py                    # Pipeline orchestrator
|   |   +-- objective_metrics/         # SCI, WD, SVR, Coverage implementations
|   |   +-- stats/                     # Statistical tests (t-test, Wilcoxon, Cohen's d, ICC)
|   |   +-- laaj/                      # LLM-as-a-Judge framework
|   |   +-- schemas/                   # Data models
|   |   +-- loaders/                   # Data loading and parsing
|   |   +-- reporting/                 # Report generation
|   +-- benchmark_llms.py             # LLM benchmark comparison script
|
+-- pipeline/
    +-- config.yaml                    # Pipeline configuration (models, parameters)
```

---

## Disciplines Evaluated

| # | Discipline Slug | Domain |
|---|----------------|--------|
| 1 | `estatistica_data_science` | Statistics / Data Science |
| 2 | `banco_de_dados` | Database Systems |
| 3 | `desenvolvimento_full_cycle` | Full-Cycle Software Development |
| 4 | `modelagem_matematica` | Mathematical Modelling |
| 5 | `estatistica_geral` | General Statistics |
| 6 | `ferramentas_propriedade_industrial` | Industrial Property Tools |
| 7 | `resistencia_materiais` | Strength of Materials |

---

## Evaluation Methodology

### Objective Metrics (Automated)

| Metric | Abbreviation | Range | Description |
|--------|-------------|-------|-------------|
| Structural Composition Index | **SCI** | [0, 1] | Completeness of mandatory structural components per learning unit |
| Weighted Deviation | **WD** | [0, 1] | Relative deviation from target time allocation (lower = better) |
| Structural Variety Ratio | **SVR** | [0, 1] | Diversity and interleaving of resource types |
| Content Coverage | **Coverage** | [0, 1] | Fraction of curriculum content covered in the generated plan |
| Total Processing Time | **TPT** | seconds | End-to-end generation time |

### LLM-as-a-Judge (LAAJ) Protocol

A two-step evaluation protocol using two independent LLM judges (`deepseek-r1:14b` and `qwen2.5:14b`):

- **Step A (Pointwise):** Each artifact (human-authored and tool-generated) is scored independently on 5 pedagogical criteria (1-5 scale), with 3 replicas per judge for robustness.
- **Step B (Holistic Pairwise):** Direct head-to-head comparison with balanced position assignment (AB, BA, AB, BA -- 4 replicas) to control for position bias.

### Statistical Tests

- **Paired t-test** and **Wilcoxon signed-rank test** for human vs. tool comparison
- **Cohen's d** for effect size quantification
- **ICC(2,1)** and **ICC(3,1)** for inter-rater reliability assessment
- **Kruskal-Wallis H-test** for multi-group comparisons
- **Position bias detection** via deterministic signature analysis

---

## Computational Environment

| Component | Specification |
|-----------|--------------|
| Python | 3.11 |
| LLM Runtime | Ollama (local) |
| Judge Models | `deepseek-r1:14b`, `qwen2.5:14b` |
| LLM Temperature | 0.1 |
| LLM Top-p | 0.9 |
| Context Window | 32,768 tokens |
| Pointwise Replicas | 3 per judge |
| Holistic Replicas | 4 per judge (balanced AB/BA) |
| Key Dependencies | `numpy`, `scipy`, `pyyaml`, `requests` |

---

## Data Availability Statement (DAS)

> **Data Availability Statement:**  
> The evaluation datasets, metric results, statistical test outputs, and complete analysis pipeline generated during this study are openly available in the Zenodo repository at [https://zenodo.org/badge/latestdoi/1430334795](https://zenodo.org/badge/latestdoi/1430334795) and on GitHub at [https://github.com/RyanLuigy/pedagogical-multiagent-framework-data](https://github.com/RyanLuigy/pedagogical-multiagent-framework-data).  
> The original institutional curricula and proprietary Learning Activity Plans (PAAs) cannot be shared publicly due to institutional policies; anonymised excerpts are available from the corresponding author upon reasonable request.

---

## How to Cite

If you use this data or code in your work, please cite:

```bibtex
@dataset{luz2026pedagogical,
  author    = {Luz, Ryan and Cardia, Leonardo and Santos, Sanval},
  title     = {Evaluation Data: A Pedagogically Oriented Multi-Agent Framework
               for AI-Assisted Instructional Planning with Institutional Memory
               and Teacher-in-the-Loop Learning},
  year      = {2026},
  url       = {https://zenodo.org/badge/latestdoi/1430334795}
}
```

---

## License

This dataset is distributed under the [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) license.
The evaluation scripts are provided under the MIT License for code reuse.
