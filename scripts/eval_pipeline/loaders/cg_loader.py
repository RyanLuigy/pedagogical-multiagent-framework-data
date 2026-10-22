"""Carregador do CG (DCC estruturado) e do gabarito institucional."""
import json
from pathlib import Path
from typing import Dict, List


def carregar_cg(caminho_json: Path) -> Dict:
    """Carrega o cg.json (saída do agente_02 / DCC estruturado).

    Retorna dict com: conteudos_gerais (todos os conteúdos formativos listados),
    objetivos_gerais, competencias, modalidade, ch_total.
    """
    with open(caminho_json, encoding="utf-8") as f:
        dados = json.load(f)

    conteudos_gerais: List[str] = []
    objetivos_gerais: List[str] = []
    competencias: List[str] = []
    modalidade = "N/A"
    ch_total = 60.0

    # Conteúdos formativos costumam ficar sob 'CONTEÚDOS FORMATIVOS'
    conteudos_raw = dados.get("CONTEÚDOS FORMATIVOS") or dados.get("CONTEUDOS FORMATIVOS") or []
    if isinstance(conteudos_raw, list):
        for c in conteudos_raw:
            if isinstance(c, str):
                conteudos_gerais.append(c.strip())
            elif isinstance(c, dict):
                for v in c.values():
                    if isinstance(v, str) and v.strip():
                        conteudos_gerais.append(v.strip())

    # Objetivos da disciplina
    obj_raw = dados.get("OBJETIVOS") or dados.get("OBJETIVOS DA DISCIPLINA") or []
    if isinstance(obj_raw, list):
        for o in obj_raw:
            if isinstance(o, str):
                objetivos_gerais.append(o.strip())
            elif isinstance(o, dict):
                objetivos_gerais.append(str(o.get("objetivo") or o.get("descricao") or "").strip())

    competencias_raw = dados.get("COMPETÊNCIAS") or dados.get("COMPETENCIAS") or []
    if isinstance(competencias_raw, list):
        competencias = [str(c).strip() for c in competencias_raw if str(c).strip()]

    diretrizes = dados.get("DIRETRIZES DO COMPONENTE CURRICULAR") or {}
    modalidade = str(diretrizes.get("MODALIDADE", modalidade) or modalidade)

    ch_str = ""
    for chave in ("CARGA HORÁRIA", "CARGA HORARIA", "CH TOTAL", "CH TOTAL (HORAS)"):
        valor_chave = diretrizes.get(chave)
        if valor_chave:
            ch_str = str(valor_chave)
            break
    import re
    match = re.search(r"(\d+)", ch_str)
    if match:
        ch_total = float(match.group(1))

    return {
        "conteudos_gerais": [c for c in conteudos_gerais if c],
        "objetivos_gerais": [o for o in objetivos_gerais if o],
        "competencias": [c for c in competencias if c],
        "modalidade": modalidade,
        "ch_total": ch_total,
    }


def carregar_gabarito(caminho_json: Path) -> Dict:
    """Carrega disciplina_gabarito.json (referência institucional por disciplina)."""
    with open(caminho_json, encoding="utf-8") as f:
        return json.load(f)


def texto_completo_cg(dados: Dict) -> str:
    """Serializa o CG (dict cru do cg.json) em texto legível para prompts de LLM."""
    partes = []

    diretrizes = dados.get("DIRETRIZES DO COMPONENTE CURRICULAR") or {}
    if diretrizes:
        partes.append("DIRETRIZES DO COMPONENTE CURRICULAR:")
        for k, v in diretrizes.items():
            if v not in (None, ""):
                partes.append(f"- {k}: {v}")

    ementa = dados.get("EMENTA")
    if ementa:
        partes.append("EMENTA:")
        partes.append(str(ementa))

    competencias = dados.get("COMPETÊNCIAS") or dados.get("COMPETENCIAS") or []
    if competencias:
        partes.append("COMPETÊNCIAS:")
        if isinstance(competencias, list):
            partes.extend(f"- {c}" for c in competencias if str(c).strip())
        else:
            partes.append(str(competencias))

    objetivos = (dados.get("OBJETIVOS DE APRENDIZAGEM")
                 or dados.get("OBJETIVOS")
                 or dados.get("OBJETIVOS DA DISCIPLINA") or [])
    if objetivos:
        partes.append("OBJETIVOS DE APRENDIZAGEM:")
        if isinstance(objetivos, list):
            partes.extend(f"- {o}" for o in objetivos if str(o).strip())
        else:
            partes.append(str(objetivos))

    criterios = dados.get("CRITÉRIOS DE AVALIAÇÃO (Resumo)") or dados.get("CRITÉRIOS DE AVALIAÇÃO")
    if criterios:
        partes.append("CRITÉRIOS DE AVALIAÇÃO:")
        partes.append(str(criterios))

    conteudos = dados.get("CONTEÚDOS FORMATIVOS") or dados.get("CONTEUDOS FORMATIVOS") or []
    if conteudos:
        partes.append("CONTEÚDOS FORMATIVOS:")
        for c in conteudos:
            if isinstance(c, str):
                partes.append(f"- {c}")
            elif isinstance(c, dict):
                for v in c.values():
                    if isinstance(v, str) and v.strip():
                        partes.append(f"- {v}")

    return "\n".join(partes)
