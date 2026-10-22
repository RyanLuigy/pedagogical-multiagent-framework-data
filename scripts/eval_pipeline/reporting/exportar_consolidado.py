"""Export consolidado único do LAAJ para análise/gráficos (artigo).

Lê os JSONs brutos individuais salvos em `dir_saida` e produz um único arquivo
plano (`resultado_consolidado.json`) mais dois CSVs:
- resultado_consolidado_passo_a.csv
- resultado_consolidado_passo_b.csv

É uma VIEW DERIVADA dos dados brutos — regenerável a qualquer momento
(`python -m eval_pipeline.reporting.exportar_consolidado`) sem re-rodar os
juízes. Não é a fonte primária dos dados.
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from eval_pipeline.main import carregar_config
from eval_pipeline.laaj.deteccao_position_bias import calcular_taxa_position_bias

_CAMINHO_CONFIG = Path(__file__).resolve().parent.parent / "config.yaml"

_ORIGENS = ["humano", "ferramenta"]
_CRITERIOS = [
    "curricular_alignment",
    "learning_objectives",
    "constructive_alignment",
    "pedagogical_progression",
    "activity_resource_workload_viability",
]


def _ler_json(caminho: Path) -> Optional[dict]:
    if not caminho.exists():
        return None
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def _mtime_iso(caminho: Path) -> str:
    if caminho.exists():
        return datetime.fromtimestamp(caminho.stat().st_mtime).isoformat()
    return datetime.now().isoformat()


def _traduzir_voto(voto: str) -> str:
    return {"paa_1": "humano", "paa_2": "gerado", "tie": "tie"}.get(voto, voto)


def _montar_passo_a(dir_saida: Path, disciplinas: List[str],
                    juizes: List[str]) -> tuple:
    escores = []
    escore_global = []
    for slug in disciplinas:
        for origem in _ORIGENS:
            arquivo = dir_saida / f"laaj_pointwise_{slug}_{origem}.json"
            dados = _ler_json(arquivo)
            if not dados:
                continue
            for juiz in juizes:
                g = dados.get("juizes", {}).get(juiz, {})
                med = g.get("mediana_por_criterio") or {}
                desv = g.get("desvio_padrao_por_criterio") or {}
                n_validas = len(g.get("replicas_validas") or [])
                n_falhas = g.get("replicas_falhas", 0)
                for crit in _CRITERIOS:
                    escores.append({
                        "disciplina": slug,
                        "artefato": origem,
                        "juiz": juiz,
                        "criterio": crit,
                        "mediana": med.get(crit),
                        "desvio_padrao": desv.get(crit),
                        "n_replicas_validas": n_validas,
                        "n_replicas_falhas": n_falhas,
                    })
                escore_global.append({
                    "disciplina": slug,
                    "artefato": origem,
                    "juiz": juiz,
                    "escore_global_ponderado": g.get("escore_global_ponderado"),
                })
    return escores, escore_global


def _montar_passo_b(dir_saida: Path, disciplinas: List[str],
                    juizes: List[str]) -> List[dict]:
    votos = []
    for slug in disciplinas:
        dados = _ler_json(dir_saida / f"laaj_holistico_{slug}.json")
        if not dados:
            continue
        for juiz in juizes:
            g = dados.get("juizes", {}).get(juiz, {})
            traduzidos = [_traduzir_voto(v) for v in g.get("votos_traduzidos", [])]
            votos.append({
                "disciplina": slug,
                "juiz": juiz,
                "padrao_votos": g.get("padrao_votos"),
                "vencedor_padrao_votos": g.get("vencedor_padrao_votos"),
                "preferencia_final": _traduzir_voto(g.get("preferencia_final", "")),
                "votos_individuais": traduzidos,
                "confidence_por_execucao": g.get("confidence_por_execucao") or [],
            })
    return votos


def _taxas_vitoria(laaj_consolidado: dict, juizes: List[str]) -> dict:
    por_juiz = {}
    hol = laaj_consolidado.get("resultados_holistico_por_disciplina") or {}
    for juiz in juizes:
        vh = vg = emp = 0
        for pref in hol.values():
            p = pref.get(juiz)
            if p == "paa_1":
                vh += 1
            elif p == "paa_2":
                vg += 1
            elif p == "tie":
                emp += 1
        por_juiz[juiz] = {
            "vitorias_gerado": vg,
            "vitorias_humano": vh,
            "empates": emp,
        }
    return {"por_juiz": por_juiz}


def _montar_matriz_para_icc(passo_a_escores: List[dict],
                            juizes: List[str]) -> List[dict]:
    """Pivô de passo_a_escores para a matriz de entrada do ICC externo.

    linha = artefato_id (disciplina:origem) x criterio, uma coluna por juiz
    (valor = mediana). Nenhuma transformação estatística — só reorganização,
    para o ICC ser recalculado fora do pipeline (seção de escopo).
    """
    matriz = {}
    for e in passo_a_escores:
        chave = (f"{e['disciplina']}:{e['artefato']}", e["criterio"])
        matriz.setdefault(chave, {})[e["juiz"]] = e.get("mediana")
    linhas = []
    for (artefato_id, criterio), por_juiz in sorted(matriz.items()):
        linha = {"artefato_id": artefato_id, "criterio": criterio}
        for juiz in juizes:
            linha[juiz] = por_juiz.get(juiz)
        linhas.append(linha)
    return linhas


def _montar_position_bias(dir_saida: Path, disciplinas: List[str],
                          juizes: List[str]) -> dict:
    """Recomputa a taxa de viés de posição a partir dos JSONs holísticos.

    Usa votos_traduzidos (rótulos paa_1/paa_2 na ordem das execuções AB, BA,
    AB, BA) — os votos_individuais traduzidos do export não servem porque
    perderiam o rótulo de posição. Mesma função usada pelo main.py.
    """
    resultados_passo_b = {}
    for slug in disciplinas:
        dados = _ler_json(dir_saida / f"laaj_holistico_{slug}.json")
        if not dados:
            continue
        por_juiz = {}
        for juiz in juizes:
            g = dados.get("juizes", {}).get(juiz, {})
            por_juiz[juiz] = {"votos_traduzidos": g.get("votos_traduzidos", [])}
        resultados_passo_b[slug] = por_juiz
    return calcular_taxa_position_bias(resultados_passo_b)


def exportar_consolidado(cfg: dict) -> dict:
    dir_saida = Path(cfg["caminhos"]["dir_saida"])
    disciplinas = cfg["disciplinas"]
    juizes = cfg["llm"]["juizes"]
    n_planejado = cfg.get("opcoes", {}).get("n_disciplinas_planejado", len(disciplinas))

    passo_a_escores, passo_a_escore_global = _montar_passo_a(
        dir_saida, disciplinas, juizes)
    passo_b_votos = _montar_passo_b(dir_saida, disciplinas, juizes)
    matriz_para_icc = _montar_matriz_para_icc(passo_a_escores, juizes)
    position_bias = _montar_position_bias(dir_saida, disciplinas, juizes)

    consol = _ler_json(dir_saida / "laaj_consolidado.json") or {}
    log_san = _ler_json(dir_saida / "laaj_log_sanitizacao.json") or {}
    log_esc = _ler_json(dir_saida / "laaj_log_escopo_uas.json") or {}
    log_norm = _ler_json(dir_saida / "laaj_log_normalizacao.json") or {}

    n_avaliadas = sum(
        1 for s in disciplinas
        if (dir_saida / f"laaj_holistico_{s}.json").exists()
    )

    resultado = {
        "metadados": {
            "n_disciplinas_planejado": n_planejado,
            "n_disciplinas_avaliadas": n_avaliadas,
            "juizes": juizes,
            "data_execucao": _mtime_iso(dir_saida / "laaj_consolidado.json"),
        },
        "passo_a_escores": passo_a_escores,
        "passo_a_escore_global": passo_a_escore_global,
        "matriz_escores_para_icc": matriz_para_icc,
        "passo_b_votos": passo_b_votos,
        "position_bias_passo_b": position_bias,
        "concordancia_juizes": {
            "concordancia_holistica_percentual": (
                consol.get("concordancia_holistica") or {}
            ).get("percentual_concordancia"),
        },
        "taxas_vitoria_passo_b": _taxas_vitoria(consol, juizes),
        "sanitizacao_e_escopo": {
            "marcadores_removidos_total": log_san.get("total_marcadores_removidos", 0),
            "uas_fora_de_escopo_removidas_total": log_esc.get(
                "total_uas_fora_de_escopo_removidas", 0),
            "normalizacao": log_norm.get("resumo") or {},
            "ver_detalhe_em": [
                str(dir_saida / "laaj_log_sanitizacao.json"),
                str(dir_saida / "laaj_log_escopo_uas.json"),
                str(dir_saida / "laaj_log_normalizacao.json"),
            ],
        },
    }

    with open(dir_saida / "resultado_consolidado.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2, default=str)

    _escrever_csv(dir_saida / "resultado_consolidado_passo_a.csv", passo_a_escores)
    _escrever_csv(dir_saida / "resultado_consolidado_passo_b.csv",
                  _aplanar_passo_b(passo_b_votos))

    return resultado


def _aplanar_passo_b(votos: List[dict]) -> List[dict]:
    planos = []
    for v in votos:
        copia = dict(v)
        copia["votos_individuais"] = "; ".join(v.get("votos_individuais", []))
        copia["confidence_por_execucao"] = "; ".join(
            str(c) for c in (v.get("confidence_por_execucao") or []))
        planos.append(copia)
    return planos


def _escrever_csv(caminho: Path, registros: List[dict]) -> None:
    if not registros:
        return
    campos = list(registros[0].keys())
    with open(caminho, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(registros)


def main() -> int:
    import sys as _sys
    caminho_config = Path(_sys.argv[1]) if len(_sys.argv) > 1 else _CAMINHO_CONFIG
    cfg = carregar_config(caminho_config)
    exportar_consolidado(cfg)
    dir_saida = Path(cfg["caminhos"]["dir_saida"])
    print(f"Export consolidado gerado em {dir_saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
