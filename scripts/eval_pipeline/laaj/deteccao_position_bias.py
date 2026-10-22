"""Detecta assinatura determinística de viés de posição nas respostas do
Passo B: um juiz que escolhe sempre o mesmo rótulo (A ou B) em todas as
execuções, independente de qual artefato estava naquela posição.

Esta função roda sobre os `votos_traduzidos` já calculados por
avaliar_holistico_par, e não decide nada sobre o resultado — apenas
documenta a taxa de suspeita de viés de posição, para ser reportada como
métrica de robustez do próprio protocolo, seja qual for o valor.
"""
from typing import Dict, List


def eh_padrao_posicao_fixa(votos_traduzidos: List[str], paa_1_label: str, paa_2_label: str) -> bool:
    """votos_traduzidos: lista de 4 valores, cada um paa_1_label ou paa_2_label,
    na ordem das execuções (AB, BA, AB, BA). Retorna True se o padrão bate
    exatamente com 'sempre escolheu a posição A' (alternando paa_1/paa_2 na
    ordem esperada) ou 'sempre escolheu a posição B' (padrão espelhado)."""
    if len(votos_traduzidos) != 4:
        return False
    assinatura_sempre_a = [paa_1_label, paa_2_label, paa_1_label, paa_2_label]
    assinatura_sempre_b = [paa_2_label, paa_1_label, paa_2_label, paa_1_label]
    return votos_traduzidos == assinatura_sempre_a or votos_traduzidos == assinatura_sempre_b


def calcular_taxa_position_bias(resultados_passo_b: Dict[str, Dict]) -> Dict:
    """resultados_passo_b: {disciplina: {juiz: {"votos_traduzidos": [...]}}}.
    Retorna a taxa de suspeita de viés de posição, geral e por juiz, com o
    detalhe de quais (disciplina, juiz) foram sinalizados."""
    detalhe = []
    for disciplina, por_juiz in resultados_passo_b.items():
        for juiz, dados in por_juiz.items():
            suspeito = eh_padrao_posicao_fixa(
                dados["votos_traduzidos"], "paa_1", "paa_2"
            )
            detalhe.append({"disciplina": disciplina, "juiz": juiz, "suspeito_position_bias": suspeito})

    total = len(detalhe)
    suspeitos = sum(1 for d in detalhe if d["suspeito_position_bias"])

    por_juiz = {}
    for juiz in {d["juiz"] for d in detalhe}:
        itens_juiz = [d for d in detalhe if d["juiz"] == juiz]
        n = len(itens_juiz)
        s = sum(1 for d in itens_juiz if d["suspeito_position_bias"])
        por_juiz[juiz] = {"suspeitos": s, "total": n, "taxa": round(s / n, 3) if n else None}

    return {
        "taxa_geral": round(suspeitos / total, 3) if total else None,
        "suspeitos_total": suspeitos,
        "total": total,
        "por_juiz": por_juiz,
        "detalhe": detalhe,
    }
