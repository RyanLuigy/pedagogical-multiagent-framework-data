"""Limite de escopo de UAs do PAA humano (UA9 em diante) para o LAAJ.

LAPs humanos podem conter estrutura adicional além das 8 UAs comparáveis
definidas pela CG (ex.: seções administrativas, anexos institucionais,
cabeçalhos/rodapés numerados como UA9, UA10). Enviar esse conteúdo ao juiz
pode (a) revelar a origem humana pelo formato institucional e (b) inflar o
documento com conteúdo fora da comparação justa com o LAP gerado (UA1..UA8).

Aplica-se EXCLUSIVAMENTE ao PAA humano — o PAA gerado não passa por este
corte (o framework já produz apenas as UAs definidas pela CG).
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)


def _numero_ua(ua_label: str) -> int:
    """Extrai o N de "UAN" (ex.: "UA09" -> 9)."""
    match = re.search(r"UA\s*(\d+)", str(ua_label), re.IGNORECASE)
    return int(match.group(1)) if match else 0


def limitar_uas_paa_humano(paa, limite_ua: int = 8) -> List[str]:
    """Remove do PAA HUMANO qualquer UA numerada acima do limite.

    Modifica o PAA in-place e retorna a lista de rótulos de UAs removidas
    (para auditoria e registro em laaj_log_escopo_uas.json).
    """
    uas_removidas = [ua for ua in paa.uas if _numero_ua(ua.ua) > limite_ua]
    if uas_removidas:
        logger.warning(
            f"{paa.slug} (humano): UAs acima de UA{limite_ua} removidas antes "
            f"do envio ao LAAJ: {[ua.ua for ua in uas_removidas]}"
        )
        paa.uas = [ua for ua in paa.uas if _numero_ua(ua.ua) <= limite_ua]
    return [ua.ua for ua in uas_removidas]
