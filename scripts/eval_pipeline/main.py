"""Pipeline 3 - Avaliação das PAAs (humano vs ferramenta).

Uso:
    python -m eval_pipeline.main [--only-objetivas] [--sem-llm] [--slug DISCIPLINA]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("eval_pipeline")

try:
    import requests
except ImportError:
    requests = None


def carregar_config(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _ollama_disponivel(base_url: str) -> bool:
    if requests is None:
        return False
    try:
        r = requests.get(f"{base_url}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def _filtrar_disciplinas(cfg: dict, slug: str | None) -> list:
    disciplinas = cfg["disciplinas"]
    if not slug:
        return disciplinas
    if slug not in disciplinas:
        raise SystemExit(f"Disciplina '{slug}' não está no config.yaml. Disponível: {disciplinas}")
    return [slug]


def _carregar_paa_laaj(caminho, slug: str, origem: str, eh_humano: bool):
    """Carrega um PAA para o LAAJ aplicando as garantias de integridade,
    nesta ordem e UMA única vez por PAA:

    1. normalização de referências G/ObjN nos objetivos (no dado bruto);
    2. corte de UAs acima de UA8 por rótulo (APENAS no PAA humano);
    3. sanitização de marcadores de processo interno (in-place);
    4. validação de ausência de marcadores residuais (bloqueia envio).

    Retorna (paa, logs) com logs = {"escopo", "normalizacao", "sanitizacao"}.
    Levanta ValueError se a sanitização falhar.
    """
    from eval_pipeline.laaj.normalizacao import normalizar_referencias_objetivos
    from eval_pipeline.laaj.escopo import limitar_uas_paa_humano
    from eval_pipeline.laaj.sanitizacao import sanitizar_paa, validar_ausencia_de_marcadores
    from eval_pipeline.loaders.paa_loader import carregar_paa_de_dados

    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    log_normalizacao = normalizar_referencias_objetivos(dados, slug, origem)
    paa = carregar_paa_de_dados(dados, slug, origem,
                                descartar_ua_extra=not eh_humano)
    log_escopo = []
    if eh_humano:
        log_escopo = limitar_uas_paa_humano(paa)
    log_sanitizacao = sanitizar_paa(paa)
    residuais = validar_ausencia_de_marcadores(paa)
    if residuais:
        raise ValueError(
            f"Sanitização falhou para {slug} ({origem}): padrões residuais "
            f"{residuais}. LAP NÃO enviado ao LAAJ."
        )
    return paa, {
        "escopo": log_escopo,
        "normalizacao": log_normalizacao,
        "sanitizacao": log_sanitizacao,
    }


def main():
    parser = argparse.ArgumentParser(description="Pipeline 3 - Avaliação")
    parser.add_argument("--sug", default="eval_pipeline/config.yaml")
    parser.add_argument("--only-objetivas", action="store_true",
                        help="Calcula apenas métricas objetivas (sem LAAJ)")
    parser.add_argument("--sem-llm", action="store_true",
                        help="Pula LAAJ mesmo se o Ollama estiver disponível")
    parser.add_argument("--slug", default=None,
                        help="Roda apenas uma disciplina (ex.: banco_de_dados) - útil para sanidade")
    args = parser.parse_args()

    cfg = carregar_config(Path(args.sug))
    paths = cfg["caminhos"]
    dir_raiz = Path(paths["dir_raiz"])
    dir_saida = Path(paths["dir_saida"])
    dir_saida.mkdir(parents=True, exist_ok=True)

    disciplinas = _filtrar_disciplinas(cfg, args.slug)

    from eval_pipeline.loaders.paa_loader import carregar_paa, minutagem_alvo_por_ua
    from eval_pipeline.loaders.cg_loader import carregar_cg
    from eval_pipeline.objective_metrics import avaliar_paa

    usar_laaj = cfg["opcoes"]["usar_laaj"] and not args.only_objetivas and not args.sem_llm
    base_url = cfg["llm"]["base_url"]
    if usar_laaj:
        usar_laaj = _ollama_disponivel(base_url)
        if not usar_laaj:
            logger.warning("Ollama indisponível - LAAJ será pulado.")

    resultados = {}
    for slug in disciplinas:
        dir_humano = dir_raiz / paths["subdir_humano"] / slug
        dir_ferramenta = dir_raiz / paths["subdir_ferramenta"] / slug
        arquivo_cg = dir_ferramenta / paths["arquivo_cg"]

        if not arquivo_cg.exists():
            logger.warning(f"{slug}: cg.json ausente em {dir_ferramenta} - pulando CG")
            cg = {"conteudos_gerais": [], "ch_total": 60.0}
        else:
            cg = carregar_cg(arquivo_cg)

        alvos = minutagem_alvo_por_ua(cg.get("ch_total", 60.0))
        res_ferramenta = None
        res_humano = None

        if (dir_ferramenta / paths["arquivo_ferramenta"]).exists():
            paa_f = carregar_paa(dir_ferramenta / paths["arquivo_ferramenta"], slug, "ferramenta")
            res_ferramenta = avaliar_paa(paa_f, cg["conteudos_gerais"], alvos)
        else:
            logger.warning(f"{slug}: ciclo_03.json ausente em {dir_ferramenta}")

        if (dir_humano / paths["arquivo_humano"]).exists():
            paa_h = carregar_paa(dir_humano / paths["arquivo_humano"], slug, "humano")
            res_humano = avaliar_paa(paa_h, cg["conteudos_gerais"], alvos)
        else:
            logger.warning(f"{slug}: paa_humana.json ausente em {dir_humano}")

        tpt = None
        meta_path = dir_ferramenta / "metadata.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                tpt = meta.get("duracao_segundos")
            except Exception:
                pass

        resultados[slug] = {
            "humano": res_humano,
            "ferramenta": res_ferramenta,
            "tpt": tpt,
        }

    # LAAJ: Passo A (pointwise, documento inteiro) + Passo B (holístico pareado)
    laaj_por_disciplina = {}
    if usar_laaj:
        from eval_pipeline.laaj.juizes import (
            avaliar_pointwise_documento,
            avaliar_holistico_par,
            concordancia_holistica,
        )
        from eval_pipeline.laaj.deteccao_position_bias import calcular_taxa_position_bias
        from eval_pipeline.loaders.cg_loader import texto_completo_cg

        # --- Passo A: ambos os artefatos (humano e ferramenta) contra a CG ---
        escores_por_artefato = {}
        cgs_texto = {}
        paas = {}
        aud_escopo = {}
        aud_normalizacao = []
        aud_sanitizacao = []

        for slug in disciplinas:
            dir_humano = dir_raiz / paths["subdir_humano"] / slug
            dir_ferramenta = dir_raiz / paths["subdir_ferramenta"] / slug
            arquivo_cg = dir_ferramenta / paths["arquivo_cg"]

            if not arquivo_cg.exists():
                logger.warning(f"{slug}: cg.json ausente - pulando LAAJ")
                continue

            with open(arquivo_cg, encoding="utf-8") as f:
                dados_cg = json.load(f)
            cgs_texto[slug] = texto_completo_cg(dados_cg)

            artefatos = {}
            if (dir_humano / paths["arquivo_humano"]).exists():
                paa_h, logs_h = _carregar_paa_laaj(
                    dir_humano / paths["arquivo_humano"], slug, "humano", True)
                artefatos["humano"] = paa_h
                aud_escopo[slug] = logs_h["escopo"]
                aud_normalizacao += logs_h["normalizacao"]
                aud_sanitizacao += logs_h["sanitizacao"]
            if (dir_ferramenta / paths["arquivo_ferramenta"]).exists():
                paa_f, logs_f = _carregar_paa_laaj(
                    dir_ferramenta / paths["arquivo_ferramenta"], slug, "ferramenta", False)
                artefatos["ferramenta"] = paa_f
                aud_escopo.setdefault(slug, [])
                aud_normalizacao += logs_f["normalizacao"]
                aud_sanitizacao += logs_f["sanitizacao"]

            paas[slug] = artefatos

        # --- Execução em FASES POR JUIZ: cada modelo é carregado UMA única vez
        # (juiz 1 faz todos os Passos A e B; depois juiz 2), evitando recarregar
        # modelos de ~9GB a cada troca de artefato. A ordem de execução não muda
        # os resultados — apenas a ordem das chamadas LLM. ---
        juizes = cfg["llm"]["juizes"]
        replicas_holistico = cfg["llm"].get("replicas_holistico", 4)
        ponto_bruto = {
            slug: {origem: {} for origem in ("humano", "ferramenta")}
            for slug in disciplinas
        }
        hol_bruto = {}

        for juiz in juizes:
            logger.info(f"[LAAJ] FASE Passo A: juiz {juiz} (todos os artefatos)")
            for slug in disciplinas:
                artefatos = paas.get(slug, {})
                for origem, paa in artefatos.items():
                    artefato_id = f"{slug}:{origem}"
                    logger.info(f"LAAJ Passo A (pointwise): {artefato_id} [{juiz}]")
                    res = avaliar_pointwise_documento(
                        paa, cgs_texto[slug], juizes=[juiz])
                    dados_juiz = res["juizes"][juiz]
                    ponto_bruto[slug][origem][juiz] = dados_juiz
                    escores_por_artefato.setdefault(artefato_id, {})[juiz] = \
                        dados_juiz["escore_global_ponderado"]

            logger.info(f"[LAAJ] FASE Passo B: juiz {juiz} (todos os pares)")
            for slug in disciplinas:
                artefatos = paas.get(slug, {})
                if "humano" not in artefatos or "ferramenta" not in artefatos:
                    continue
                logger.info(f"LAAJ Passo B (holístico pareado): {slug} [{juiz}]")
                hol = avaliar_holistico_par(
                    artefatos["humano"], artefatos["ferramenta"],
                    cg_texto=cgs_texto[slug], disciplina=slug,
                    juizes=[juiz], replicas=replicas_holistico,
                )
                hol_bruto.setdefault(slug, {})[juiz] = hol["juizes"][juiz]

        # --- Montagem e gravação dos resultados por artefato/disciplina ---
        resultados_holistico = {}
        for slug in disciplinas:
            por_origem = ponto_bruto.get(slug, {})
            if por_origem:
                ponto = {}
                for origem, por_juiz in por_origem.items():
                    if not por_juiz:
                        continue
                    ponto[origem] = {"juizes": por_juiz}
                    with open(dir_saida / f"laaj_pointwise_{slug}_{origem}.json", "w",
                              encoding="utf-8") as f:
                        json.dump(ponto[origem], f, ensure_ascii=False, indent=2,
                                  default=str)
                if ponto:
                    laaj_por_disciplina[slug] = {"pointwise": ponto}

            hol_por_juiz = hol_bruto.get(slug)
            if hol_por_juiz:
                hol = {"juizes": hol_por_juiz, "execucoes": replicas_holistico}
                laaj_por_disciplina.setdefault(slug, {}).setdefault("holistico", hol)
                resultados_holistico[slug] = {
                    juiz: dados["preferencia_final"]
                    for juiz, dados in hol_por_juiz.items()
                }
                with open(dir_saida / f"laaj_holistico_{slug}.json", "w",
                          encoding="utf-8") as f:
                    json.dump(hol, f, ensure_ascii=False, indent=2, default=str)

        # --- Logs de auditoria (sanitização, escopo de UAs, normalização) ---
        with open(dir_saida / "laaj_log_sanitizacao.json", "w",
                  encoding="utf-8") as f:
            json.dump({
                "ocorrencias": aud_sanitizacao,
                "total_marcadores_removidos": len(aud_sanitizacao),
            }, f, ensure_ascii=False, indent=2, default=str)

        with open(dir_saida / "laaj_log_escopo_uas.json", "w",
                  encoding="utf-8") as f:
            json.dump({
                "por_disciplina": aud_escopo,
                "total_uas_fora_de_escopo_removidas": sum(
                    len(v) for v in aud_escopo.values()),
            }, f, ensure_ascii=False, indent=2, default=str)

        with open(dir_saida / "laaj_log_normalizacao.json", "w",
                  encoding="utf-8") as f:
            json.dump({
                "eventos": aud_normalizacao,
                "resumo": {
                    "referencias_resolvidas": sum(
                        1 for e in aud_normalizacao
                        if e["tipo"] == "referencia_resolvida"),
                    "nao_resolvidas": sum(
                        1 for e in aud_normalizacao
                        if e["tipo"] == "nao_resolvido"),
                    "deduplicadas": sum(
                        1 for e in aud_normalizacao
                        if e["tipo"] == "deduplicado"),
                },
            }, f, ensure_ascii=False, indent=2, default=str)

        # --- Detecção de viés de posição (Passo B): contagem determinística da
        # assinatura "sempre escolhe o rótulo A/B" nas execuções balanceadas.
        # É métrica de robustez do protocolo, reportada seja qual for o valor.
        # NENHUM teste inferencial é executado aqui (ver escopo do pipeline).
        position_bias = calcular_taxa_position_bias(hol_bruto)
        with open(dir_saida / "laaj_position_bias.json", "w",
                  encoding="utf-8") as f:
            json.dump(position_bias, f, ensure_ascii=False, indent=2, default=str)

        conc_hol = concordancia_holistica(resultados_holistico)

        # Taxas de vitória/empate/derrota do framework (ferramenta) vs humano.
        # Rotulagem EXPLÍCITA: paa_2 = vitória do gerado (framework), paa_1 =
        # vitória do humano, tie = empate. (evita a inversão 'vitorias/derrotas'
        # que o rótulo ambíguo antigo permitia.)
        vitorias = {}
        for juiz in cfg["llm"]["juizes"]:
            vh = vg = emp = 0
            for pref in resultados_holistico.values():
                p = pref.get(juiz)
                if p == "paa_1":
                    vh += 1
                elif p == "tie":
                    emp += 1
                elif p == "paa_2":
                    vg += 1
            vitorias[juiz] = {"vitorias_gerado": vg, "vitorias_humano": vh, "empates": emp}

        laaj_consolidado = {
            "escores_globais_ponderados": escores_por_artefato,
            "concordancia_holistica": conc_hol,
            "vitorias_empates_derrotas": vitorias,
            "resultados_holistico_por_disciplina": resultados_holistico,
            "position_bias_passo_b": position_bias,
        }
        with open(dir_saida / "laaj_consolidado.json", "w", encoding="utf-8") as f:
            json.dump(laaj_consolidado, f, ensure_ascii=False, indent=2, default=str)

        for slug in disciplinas:
            if slug in laaj_por_disciplina:
                with open(dir_saida / f"laaj_{slug}.json", "w", encoding="utf-8") as f:
                    json.dump(laaj_por_disciplina[slug], f, ensure_ascii=False, indent=2, default=str)

    with open(dir_saida / "resultados_objetivas.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)

    # Relatórios
    from eval_pipeline.reporting.relatorio import (
        relatorio_disciplina,
        relatorio_consolidado,
        relatorio_laaj_consolidado,
    )
    for slug in disciplinas:
        rh = resultados[slug]["humano"]
        rf = resultados[slug]["ferramenta"]
        if not rh or not rf:
            continue
        texto = relatorio_disciplina(slug, rh, rf, laaj_por_disciplina.get(slug))
        (dir_saida / f"relatorio_{slug}.md").write_text(texto, encoding="utf-8")

    consolidado = relatorio_consolidado(disciplinas, resultados)
    (dir_saida / "relatorio_consolidado.md").write_text(consolidado, encoding="utf-8")

    if usar_laaj and "laaj_consolidado" in locals():
        laaj_md = relatorio_laaj_consolidado(disciplinas, laaj_consolidado, laaj_por_disciplina)
        (dir_saida / "relatorio_laaj.md").write_text(laaj_md, encoding="utf-8")

    logger.info(f"Concluído! Resultados em {dir_saida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
