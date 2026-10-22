"""Estatísticas descritivas e comparativas entre grupos."""
import statistics
from typing import List, Optional

import numpy as np
from scipy import stats


def descritivas(valores: List[float]) -> Optional[dict]:
    if not valores:
        return None
    return {
        "n": len(valores),
        "media": round(statistics.fmean(valores), 4),
        "mediana": round(float(np.median(valores)), 4),
        "dp": round(statistics.pstdev(valores) if len(valores) > 1 else 0.0, 4),
        "min": round(min(valores), 4),
        "max": round(max(valores), 4),
    }


def cohen_d(grupo_a: List[float], grupo_b: List[float]) -> float:
    if not grupo_a or not grupo_b:
        return 0.0
    a = np.asarray(grupo_a, dtype=float)
    b = np.asarray(grupo_b, dtype=float)
    n1, n2 = len(a), len(b)
    dp_pool = np.sqrt(((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2))
    if dp_pool == 0:
        return 0.0
    return float((a.mean() - b.mean()) / dp_pool)


def comparar_pareado(humano: List[float], ferramenta: List[float],
                     nome_metrica: str) -> dict:
    """Comparação pareada humano vs ferramenta: t-test pareado + Wilcoxon + d de Cohen."""
    if not humano or not ferramenta or len(humano) != len(ferramenta):
        return {"metrica": nome_metrica, "erro": "grupos incompatíveis"}

    t_stat, p_t = stats.ttest_rel(humano, ferramenta)
    try:
        w_stat, p_w = stats.wilcoxon(humano, ferramenta)
    except ValueError:
        w_stat, p_w = None, None

    return {
        "metrica": nome_metrica,
        "humano": descritivas(humano),
        "ferramenta": descritivas(ferramenta),
        "d_cohen": round(cohen_d(humano, ferramenta), 4),
        "t_pareado": round(float(t_stat), 4),
        "p_t": round(float(p_t), 4),
        "w_wilcoxon": round(float(w_stat), 4) if w_stat is not None else None,
        "p_w": round(float(p_w), 4) if p_w is not None else None,
        "significativo_p005": (p_t < 0.05) or (p_w is not None and p_w < 0.05),
    }


def kruskal_wallis(grupos: List[List[float]], nomes: List[str]) -> dict:
    """Teste não-paramétrico entre 3+ grupos."""
    dados_validos = [g for g in grupos if len(g) > 0]
    if len(dados_validos) < 3:
        return {"erro": "necessário pelo menos 3 grupos com dados"}
    h, p = stats.kruskal(*dados_validos)
    return {"h": round(float(h), 4), "p": round(float(p), 4), "grupos": nomes}
