"""Cálculo de ICC (Intraclass Correlation Coefficient) via ANOVA com numpy/scipy.

Implementa ICC(2,1) e ICC(3,1) sem depender de pingouin.
"""
import numpy as np
from scipy import stats


def _anova(data: np.ndarray):
    """data: matriz (n sujeitos, k avaliadores). Retorna MS_between, MS_within,
    MS_judges (avaliadores), MS_error (residual), df correspondentes."""
    n, k = data.shape
    total = data.sum()
    n_total = n * k

    soma_total = np.sum(data ** 2)

    soma_sujeitos = np.sum(data.sum(axis=1) ** 2) / k
    soma_juizes = np.sum(data.sum(axis=0) ** 2) / n
    soma_media = total ** 2 / n_total

    ss_total = soma_total - soma_media
    ss_sujeitos = soma_sujeitos - soma_media
    ss_juizes = soma_juizes - soma_media
    ss_residual = ss_total - ss_sujeitos - ss_juizes

    df_sujeitos = n - 1
    df_juizes = k - 1
    df_residual = (n - 1) * (k - 1)
    df_total = n_total - 1

    ms_sujeitos = ss_sujeitos / df_sujeitos
    ms_juizes = ss_juizes / df_juizes
    ms_residual = ss_residual / df_residual

    return {
        "n": n, "k": k,
        "ss_sujeitos": ss_sujeitos, "ss_juizes": ss_juizes, "ss_residual": ss_residual,
        "ms_sujeitos": ms_sujeitos, "ms_juizes": ms_juizes, "ms_residual": ms_residual,
        "df_sujeitos": df_sujeitos, "df_juizes": df_juizes, "df_residual": df_residual,
    }


def icc2_1(data: np.ndarray) -> dict:
    """ICC(2,1) - two-way random effects, single measures (consistência absoluta)."""
    a = _anova(data)
    n, k = a["n"], a["k"]
    ms_s, ms_j, ms_e = a["ms_sujeitos"], a["ms_juizes"], a["ms_residual"]

    numerador = ms_s - ms_e
    denominador = ms_s + (k - 1) * ms_e + k * (ms_j - ms_e) / n
    valor = numerador / denominador if denominador != 0 else 0.0

    # Teste F: variância entre sujeitos significativa?
    f = ms_s / ms_e if ms_e != 0 else float("inf")
    p = stats.f.sf(f, a["df_sujeitos"], a["df_residual"])

    return {"tipo": "ICC(2,1)", "valor": float(valor), "f": float(f), "p": float(p)}


def icc3_1(data: np.ndarray) -> dict:
    """ICC(3,1) - two-way mixed effects, single measures (consistência)."""
    a = _anova(data)
    k = a["k"]
    ms_s, ms_e = a["ms_sujeitos"], a["ms_residual"]

    numerador = ms_s - ms_e
    denominador = ms_s + (k - 1) * ms_e
    valor = numerador / denominador if denominador != 0 else 0.0

    f = ms_s / ms_e if ms_e != 0 else float("inf")
    p = stats.f.sf(f, a["df_sujeitos"], a["df_residual"])

    return {"tipo": "ICC(3,1)", "valor": float(valor), "f": float(f), "p": float(p)}


def icc_agregado(matriz_juizes: list, min_sujeitos_recomendado: int = 10) -> dict:
    """matriz_juizes: lista de listas, linha = sujeito (artefato/UA), coluna = juiz.

    Retorna ICC(2,1) e ICC(3,1) com F e p. Retorna None se não houver dados
    suficientes (menos de 2 sujeitos ou 2 juízes, ou variância nula).
    Se o número de sujeitos for menor que `min_sujeitos_recomendado`, inclui um
    aviso sobre a cautela na interpretação (intervalo de confiança amplo).
    """
    data = np.asarray(matriz_juizes, dtype=float)
    if data.ndim != 2 or data.shape[0] < 2 or data.shape[1] < 2:
        return None
    if data.shape[1] > 2:
        data = data[:, :2]

    if np.all(data == data[0, :]) or np.all(np.std(data, axis=0) == 0):
        return None

    resultado = {"icc2_1": icc2_1(data), "icc3_1": icc3_1(data)}
    if data.shape[0] < min_sujeitos_recomendado:
        resultado["aviso"] = (
            f"Apenas {data.shape[0]} sujeitos; ICC com poucos sujeitos tem "
            "intervalo de confiança amplo e deve ser interpretado com cautela."
        )
    return resultado


def calcular_icc_da_matriz(matriz_escores: list, juizes: list) -> list:
    """Matriz pivô: lista de {artefato_id, criterio, <juiz>: mediana}.

    Retorna um ICC por linha (artefato_id x criterio) que tenha escore dos
    dois juízes. Não é chamado pelo pipeline — é utilitário externo.
    """
    resultados = []
    for linha in matriz_escores:
        j0, j1 = juizes[0], juizes[1]
        v0, v1 = linha.get(j0), linha.get(j1)
        if v0 is None or v1 is None:
            continue
        icc = icc_agregado([[float(v0), float(v1)]])
        if icc is None:
            continue
        resultados.append({
            "artefato_id": linha["artefato_id"],
            "criterio": linha["criterio"],
            **icc,
        })
    return resultados


def main() -> int:
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        description="ICC(2,1)/ICC(3,1) externo sobre o export consolidado. "
                    "NÃO é chamado pelo pipeline — roda manualmente."
    )
    parser.add_argument("--input", required=True,
                        help="Caminho do resultado_consolidado.json")
    parser.add_argument("--criterio", default=None,
                        help="Criterio específico (default: todos + global)")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        dados = json.load(f)
    juizes = dados.get("metadados", {}).get("juizes", [])
    if len(juizes) < 2:
        print("Erro: metadados.juizes precisa ter 2 juízes.", file=sys.stderr)
        return 1

    matriz = dados.get("matriz_escores_para_icc") or []
    criterios = sorted({m["criterio"] for m in matriz})
    if args.criterio:
        criterios = [c for c in criterios if c == args.criterio]

    for crit in criterios:
        linhas = [m for m in matriz if m["criterio"] == crit]
        sujeitos = [[float(m[j]) for j in juizes] for m in linhas
                    if m.get(juizes[0]) is not None and m.get(juizes[1]) is not None]
        if len(sujeitos) < 2:
            print(f"critério {crit}: <2 sujeitos completos — ICC não calculado")
            continue
        icc = icc_agregado(sujeitos)
        if not icc:
            print(f"critério {crit} (n={len(sujeitos)}): variância nula — ICC não definido")
            continue
        print(f"critério {crit} (n={len(sujeitos)}): "
              + "; ".join(f"{v['tipo']}={v['valor']:.3f} (F={v['f']:.2f}, p={v['p']:.4f})"
                          for v in icc.values() if isinstance(v, dict) and "tipo" in v))

    # ICC global a partir do escore global ponderado (passo_a_escore_global)
    globais = dados.get("passo_a_escore_global") or []
    artefatos = {}
    for g in globais:
        artefatos.setdefault(f"{g['disciplina']}:{g['artefato']}", {})[g["juiz"]] = g.get("escore_global_ponderado")
    sujeitos = []
    for _, por_juiz in artefatos.items():
        if por_juiz.get(juizes[0]) is not None and por_juiz.get(juizes[1]) is not None:
            sujeitos.append([float(por_juiz[j]) for j in juizes])
    if len(sujeitos) >= 2:
        icc = icc_agregado(sujeitos)
        if not icc:
            print(f"global (n={len(sujeitos)}): variância nula — ICC não definido")
        else:
            print(f"global (n={len(sujeitos)}): "
                  + "; ".join(f"{v['tipo']}={v['valor']:.3f} (F={v['f']:.2f}, p={v['p']:.4f})"
                              for v in icc.values() if isinstance(v, dict) and "tipo" in v))
    else:
        print("global: <2 artefatos completos — ICC não calculado")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
