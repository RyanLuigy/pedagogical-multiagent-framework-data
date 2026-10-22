"""Carregadores e normalizadores dos artefatos de PAA (humano e ferramenta).

UA09 é ignorada em tudo (indices >= 8).
"""
import json
import re
from pathlib import Path
from typing import List, Optional

from eval_pipeline.schemas.normalized import PAA, UA, Recurso

# Mapas de tipo -> canônico
TIPO_CANONICO = {
    "ova": "OVA",
    "texto": "Texto",
    "texto (html)": "Texto",
    "texto (html) (infra)": "Texto",
    "texto (infra)": "Texto",
    "texto (gratuito)": "Texto",
    "roteiro de atividade (html)": "Roteiro de Atividade (HTML)",
    "roteiro de atividade": "Roteiro de Atividade (HTML)",
    "roteiro": "Roteiro de Atividade (HTML)",
    "aula síncrona": "Aula Síncrona",
    "aula sincrona": "Aula Síncrona",
    "na": "Aula Síncrona",
    "quiz": "Quiz",
    "vídeo": "Vídeo",
    "video": "Vídeo",
    "podcast": "Podcast",
    "parada obrigatória": "Parada Obrigatória",
    "parada obrigatoria": "Parada Obrigatória",
    "exame de conhecimentos": "Exame de Conhecimentos",
    "avaliação de conhecimentos": "Avaliação de Conhecimentos",
}

NUM_UAS_UTILIZADAS = 8  # UA09 ignorada para tudo


def _normalizar_tipo(tipo_raw: Optional[str]) -> str:
    if not tipo_raw:
        return "Desconhecido"
    chave = tipo_raw.strip().lower()
    if chave in TIPO_CANONICO:
        return TIPO_CANONICO[chave]
    # Fallback: tira números/parênteses
    limpo = re.sub(r"\s*\(\w+\)\s*", "", tipo_raw, flags=re.IGNORECASE).strip()
    return TIPO_CANONICO.get(limpo.lower(), tipo_raw.strip() or "Desconhecido")


def _parse_minutagem(valor) -> Optional[float]:
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", texto)
    if not match:
        return None
    return float(match.group(0).replace(",", "."))


def _eh_so_prefixo_grupo(t: str) -> bool:
    """True se o texto é apenas um prefixo de grupo (ex.: 'G.1, G.2 e G.3:')."""
    return bool(re.match(
        r"^G\.?\s*\d+([\s,.;]*e?[\s,.;]*G\.?\s*\d+)*:?\s*$", t, re.IGNORECASE
    ))


def _split_objetivos(objetivos) -> List[str]:
    """Humanos às vezes gravam todos os objetivos em uma única string com 'ObjN.'.

    Re-divida também itens de listas já carregadas (ex.: agent_05) que contenham
    múltiplos marcadores 'ObjN.' concatenados, e descarta prefixos de grupo ('G.1:').
    """
    if not objetivos:
        return []
    if isinstance(objetivos, str):
        objetivos = [objetivos]

    resultado = []
    for o in objetivos:
        s = str(o).strip()
        if not s:
            continue
        itens = re.split(r"(?i)\s*Obj\.?\s*\d+[.)]?\s*", s)
        itens = [i.strip() for i in itens if i.strip()]
        if not itens:
            itens = [s]
        for item in itens:
            if item and not _eh_so_prefixo_grupo(item):
                resultado.append(item)
    return resultado


def _extrair_recursos(ua_raw: dict) -> List[Recurso]:
    recursos = []
    for r in ua_raw.get("recursos", []) or []:
        if not isinstance(r, dict):
            continue
        recursos.append(Recurso(
            tipo=_normalizar_tipo(r.get("tipo")),
            titulo=str(r.get("titulo", "") or ""),
            minutagem=_parse_minutagem(r.get("minutagem")) or 0.0,
            conteudo_formativo=[str(c) for c in (r.get("conteudo_formativo") or []) if str(c).strip()],
            objetivos=_split_objetivos(r.get("objetivos")),
            id=r.get("id"),
        ))
    return recursos


def carregar_paa(caminho_json: Path, slug: str, origem: str = "desconhecida",
                 descartar_ua_extra: bool = True) -> PAA:
    """Carrega e normaliza um PAA ({'temas': [...]}).

    `descartar_ua_extra=True` (default) descarta UAs de índice >= 8 (regra
    de escopo do pipeline). No carregamento para o LAAJ, o PAA humano é
    carregado com `descartar_ua_extra=False` e o corte passa a ser feito por
    rótulo (UA9 em diante) via `limitar_uas_paa_humano`, para manter a
    auditoria do corte.
    """
    with open(caminho_json, encoding="utf-8") as f:
        dados = json.load(f)
    return carregar_paa_de_dados(dados, slug, origem, descartar_ua_extra)


def carregar_paa_de_dados(dados: dict, slug: str, origem: str = "desconhecida",
                          descartar_ua_extra: bool = True) -> PAA:
    """Constrói um PAA a partir de um dict já carregado (temas raw)."""
    temas = dados.get("temas", [])
    uas = []
    for indice, ua_raw in enumerate(temas):
        if descartar_ua_extra and indice >= NUM_UAS_UTILIZADAS:
            continue
        ua_raw = ua_raw or {}
        uas.append(UA(
            indice=indice,
            ua=str(ua_raw.get("ua", f"UA{indice + 1}")),
            titulo=str(ua_raw.get("titulo", "") or ""),
            conteudo_formativo=[str(c) for c in (ua_raw.get("conteudo_formativo") or []) if str(c).strip()],
            recursos=_extrair_recursos(ua_raw),
        ))
    return PAA(origem=origem, slug=slug, uas=uas)


def minutagem_alvo_por_ua(ch_total: float = 60.0) -> List[float]:
    """Distribuição institucional de minutagem (UA1 = 300/100; UAs 2-8 = 400/200)."""
    if ch_total >= 60:
        ua1, demais = 300.0, 400.0
    else:
        ua1, demais = 100.0, 200.0
    return [ua1] + [demais] * (NUM_UAS_UTILIZADAS - 1)
