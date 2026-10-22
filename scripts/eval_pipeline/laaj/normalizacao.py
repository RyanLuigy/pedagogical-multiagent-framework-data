"""Normalização de referências a objetivos (G1/G2) para o LAAJ.

PAAs humanos frequentemente rotulam objetivos de atividades com "G1: ObjN",
referindo-se a objetivos já definidos em outros recursos da mesma UA (ou de
outra UA, com prefixo "UAM -"). Enviados crus ao juiz, esses rótulos são
ininteligíveis — e, no caso de referências puras ("G1: Obj1    G2: Obj2"),
o loader chega a descartá-los por completo (objetivos vazios).

Este módulo opera sobre o dado bruto (`dados = {"temas": [...]}`), ANTES do
`_split_objetivos` do loader, e:
  1. resolve referências G -> texto do objetivo (mesma UA ou cross-UA);
  2. mantém textos inline quando presentes;
  3. deduplica objetivos por recurso;
  4. uniformiza a forma dos objetivos (texto puro, sem rótulos "ObjN." que o
     loader já descartaria — o juiz recebe textos completos e consistentes).

É um no-op para PAAs gerados (sem marcadores G/ObjN).
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# G-label: "G1", "G.1", "G.1, G.2 e G.3"
_G_LABEL = r"G\.?\s*\d+(?:[\s,.;]*e?[\s,.;]*G\.?\s*\d+)*"
# Referência cross-UA: "UA1 -" / "UA 1 -"
_UA_REF = r"UA\s*\d+\s*[-:.\u2013]?\s*"
# Marcador completo de objetivo: [G-label][UA-ref]ObjN<separador>
_MARKER = re.compile(
    r"\b(?:" + _G_LABEL + r"\s*[:.\-]?\s*)?"
    r"(?:" + _UA_REF + r")?"
    r"Obj\.?\s*\d+\s*[:.\-]?\s*",
    re.IGNORECASE,
)


def _flat_objetivos(recurso: dict) -> List[str]:
    raw = recurso.get("objetivos") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(x).strip() for x in raw if str(x).strip()]


def _tem_marcador(entry: str) -> bool:
    return bool(_MARKER.search(entry))


def _tokenizar_objetivos(s: str) -> List[dict]:
    """Divide uma string de objetivos em marcadores e seus textos.

    Cada item: {"g": [números G], "ua": int|None, "num": int|None,
    "texto": str, "raw": trecho original}. "num" None indica texto puro
    (sem marcador ObjN).
    """
    matches = list(_MARKER.finditer(s))
    if not matches:
        texto = s.strip()
        return [{"g": [], "ua": None, "num": None, "texto": texto, "raw": texto}] if texto else []

    objs: List[dict] = []
    if matches[0].start() > 0:
        pre = s[: matches[0].start()].strip()
        if pre:
            objs.append({"g": [], "ua": None, "num": None, "texto": pre, "raw": pre})

    for idx, m in enumerate(matches):
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(s)
        prefixo = m.group(0)
        texto = s[m.end():fim].strip()
        g = [int(x) for x in re.findall(r"G\.?\s*(\d+)", prefixo)]
        ua_m = re.search(r"UA\s*(\d+)", prefixo, re.IGNORECASE)
        num_m = re.search(r"Obj\.?\s*(\d+)", prefixo, re.IGNORECASE)
        objs.append({
            "g": g,
            "ua": int(ua_m.group(1)) if ua_m else None,
            "num": int(num_m.group(1)) if num_m else None,
            "texto": texto,
            "raw": s[m.start():fim],
        })
    return objs


def _numerar_objetivos(objs: List[dict]) -> Dict[int, str]:
    """Atribui números aos objetivos de uma UA, na ordem de aparição.

    Objetivos explícitos ("ObjN") mantêm seu número; objetivos sem rótulo
    (texto puro) preenchem posicionalmente os números ausentes em 1..N —
    convenção observada nos dados reais (ex.: UA04 da FPI tem Obj1, Obj4 e
    Obj8 sem rótulo, preenchidos pelos textos puros na ordem).
    """
    mapa: Dict[int, str] = {}
    explicitos: Dict[int, str] = {}
    pos_plain: List[int] = []
    for i, o in enumerate(objs):
        if o["num"] is not None:
            explicitos.setdefault(o["num"], o["texto"])
        else:
            pos_plain.append(i)
    tomados = set(explicitos)
    n_total = len(objs)
    max_num = max([0] + list(tomados))
    candidatos = [n for n in range(1, max(n_total, max_num) + 1) if n not in tomados]
    for idx, pos in enumerate(pos_plain):
        if idx < len(candidatos):
            explicitos.setdefault(candidatos[idx], objs[pos]["texto"])
    return explicitos


def _construir_pool(dados: dict) -> Dict[int, Dict[int, str]]:
    """pool[ua_index][num_objetivo] = texto, com numeração posicional por UA."""
    pool: Dict[int, Dict[int, str]] = {}
    for ua_idx, tema in enumerate(dados.get("temas", []) or []):
        objs_ua: List[dict] = []
        for r in tema.get("recursos") or []:
            for entry in _flat_objetivos(r):
                for obj in _tokenizar_objetivos(entry):
                    if obj["texto"]:
                        objs_ua.append(obj)
        pool[ua_idx] = _numerar_objetivos(objs_ua)
    return pool


def _chave_texto(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip().lower()


def _normalizar_tema(dados: dict, ua_idx: int, tema: dict, pool: dict,
                     slug: str, origem: str, log: List[dict]) -> None:
    for r in tema.get("recursos") or []:
        entries = _flat_objetivos(r)
        if not entries or not any(_tem_marcador(e) for e in entries):
            continue

        novos: List[str] = []
        for entry in entries:
            objs = _tokenizar_objetivos(entry)
            puro = len(objs) == 1 and objs[0]["num"] is None
            if puro:
                novos.append(objs[0]["texto"])
                continue
            for obj in objs:
                if obj["num"] is None:
                    novos.append(obj["texto"])
                    continue
                alvo = (obj["ua"] - 1) if obj["ua"] is not None else ua_idx
                texto = obj["texto"]
                evento_tipo = None
                if not texto:
                    texto = pool.get(alvo, {}).get(obj["num"])
                    evento_tipo = "referencia_resolvida" if texto else "nao_resolvido"
                if not texto:
                    log.append({
                        "slug": slug, "origem": origem,
                        "ua": tema.get("ua"), "recurso": r.get("titulo"),
                        "tipo": "nao_resolvido", "referencia": obj["raw"],
                        "objetivo": None, "alvo_ua": obj["ua"],
                    })
                    novos.append(obj["raw"])
                    continue
                if evento_tipo:
                    log.append({
                        "slug": slug, "origem": origem,
                        "ua": tema.get("ua"), "recurso": r.get("titulo"),
                        "tipo": evento_tipo, "referencia": obj["raw"],
                        "objetivo": texto, "alvo_ua": obj["ua"],
                    })
                novos.append(texto)

        vistos = set()
        unicos: List[str] = []
        for t in novos:
            key = _chave_texto(t)
            if key in vistos:
                log.append({
                    "slug": slug, "origem": origem,
                    "ua": tema.get("ua"), "recurso": r.get("titulo"),
                    "tipo": "deduplicado", "referencia": t, "objetivo": t,
                    "alvo_ua": None,
                })
                continue
            vistos.add(key)
            unicos.append(t)

        r["objetivos"] = unicos


def normalizar_referencias_objetivos(dados: dict, slug: str,
                                     origem: str = "desconhecida") -> List[dict]:
    """Resolve referências G/ObjN nos objetivos de todos os recursos.

    Modifica `dados["temas"][...]["recursos"][...]["objetivos"]` in-place e
    retorna os eventos de log (para laaj_log_normalizacao.json).
    """
    pool = _construir_pool(dados)
    log: List[dict] = []
    for ua_idx, tema in enumerate(dados.get("temas", []) or []):
        _normalizar_tema(dados, ua_idx, tema, pool, slug, origem, log)
    if log:
        logger.warning(
            f"Normalização de referências G em {slug} ({origem}): "
            f"{len(log)} evento(s) — "
            f"{sum(1 for e in log if e['tipo'] == 'referencia_resolvida')} resolvidos, "
            f"{sum(1 for e in log if e['tipo'] == 'nao_resolvido')} não-resolvidos."
        )
    return log
