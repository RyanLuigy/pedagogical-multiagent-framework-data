"""Sanitização de PAAs antes de qualquer envio ao LAAJ.

Remove marcadores de processo interno (rascunho, temporário, placeholders de
exportação) que poderiam revelar a origem do artefato ao juiz, quebrando o
cegamento exigido pelos Passos A e B.

A sanitização EDITA o texto in-place e nunca descarta recursos/UAs inteiros
por conterem marcadores — apenas limpa o trecho do marcador, preservando
minutagem, conteudo_formativo e objetivos intactos.
"""
import logging
import re
from typing import Iterator, List, Tuple

logger = logging.getLogger(__name__)

# Padrões conhecidos de marcadores de processo interno. Expandir esta lista
# sempre que um novo padrão for identificado nos dados reais.
PADROES_MARCADORES_INTERNOS = [
    re.compile(r"\[TEMP\]\s*", re.IGNORECASE),
    re.compile(r"\[RASCUNHO\]\s*", re.IGNORECASE),
    re.compile(r"\[DRAFT\]\s*", re.IGNORECASE),
    re.compile(r"\[PLACEHOLDER\]\s*", re.IGNORECASE),
    re.compile(r"\[WIP\]\s*", re.IGNORECASE),
]


def _marcadores_em(texto: str) -> bool:
    """True se algum marcador de processo interno está presente."""
    return any(p.search(texto) for p in PADROES_MARCADORES_INTERNOS)


def sanitizar_texto(texto: str) -> str:
    """Remove marcadores de processo interno de uma string."""
    resultado = texto
    for padrao in PADROES_MARCADORES_INTERNOS:
        resultado = padrao.sub("", resultado)
    return resultado


def _campos_textuais(paa) -> Iterator[Tuple[str, str]]:
    """Gera (rotulo, texto) para todos os campos textuais visíveis ao juiz."""
    for ua in paa.uas:
        yield f"UA{ua.ua}.titulo", ua.titulo
        for i, c in enumerate(ua.conteudo_formativo):
            yield f"UA{ua.ua}.conteudo_formativo[{i}]", c
        for r in ua.recursos:
            yield f"UA{ua.ua}.recurso.titulo", r.titulo
            for i, c in enumerate(r.conteudo_formativo):
                yield f"UA{ua.ua}.recurso.conteudo_formativo[{i}]", c
            for i, o in enumerate(r.objetivos):
                yield f"UA{ua.ua}.recurso.objetivos[{i}]", o


def sanitizar_paa(paa) -> List[str]:
    """Aplica sanitização a todos os campos textuais visíveis pelo juiz.

    Modifica o PAA in-place e retorna a lista de ocorrências removidas (para
    auditoria e registro em laaj_log_sanitizacao.json).
    """
    marcadores_encontrados = []

    for ua in paa.uas:
        titulo_original = ua.titulo
        ua.titulo = sanitizar_texto(ua.titulo)
        if ua.titulo != titulo_original:
            marcadores_encontrados.append(
                f"[{paa.slug}] UA{ua.ua}.titulo: '{titulo_original}' -> '{ua.titulo}'"
            )

        for i, c in enumerate(ua.conteudo_formativo):
            novo = sanitizar_texto(c)
            if novo != c:
                marcadores_encontrados.append(
                    f"[{paa.slug}] UA{ua.ua}.conteudo_formativo[{i}]: '{c}' -> '{novo}'"
                )
            ua.conteudo_formativo[i] = novo

        for r in ua.recursos:
            titulo_original = r.titulo
            r.titulo = sanitizar_texto(r.titulo)
            if r.titulo != titulo_original:
                marcadores_encontrados.append(
                    f"[{paa.slug}] UA{ua.ua} recurso.titulo: '{titulo_original}' -> '{r.titulo}'"
                )
            for i, c in enumerate(r.conteudo_formativo):
                novo = sanitizar_texto(c)
                if novo != c:
                    marcadores_encontrados.append(
                        f"[{paa.slug}] UA{ua.ua} recurso.conteudo_formativo[{i}]: '{c}' -> '{novo}'"
                    )
                r.conteudo_formativo[i] = novo
            for i, o in enumerate(r.objetivos):
                novo = sanitizar_texto(o)
                if novo != o:
                    marcadores_encontrados.append(
                        f"[{paa.slug}] UA{ua.ua} recurso.objetivos[{i}]: '{o}' -> '{novo}'"
                    )
                r.objetivos[i] = novo

    if marcadores_encontrados:
        logger.warning(
            f"Marcadores de processo interno removidos em {paa.slug} ({paa.origem}): "
            f"{len(marcadores_encontrados)} ocorrência(s)."
        )
        for m in marcadores_encontrados:
            logger.warning(f"  {m}")

    return marcadores_encontrados


def validar_ausencia_de_marcadores(paa) -> List[str]:
    """Checagem pós-sanitização: varre todos os campos sanitizados em busca de
    qualquer padrão residual. Deve retornar lista vazia. Se não retornar vazia,
    a sanitização falhou e o PAA NÃO deve ser enviado ao juiz — o chamador deve
    levantar exceção em vez de prosseguir silenciosamente."""
    residuais = []
    for campo, texto in _campos_textuais(paa):
        for padrao in PADROES_MARCADORES_INTERNOS:
            if padrao.search(texto):
                residuais.append(f"{padrao.pattern} em {campo}")
    return residuais
