"""Métricas objetivas de avaliação.

Convenções (documentação das fórmulas):
- SCI  (Structural Composition Index)  [0,1]: presença e completude dos
  componentes estruturais obrigatórios do template institucional por UA.
- WD   (Weighted Deviation)             [0,1]: desvio relativo da minutagem
  real de cada UA em relação ao alvo institucional (1.0 = cap de 100% de desvio).
- SVR  (Structural Variety Ratio)       [0,1]: diversidade + intercalação dos
  tipos de recursos por UA.
- TPT  (Total Processing Time)          [s]: tempo total de geração (metadata.json).
"""
from eval_pipeline.schemas.normalized import PAA

# Tipos teóricos e práticos conforme premissas institucionais
TIPOS_TEORICOS = {"OVA", "Texto", "Vídeo", "Podcast"}
TIPOS_ATIVIDADE = {"Roteiro de Atividade (HTML)", "Quiz", "Parada Obrigatória",
                   "Exame de Conhecimentos", "Avaliação de Conhecimentos"}
COMPONENTES_OBRIGATORIOS = {"OVA", "Aula Síncrona", "Quiz"}


def sci_por_ua(ua) -> float:
    """Structural Composition Index de uma UA: fração de critérios atendidos."""
    tipos = ua.tipos
    criterios = 0.0
    total = 6.0

    if "OVA" in tipos:
        criterios += 1.0
    if "Aula Síncrona" in tipos:
        criterios += 1.0
    if "Quiz" in tipos:
        criterios += 1.0
    if ua.recursos:
        criterios += 1.0
    # Todo recurso possui conteúdo formativo
    if all(r.conteudo_formativo for r in ua.recursos):
        criterios += 1.0
    # Todo recurso possui objetivos
    if all(r.objetivos for r in ua.recursos):
        criterios += 1.0

    return criterios / total


def wd_por_ua(ua, alvo: float) -> float:
    """Weighted Deviation de uma UA em relação ao alvo (capped em 1.0)."""
    if alvo <= 0:
        return 0.0
    desvio_rel = abs(ua.minutagem_total - alvo) / alvo
    return min(1.0, desvio_rel)


def svr_por_ua(ua) -> float:
    """Structural Variety Ratio de uma UA (diversidade + intercalação)."""
    tipos = ua.tipos
    n = len(tipos)
    if n <= 1:
        return 1.0 if n == 1 else 0.0

    diversidade = len(set(tipos)) / n
    alternacoes = sum(1 for i in range(n - 1) if tipos[i] != tipos[i + 1])
    intercalacao = alternacoes / (n - 1)

    return 0.5 * diversidade + 0.5 * intercalacao


def calcular_metricas_objetivas(paa: PAA, alvos: list, ch_total: float = 60.0) -> dict:
    """Calcula SCI, WD, SVR e cobertura para um PAA inteiro."""
    if not paa.uas:
        return {"sci": 0.0, "wd": 1.0, "svr": 0.0, "por_ua": []}

    por_ua = []
    for ua in paa.uas:
        alvo = alvos[ua.indice] if ua.indice < len(alvos) else 0.0
        por_ua.append({
            "indice": ua.indice,
            "ua": ua.ua,
            "minutagem": ua.minutagem_total,
            "alvo": alvo,
            "sci": round(sci_por_ua(ua), 4),
            "wd": round(wd_por_ua(ua, alvo), 4),
            "svr": round(svr_por_ua(ua), 4),
            "num_recursos": len(ua.recursos),
        })

    return {
        "sci": round(sum(p["sci"] for p in por_ua) / len(por_ua), 4),
        "wd": round(sum(p["wd"] for p in por_ua) / len(por_ua), 4),
        "svr": round(sum(p["svr"] for p in por_ua) / len(por_ua), 4),
        "por_ua": por_ua,
    }
