"""Geração de relatórios em Markdown por disciplina e consolidado."""
from datetime import datetime
from typing import Dict, List


def _tabela_metricas(resumo: dict) -> str:
    linhas = [
        f"| SCI | {resumo['sci']:.3f} |",
        f"| WD  | {resumo['wd']:.3f} |",
        f"| SVR | {resumo['svr']:.3f} |",
        f"| Cobertura conteúdo | {resumo['cobertura']:.3f} |",
        f"| Objetivos teóricos OK | {resumo['teoricos_ok']:.3f} |",
        f"| Objetivos atividade OK | {resumo['atividade_ok']:.3f} |",
    ]
    return "| Métrica | Valor |\n|---|---|\n" + "\n".join(linhas)


def relatorio_disciplina(slug: str, res_humano: Dict, res_ferramenta: Dict,
                         laaj: Dict = None) -> str:
    linhas = [
        f"# Relatório - {slug}",
        "",
        f"Gerado em: {datetime.now().isoformat()}",
        "",
        "## Métricas objetivas",
        "",
        "### Humano",
        _tabela_metricas(res_humano["resumo_geral"]),
        "",
        "### Ferramenta",
        _tabela_metricas(res_ferramenta["resumo_geral"]),
        "",
    ]

    # Tabela por UA (ferramenta)
    linhas.append("## Minutagem por UA (Ferramenta)")
    linhas.append("")
    linhas.append("| UA | Minutagem | Alvo | WD | SCI | SVR |")
    linhas.append("|---|---|---|---|---|---|")
    for p in res_ferramenta["estrutura"]["por_ua"]:
        linhas.append(
            f"| {p['ua']} | {p['minutagem']:.0f} | {p['alvo']:.0f} | "
            f"{p['wd']:.3f} | {p['sci']:.3f} | {p['svr']:.3f} |"
        )
    linhas.append("")

    if laaj:
        linhas.append("## LAAJ (LLM-as-a-Judge)")
        linhas.append("")

        # Passo A - escores globais ponderados (documento inteiro) por juiz
        ponto = laaj.get("pointwise") or {}
        linhas.append("### Passo A - Escore global ponderado (5 critérios, peso 20% cada)")
        linhas.append("")
        linhas.append("| Juiz | Humano | Ferramenta |")
        linhas.append("|---|---|---|")
        for juiz in list(ponto.get("humano", {}).get("juizes", {}).keys()):
            g_h = ponto.get("humano", {}).get("juizes", {}).get(juiz, {})
            g_f = ponto.get("ferramenta", {}).get("juizes", {}).get(juiz, {})
            v_h = g_h.get("escore_global_ponderado")
            v_f = g_f.get("escore_global_ponderado")
            linhas.append(
                f"| {juiz} | {v_h if v_h is not None else '-'} | {v_f if v_f is not None else '-'} |"
            )
        linhas.append("")

        # Mediana por critério (ferramenta e humano)
        for origem in ("humano", "ferramenta"):
            res = ponto.get(origem)
            if not res:
                continue
            linhas.append(f"#### Mediana por critério - {origem}")
            linhas.append("")
            linhas.append("| Juiz | répl. válidas | falhas | "
                          "curricular_alignment | learning_objectives | constructive_alignment | "
                          "pedagogical_progression | activity_resource_workload_viability |")
            linhas.append("|---|---|---|---|---|---|---|---|")
            for juiz, g in res["juizes"].items():
                med = g.get("mediana_por_criterio") or {}
                linhas.append(
                    f"| {juiz} | {len(g.get('replicas_validas', []))} | {g.get('replicas_falhas', 0)} | "
                    + " | ".join(f"{med.get(c) if med.get(c) is not None else '-'}" for c in [
                        "curricular_alignment", "learning_objectives", "constructive_alignment",
                        "pedagogical_progression", "activity_resource_workload_viability",
                    ])
                    + " |"
                )
            linhas.append("")

        # Passo B - preferência holística por juiz
        hol = laaj.get("holistico") or {}
        if hol.get("juizes"):
            linhas.append("### Passo B - Preferência holística (humano vs ferramenta)")
            linhas.append("")
            linhas.append("| Juiz | Padrão de votos | Votos (4 exec.) | Preferência final |")
            linhas.append("|---|---|---|---|")
            for juiz, g in hol["juizes"].items():
                padrao = g.get("padrao_votos", "-")
                vencedor = g.get("vencedor_padrao_votos", "")
                votos = "; ".join(g.get("votos_traduzidos", []))
                linhas.append(
                    f"| {juiz} | {padrao} {vencedor} | {votos} | {g.get('preferencia_final')} |"
                )
    linhas.append("")

    return "\n".join(linhas)


def relatorio_laaj_consolidado(disciplinas: List[str], laaj_consolidado: Dict,
                               laaj_por_disciplina: Dict[str, Dict]) -> str:
    linhas = [
        "# Relatório LAAJ Consolidado",
        "",
        f"Gerado em: {datetime.now().isoformat()}",
        "",
    ]

    # 1. Escores globais ponderados por artefato/juiz
    escores = laaj_consolidado.get("escores_globais_ponderados", {})
    if escores:
        juizes = sorted({j for por_artefato in escores.values() for j in por_artefato})
        linhas.append("## Escore global ponderado (Passo A) por artefato/juiz")
        linhas.append("")
        linhas.append("| Artefato | " + " | ".join(juizes) + " |")
        linhas.append("|---|" + "---|" * len(juizes))
        for artefato_id in sorted(escores.keys()):
            vals = [escores[artefato_id].get(j) for j in juizes]
            linhas.append("| " + artefato_id + " | "
                          + " | ".join(str(v) if v is not None else "-" for v in vals) + " |")
        linhas.append("")

    # 2. Viés de posição residual (Passo B) — métrica de robustez do protocolo
    pb = laaj_consolidado.get("position_bias_passo_b") or {}
    linhas.append("## Viés de posição residual (Passo B)")
    linhas.append("")
    linhas.append("Medida de robustez do protocolo: proporção de combinações "
                  "(disciplina, juiz) em que os 4 votos batem exatamente com a "
                  "assinatura determinística 'sempre escolhe o rótulo A' ou "
                  "'sempre escolhe o rótulo B' nas execuções balanceadas "
                  "(AB, BA, AB, BA). O balanceamento de ordem neutraliza o viés "
                  "de posição transformando-o em empate (2-2); a taxa abaixo "
                  "documenta o quanto desse comportamento residual ainda aparece. "
                  "Não é indicador de sucesso/falha — é um resultado do experimento.")
    linhas.append("")
    taxa_geral = pb.get("taxa_geral")
    linhas.append(f"- Taxa geral de suspeita de viés de posição: "
                  f"**{taxa_geral if taxa_geral is not None else '-'}** "
                  f"({pb.get('suspeitos_total', 0)} de {pb.get('total', 0)} combinações)")
    por_juiz = pb.get("por_juiz") or {}
    if por_juiz:
        linhas.append("- Por juiz:")
        linhas.append("")
        linhas.append("| Juiz | Suspeitos | Total | Taxa |")
        linhas.append("|---|---|---|---|")
        for juiz, v in por_juiz.items():
            linhas.append(f"| {juiz} | {v.get('suspeitos', 0)} | {v.get('total', 0)} "
                          f"| {v.get('taxa') if v.get('taxa') is not None else '-'} |")
        linhas.append("")
    if pb.get("detalhe"):
        linhas.append("| Disciplina | Juiz | Suspeito |")
        linhas.append("|---|---|---|")
        for d in pb["detalhe"]:
            linhas.append(f"| {d['disciplina']} | {d['juiz']} | {d['suspeito_position_bias']} |")
        linhas.append("")

    # 3. Concordância holística
    conc = laaj_consolidado.get("concordancia_holistica") or {}
    pct = conc.get("percentual_concordancia")
    linhas.append("## Concordância holística entre juízes (Passo B)")
    linhas.append("")
    linhas.append(f"- Percentual de concordância: {pct if pct is not None else '-'}")
    linhas.append(f"- Total de disciplinas: {conc.get('total_disciplinas', 0)}")
    linhas.append("")
    if conc.get("detalhe"):
        linhas.append("| Disciplina | Juiz 1 | Juiz 2 | Concordam |")
        linhas.append("|---|---|---|---|")
        for d in conc["detalhe"]:
            linhas.append(f"| {d['disciplina']} | {d['juiz_0']} | {d['juiz_1']} | {d['concordam']} |")
        linhas.append("")

    # 4. Vitórias/empates/derrotas do framework (ferramenta) vs humano
    linhas.append("## Vitórias/Empates/Derrotas do framework vs humano (Passo B)")
    linhas.append("")
    linhas.append("| Juiz | Vitórias (gerado) | Vitórias (humano) | Empates |")
    linhas.append("|---|---|---|---|")
    for juiz, v in (laaj_consolidado.get("vitorias_empates_derrotas") or {}).items():
        vg = v.get("vitorias_gerado")
        vh = v.get("vitorias_humano")
        emp = v.get("empates")
        if vg is None:
            # fallback p/ formato antigo (vitorias=humano, derrotas=gerado)
            vh = v.get("vitorias")
            vg = v.get("derrotas")
            emp = v.get("empates")
        linhas.append(f"| {juiz} | {vg if vg is not None else '-'} | "
                      f"{vh if vh is not None else '-'} | {emp if emp is not None else '-'} |")
    linhas.append("")

    # 5. Padrão bruto de votos por disciplina/juiz (Passo B)
    linhas.append("## Padrão bruto de votos por disciplina/juiz (Passo B)")
    linhas.append("")
    linhas.append("| Disciplina | Juiz | Padrão | Votos (4 exec.) | Preferência |")
    linhas.append("|---|---|---|---|---|")
    for slug in disciplinas:
        hol = laaj_por_disciplina.get(slug, {}).get("holistico", {})
        for juiz, g in (hol.get("juizes") or {}).items():
            padrao = g.get("padrao_votos", "-")
            vencedor = g.get("vencedor_padrao_votos", "")
            votos = "; ".join(g.get("votos_traduzidos", []))
            linhas.append(
                f"| {slug} | {juiz} | {padrao} {vencedor} | {votos} | "
                f"{g.get('preferencia_final')} |"
            )
    linhas.append("")

    return "\n".join(linhas)


def relatorio_consolidado(disciplinas: List[str], dados: Dict[str, Dict]) -> str:
    """dados: {slug: {'humano': resumo, 'ferramenta': resumo, 'tpt': segundos}}"""
    linhas = [
        "# Relatório Consolidado - Comparativo Humano vs Ferramenta",
        "",
        f"Gerado em: {datetime.now().isoformat()}",
        "",
        "| Disciplina | SCI-H | SCI-F | WD-H | WD-F | SVR-H | SVR-F | Cobert-H | Cobert-F | TPT(s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for slug in disciplinas:
        d = dados.get(slug, {})
        rh = (d.get("humano") or {}).get("resumo_geral", {})
        rf = (d.get("ferramenta") or {}).get("resumo_geral", {})
        tpt = d.get("tpt")
        def _v(dic, chave, default):
            if not dic:
                return default
            val = dic.get(chave)
            return default if val is None else val
        linhas.append(
            f"| {slug} | {_v(rh, 'sci', 0):.3f} | {_v(rf, 'sci', 0):.3f} | "
            f"{_v(rh, 'wd', 1):.3f} | {_v(rf, 'wd', 1):.3f} | "
            f"{_v(rh, 'svr', 0):.3f} | {_v(rf, 'svr', 0):.3f} | "
            f"{_v(rh, 'cobertura', 0):.3f} | {_v(rf, 'cobertura', 0):.3f} | "
            f"{tpt if tpt is not None else '-'} |"
        )
    linhas.append("")

    return "\n".join(linhas)
