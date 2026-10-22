from eval_pipeline.objective_metrics.estrutura import calcular_metricas_objetivas
from eval_pipeline.objective_metrics.conteudo import cobertura_conteudo, alinhamento_objetivos
from eval_pipeline.objective_metrics.planejamento_carga import planejamento_carga


def avaliar_paa(paa, conteudos_cg, alvos):
    """Calcula todas as métricas objetivas de um PAA."""
    metricas = calcular_metricas_objetivas(paa, alvos)
    conteudo = cobertura_conteudo(paa, conteudos_cg)
    objetivos = alinhamento_objetivos(paa)
    carga = planejamento_carga(paa)

    return {
        "estrutura": metricas,
        "conteudo": conteudo,
        "objetivos": objetivos,
        "carga": carga,
        "resumo_geral": {
            "sci": metricas["sci"],
            "wd": metricas["wd"],
            "svr": metricas["svr"],
            "cobertura": conteudo["cobertura_global"],
            "teoricos_ok": objetivos["teoricos_ok"],
            "atividade_ok": objetivos["atividade_ok"],
        },
    }
