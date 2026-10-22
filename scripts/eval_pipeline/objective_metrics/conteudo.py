"""Métricas de conteúdo: cobertura do DCC e alinhamento de objetivos."""
import re
from typing import List


def _normalizar(texto: str) -> str:
    return re.sub(r"[^a-z0-9áéíóúâêôãõçàü ]", " ", texto.lower()).strip()


def _tokens(norm: str) -> set:
    return {t for t in norm.split() if len(t) > 2}


def conteudo_coberto(conteudo_cg: str, conteudos_recursos: List[str]) -> bool:
    """Verifica se um conteúdo do CG aparece nos conteúdos dos recursos,
    por correspondência de tokens (ordenada) ou substring."""
    alvo = _normalizar(conteudo_cg)
    alvo_tokens = _tokens(alvo)
    if not alvo_tokens:
        return False
    for texto in conteudos_recursos:
        norm = _normalizar(texto)
        if alvo in norm:
            return True
        # coincidência de pelo menos 80% dos tokens significativos
        textos_tokens = _tokens(norm)
        if textos_tokens and len(alvo_tokens & textos_tokens) / len(alvo_tokens) >= 0.8:
            return True
    return False


def cobertura_conteudo(paa, conteudos_cg: List[str]) -> dict:
    """Fração dos conteúdos do CG cobertos nos recursos do PAA (global e por UA)."""
    if not conteudos_cg or not paa.uas:
        return {"cobertura_global": 0.0, "cobertura_por_ua": [], "nao_cobertos": list(conteudos_cg)}

    todos_conteudos_recursos = []
    cobertura_por_ua = []
    for ua in paa.uas:
        ua_conteudos = [c for r in ua.recursos for c in r.conteudo_formativo]
        todos_conteudos_recursos.extend(ua_conteudos)
        cobertos_ua = [c for c in conteudos_cg if conteudo_coberto(c, ua_conteudos)]
        cobertura_por_ua.append({
            "indice": ua.indice,
            "ua": ua.ua,
            "cobertura": round(len(cobertos_ua) / len(conteudos_cg), 4),
        })

    cobertos_global = [c for c in conteudos_cg if conteudo_coberto(c, todos_conteudos_recursos)]
    nao_cobertos = [c for c in conteudos_cg if c not in cobertos_global]

    return {
        "cobertura_global": round(len(cobertos_global) / len(conteudos_cg), 4),
        "cobertura_por_ua": cobertura_por_ua,
        "nao_cobertos": nao_cobertos,
    }


def _normalizar_objetivo(texto: str) -> str:
    """Normaliza um objetivo para comparação: remove prefixos de grupo (G.1:),
    marcadores de numeração (Obj.1:), pontuação e caixa."""
    t = texto.strip()
    # Remove lista de grupos: 'G.1, G.2 e G.3:', 'G1:', 'G.1:'
    t = re.sub(r"^(?:G\.?\s*\d+\s*[\s,.;]*[e&]?\s*)+:\s*", "", t, flags=re.IGNORECASE)
    # Remove marcadores 'Obj.N:' / 'Objetivo N:'
    t = re.sub(r"^Obj\.?\s*\d+[.)]?\s*[:]?\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"^Objetivo\s*\d+\s*[:]\s*", "", t, flags=re.IGNORECASE)
    # Normaliza caixa, acentos e espaços
    t = re.sub(r"\s+", " ", t).strip().lower()
    t = re.sub(r"[.,;:]\s*$", "", t)
    return t


def _objetivo_presente(objetivo, conjunto: set) -> bool:
    """True se o objetivo (normalizado) casa com algum item do conjunto."""
    if not objetivo:
        return False
    alvo = _normalizar_objetivo(objetivo)
    if not alvo:
        return False
    if alvo in conjunto:
        return True
    # Tolerância de substring para rótulos com sufixo (ex.: 'projetar vigas... (G1)')
    return any(alvo in c or c in alvo for c in conjunto)


def alinhamento_objetivos(paa) -> dict:
    """Percentual de recursos teóricos com até 5 objetivos e de recursos de
    atividade com objetivos já presentes em recursos teóricos."""
    if not paa.uas:
        return {"teoricos_ok": 0.0, "atividade_ok": 0.0}

    objetivos_teoricos = set()
    n_teoricos = 0
    n_teoricos_ok = 0
    n_atividade = 0
    n_atividade_ok = 0

    for ua in paa.uas:
        for r in ua.recursos:
            tipo_norm = r.tipo
            eh_teorico = tipo_norm in {"OVA", "Texto", "Vídeo", "Podcast"}
            eh_atividade = tipo_norm in {"Quiz", "Roteiro de Atividade (HTML)",
                                         "Parada Obrigatória", "Exame de Conhecimentos",
                                         "Avaliação de Conhecimentos"}
            if eh_teorico:
                n_teoricos += 1
                if 0 < len(r.objetivos) <= 5:
                    n_teoricos_ok += 1
                objetivos_teoricos.update(
                    _normalizar_objetivo(o) for o in r.objetivos if _normalizar_objetivo(o)
                )
            elif eh_atividade:
                n_atividade += 1
                if r.objetivos and all(
                    _objetivo_presente(o, objetivos_teoricos) for o in r.objetivos
                ):
                    n_atividade_ok += 1

    return {
        "teoricos_ok": round(n_teoricos_ok / n_teoricos, 4) if n_teoricos else 1.0,
        "atividade_ok": round(n_atividade_ok / n_atividade, 4) if n_atividade else 1.0,
        "num_teoricos": n_teoricos,
        "num_atividade": n_atividade,
    }
