"""Métricas de planejamento de carga: equilíbrio de minutagem entre UAs."""
import statistics


def planejamento_carga(paa) -> dict:
    """Equilíbrio da distribuição de carga entre UAs.

    - cv: coeficiente de variação das minutagens totais (menor = mais equilibrado).
    - desvio_gabarito: desvio médio relativo às durações de referência, se fornecidas.
    """
    totais = [ua.minutagem_total for ua in paa.uas]
    if not totais:
        return {"cv": 0.0, "media": 0.0, "min": 0.0, "max": 0.0}

    media = statistics.fmean(totais)
    dp = statistics.pstdev(totais) if len(totais) > 1 else 0.0
    cv = (dp / media) if media else 0.0

    return {
        "cv": round(cv, 4),
        "media": round(media, 2),
        "min": round(min(totais), 2),
        "max": round(max(totais), 2),
    }
