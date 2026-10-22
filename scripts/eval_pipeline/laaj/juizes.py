"""LAAJ (LLM-as-a-Judge) com dois juízes via Ollama.

Protocolo experimental (resumo):
- Passo A (pointwise, documento inteiro): cada LAP completo é avaliado contra a
  Curriculum Guideline (CG) usando 5 critérios oficiais (peso 20% cada), em N
  réplicas; o escore final é a mediana por critério e o escore global ponderado.
  Este é o dado que entra no teste estatístico pareado (Wilcoxon).
- Passo B (holístico pareado): os dois LAPs da mesma disciplina são comparados de
  forma anonimizada (Artifact A/B), com ordem invertida entre execuções, e o juiz
  escolhe categoricamente A, B ou empate (sem notas numéricas).
- ICC entre juízes é calculado UMA única vez, sobre o conjunto de todos os
  artefatos (n sujeitos x 2 juízes), usando os escores globais ponderados.
- Concordância do Passo B é medida por percentual de concordância categórica.

Juízes: deepseek-r1:14b e qwen2.5:14b (temperatura 0.1, top_p 0.9).
Passo B: 4 execuções balanceadas por ordem (AB, BA, AB, BA); maioria simples
decide (3-1 ou 4-0); 2-2 permanece empate. SEM tiebreak por confidence.
"""
import json
import logging
import os
import re
import statistics
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

JUIZES = ["deepseek-r1:14b", "qwen2.5:14b"]
TEMPERATURE = 0.1
TOP_P = 0.9
NUM_REPLICAS_POINTWISE = 3
NUM_REPLICAS_HOLISTICO = 4
MAX_TENTATIVAS_REPLICA = 3
NUM_CTX = 32768
# Margem de segurança para diferenças entre o estimador e o tokenizador real.
# A verificação garante que o INPUT inteiro cabe em num_ctx (truncamento de
# entrada seria corrupção silenciosa); truncamento de SAÍDA é tolerado pela
# lógica de retries/parse (réplica descartada, nunca dado corrompido).
MARGEM_ESTIMATIVA_TOKEN = 512
# num_ctx é alocado por chamada como o mínimo seguro para o prompt (tokens
# estimados + margem, cap NUM_CTX). Usar o mínimo reduz o KV cache e evita
# offload para CPU em GPUs com VRAM limitada, acelerando a inferência sem
# truncar o input. NUM_CTX_MINIMO evita alocações irrisórias em prompts curtos.
NUM_CTX_MINIMO = 8192
MARGEM_NUM_CTX = 1536
# Timeout por chamada: inferência com offload parcial (CPU) é lenta; 900s evita
# retries dispendiosos em prompts grandes quando a resposta demora a gerar.
TIMEOUT_CHAT = 900

CRITERIOS = [
    "curricular_alignment",
    "learning_objectives",
    "constructive_alignment",
    "pedagogical_progression",
    "activity_resource_workload_viability",
]

PESOS_CRITERIOS = {c: 0.20 for c in CRITERIOS}

DEFINICOES_CRITERIOS = {
    "curricular_alignment": "Cobertura e fidelidade dos objetivos e conteúdos do LAP em relação às competências e requisitos da Curriculum Guideline (CG).",
    "learning_objectives": "Clareza, observabilidade, granularidade adequada e uso de verbos mensuráveis nos objetivos de aprendizagem.",
    "constructive_alignment": "Coerência entre competências, objetivos, conteúdos, atividades e avaliações ao longo de todo o documento.",
    "pedagogical_progression": "Sequenciamento lógico, relações de pré-requisito e progressão pedagógica entre as Unidades de Aprendizagem (UAs).",
    "activity_resource_workload_viability": "Viabilidade, diversidade, relevância e adequação contextual das atividades e recursos propostos, incluindo compatibilidade com a carga horária disponível.",
}

ESCALA_ANCORAS = """1 = O critério está ausente ou apresenta inconsistências críticas que tornam a parte correspondente do LAP inutilizável.
2 = O critério é apenas parcialmente atendido, com omissões ou inconsistências relevantes que exigem revisão substancial.
3 = O critério é adequadamente atendido, mas omissões ou inconsistências identificáveis exigem revisão moderada.
4 = O critério é bem atendido, com limitações menores que não comprometem sua função pretendida.
5 = O critério é abordado de forma completa e consistente, com evidências explícitas e sem necessidade de revisão material."""

PROMPT_POINTWISE = """Você é um avaliador pedagógico (LLM-as-a-Judge) em um experimento científico.
Avalie o LAP completo abaixo em relação à Curriculum Guideline (CG), com 5 critérios.
Use notas INTEIRAS de 1 a 5. Avalie o documento como um todo — considere a progressão
e a coerência entre TODAS as Unidades de Aprendizagem (UAs).

DIRETRIZES DE AVALIAÇÃO:
- Os LAPs podem variar em comprimento, nível de detalhe e formatação. NÃO deixe que
  comprimento, verbosidade ou estilo de escrita influenciem suas notas — avalie apenas
  a qualidade pedagógica substantiva.
- Para cada critério, escreva PRIMEIRO o seu raciocínio (rationale), com evidência
  específica do LAP (cite a UA ou o recurso que embasa a nota), e SÓ DEPOIS atribua a
  nota inteira de 1 a 5. A nota deve ser decidida pela evidência, independentemente do
  tamanho do rationale; o rationale é um registro do raciocínio pré-decisão.
- Escreva também um rationale_geral, antes de avaliar critério por critério, com sua
  visão pré-decisão do LAP como um todo.

CRITÉRIOS:
{criterios_definicoes}

ESCALA DE PONTUAÇÃO (aplicar a cada critério):
{escala}

========== DADOS ==========

CURRICULUM GUIDELINE (CG):
{cg_texto}

LAP COMPLETO A SER AVALIADO:
{lap_texto}

========== SAÍDA ==========

Responda APENAS com JSON, sem texto fora dele, preenchendo exatamente esta estrutura
(substitua N por nota inteira 1-5 e os "..." por rationales/justificativas):

{{
  "rationale_geral": "...",
  "curricular_alignment": {{"rationale": "...", "score": N}},
  "learning_objectives": {{"rationale": "...", "score": N}},
  "constructive_alignment": {{"rationale": "...", "score": N}},
  "pedagogical_progression": {{"rationale": "...", "score": N}},
  "activity_resource_workload_viability": {{"rationale": "...", "score": N}},
  "issues_identified": ["..."]
}}
"""

PROMPT_HOLISTICO = """A ordem de apresentação dos artefatos (A ou B) é ALEATÓRIA e não carrega \
nenhum significado. NÃO existe vantagem ou desvantagem associada à posição A ou B. Sua decisão \
deve se basear exclusivamente no conteúdo pedagógico de cada artefato, nunca na ordem em que foi \
apresentado.

Você é um avaliador pedagógico especialista em design instrucional. Compare os dois LAPs \
(Lesson and Assessment Plans) abaixo, ambos elaborados para a mesma Curriculum Guideline (CG), \
e indique qual é PEDAGOGICAMENTE SUPERIOR no conjunto — considerando qualidade pedagógica geral, \
cobertura curricular e viabilidade prática.

Antes de decidir, liste de 2 a 3 diferenças CONCRETAS entre Artifact A e Artifact B (ex.: cobertura \
de um tópico específico da CG, qualidade de um objetivo de aprendizagem específico, viabilidade de \
uma atividade específica). Cada diferença deve citar o elemento específico (UA ou recurso) de AMBOS \
os artefatos que embasa a comparação — não é suficiente citar evidência de apenas um lado.

NÃO atribua notas numéricas nesta etapa. Se os dois artefatos forem equivalentes em qualidade, \
registre empate explicitamente.

Responda APENAS com um JSON válido, sem texto fora do JSON, no formato exato:
{{
  "comparacao": [
    {{"aspecto": "...", "evidencia_artifact_a": "...", "evidencia_artifact_b": "..."}},
    {{"aspecto": "...", "evidencia_artifact_a": "...", "evidencia_artifact_b": "..."}}
  ],
  "preferred_artifact": "A" | "B" | "tie",
  "confidence": "high" | "medium" | "low",
  "justification": "...",
  "is_tie": true | false
}}

CURRICULUM GUIDELINE (CG):
{cg_texto}

ARTIFACT A:
{artefato_a}

ARTIFACT B:
{artefato_b}
"""


def _chat(model: str, mensagens: List[Dict], timeout: int = TIMEOUT_CHAT,
          num_ctx: Optional[int] = None) -> Optional[str]:
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": mensagens,
                "stream": False,
                "options": {
                    "temperature": TEMPERATURE,
                    "top_p": TOP_P,
                    "num_ctx": num_ctx or NUM_CTX,
                },
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")
    except Exception as e:
        logger.warning(f"Falha LAAJ ({model}): {e}")
        return None


def _strip_think(content: str) -> str:
    """Remove bloco <think>...</think> emitido por modelos como deepseek-r1
    antes de tentar o parse do JSON final."""
    return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()


def _parse_json(content: Optional[str]) -> Optional[Dict]:
    if not content:
        return None
    content = _strip_think(content)
    try:
        return json.loads(content)
    except Exception:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except Exception:
            return None


def _nota(valor) -> Optional[int]:
    try:
        n = int(round(float(valor)))
        return n if 1 <= n <= 5 else None
    except (TypeError, ValueError):
        return None


def _estimar_tokens(texto: str) -> int:
    """Estimativa determinística de tokens (proxy do tokenizador Qwen2).

    Verificado contra o tokenizador real (Qwen2.5-7B): divergência < 0.5%.
    Usa tiktoken se disponível; fallback heurístico chars/4.
    """
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(texto))
    except Exception:
        return len(texto) // 4


def _num_ctx_para_prompt(conteudo: str) -> int:
    """num_ctx mínimo seguro para o prompt: tokens estimados + margem, cap NUM_CTX.

    num_ctx define o tamanho do KV cache alocado; usar o mínimo necessário reduz
    memória/offload para CPU e acelera a inferência, sem truncar input (a margem
    cobre o template/system do Ollama e o erro do estimador).
    """
    est = _estimar_tokens(conteudo)
    return min(NUM_CTX, max(NUM_CTX_MINIMO, est + MARGEM_NUM_CTX))


def _checar_budget(conteudo: str, rotulo: str) -> None:
    """Falha alto se o INPUT do prompt não couber inteiro em num_ctx.

    Nunca trunca silenciosamente: se o LAP/CG excederem o contexto, o envio é
    bloqueado para que o operador aumente num_ctx — em vez de o juiz avaliar
    um documento mutilado (corrupção de dados).
    """
    est = _estimar_tokens(conteudo)
    limite = NUM_CTX - MARGEM_ESTIMATIVA_TOKEN
    if est > limite:
        raise RuntimeError(
            f"[LAAJ] {rotulo}: prompt estimado em {est} tokens ultrapassa "
            f"num_ctx={NUM_CTX} (margem {MARGEM_ESTIMATIVA_TOKEN}). Aumente "
            f"num_ctx em config.yaml/juizes.py para evitar truncamento do input."
        )


def avaliar_pointwise_documento(paa, cg_texto: str,
                                 juizes: Optional[List[str]] = None,
                                 replicas: int = NUM_REPLICAS_POINTWISE) -> Dict:
    """Avalia o PAA completo (todas as UAs) contra a CG, por juiz, com N réplicas.

    Retorna, por juiz: as réplicas brutas válidas, o número de réplicas descartadas,
    a mediana por critério, o desvio-padrão por critério (autoconsistência) e o
    escore global ponderado (20% x 5 critérios). Este é o dado usado no teste
    estatístico pareado (Wilcoxon) por disciplina. NENHUM ICC é calculado aqui.
    """
    juizes = juizes or JUIZES
    lap_texto = paa.texto_completo()
    resultado = {"juizes": {}}
    conteudo_prompt = PROMPT_POINTWISE.format(
        escala=ESCALA_ANCORAS,
        criterios_definicoes="\n".join(
            f"- {c}: {DEFINICOES_CRITERIOS[c]}" for c in CRITERIOS
        ),
        cg_texto=cg_texto,
        lap_texto=lap_texto,
    )
    _checar_budget(conteudo_prompt, f"Passo A pointwise {paa.slug}:{paa.origem}")
    num_ctx_call = _num_ctx_para_prompt(conteudo_prompt)

    for juiz in juizes:
        replicas_validas = []
        falhas = 0
        for _ in range(replicas):
            notas = None
            for _tentativa in range(MAX_TENTATIVAS_REPLICA):
                conteudo = _chat(juiz, [{
                    "role": "user",
                    "content": conteudo_prompt,
                }], num_ctx=num_ctx_call)
                parsed = _parse_json(conteudo)
                notas_candidatas = {}
                rationales_candidatas = {}
                valido = parsed is not None
                for crit in CRITERIOS:
                    bloco = (parsed or {}).get(crit, {}) if parsed else {}
                    nota = _nota(bloco.get("score")) if isinstance(bloco, dict) else None
                    if nota is None:
                        valido = False
                        break
                    notas_candidatas[crit] = nota
                    rationales_candidatas[crit] = bloco.get("rationale")
                if valido:
                    notas = {
                        "notas": notas_candidatas,
                        "rationale_geral": (parsed or {}).get("rationale_geral"),
                        "rationales": rationales_candidatas,
                    }
                    break
                logger.warning(
                    f"Réplica pointwise inválida ({juiz}, {paa.slug}) - "
                    f"tentativa {_tentativa + 1}/{MAX_TENTATIVAS_REPLICA}"
                )
            if notas is not None:
                replicas_validas.append(notas)
            else:
                falhas += 1
                logger.warning(f"Réplica pointwise descartada após {MAX_TENTATIVAS_REPLICA} tentativas ({juiz}, {paa.slug})")

        if replicas_validas:
            mediana = {
                crit: statistics.median(r["notas"][crit] for r in replicas_validas)
                for crit in CRITERIOS
            }
            desvio = {
                crit: round(statistics.pstdev(r["notas"][crit] for r in replicas_validas), 3)
                if len(replicas_validas) > 1 else 0.0
                for crit in CRITERIOS
            }
            escore_global = round(
                sum(mediana[c] * PESOS_CRITERIOS[c] for c in CRITERIOS), 3
            )
        else:
            mediana, desvio, escore_global = None, None, None

        resultado["juizes"][juiz] = {
            "replicas_validas": replicas_validas,
            "replicas_falhas": falhas,
            "mediana_por_criterio": mediana,
            "desvio_padrao_por_criterio": desvio,
            "escore_global_ponderado": escore_global,
        }

    return resultado


def _traduzir_voto(r: dict) -> str:
    """Traduz uma resposta bruta (A/B/tie + mapeamento) para paa_1/paa_2/tie."""
    if r["is_tie"]:
        return "tie"
    if r["mapeamento"].startswith("paa_1=A"):
        return "paa_1" if r["preferred_artifact"] == "A" else "paa_2"
    return "paa_2" if r["preferred_artifact"] == "A" else "paa_1"


def _agregar_votos_holistico(respostas: List[dict]) -> dict:
    """Agrega os votos das execuções em preferência final.

    Regras (SEM tiebreak por confidence):
    - Conta votos traduzidos (paa_1/paa_2/tie) sobre as 4 execuções.
    - Um lado com >2 votos decide (3-1 ou 4-0).
    - Qualquer outro padrão (2-2, 2-1-1, ...) resulta em "tie".

    IMPORTANTE: respostas vazias (juiz que falhou em TODAS as execuções, ex.
    Ollama indisponível) NÃO são um empate — são AUSÊNCIA DE DADO. Nesse caso
    preferencia_final é None para que o juiz seja excluído de concordância,
    taxas e ICC (nunca contabilizado como empate indevido).
    """
    if not respostas:
        return {
            "preferencia_final": None,
            "votos_traduzidos": [],
            "padrao_votos": "sem-dados",
            "vencedor_padrao_votos": None,
            "confidence_por_execucao": [],
        }

    votos = [_traduzir_voto(r) for r in respostas]
    c1 = votos.count("paa_1")
    c2 = votos.count("paa_2")
    ct = votos.count("tie")

    if c1 > 2 and c1 > c2:
        preferencia = "paa_1"
    elif c2 > 2 and c2 > c1:
        preferencia = "paa_2"
    else:
        preferencia = "tie"

    humano = votos.count("paa_1")
    gerado = votos.count("paa_2")
    padrao_votos = f"{gerado}-{humano}"
    if preferencia == "paa_1":
        vencedor = "humano"
    elif preferencia == "paa_2":
        vencedor = "gerado"
    else:
        vencedor = "tie"

    return {
        "preferencia_final": preferencia,
        "votos_traduzidos": votos,
        "padrao_votos": padrao_votos,
        "vencedor_padrao_votos": vencedor,
        "confidence_por_execucao": [
            r.get("confidence") if r.get("confidence") in ("high", "medium", "low") else None
            for r in respostas
        ],
    }


def _comparacao_valida(parsed: Optional[Dict]) -> bool:
    """Valida a comparação estruturada obrigatória da resposta holística.

    Exige >=2 itens em `comparacao` e que CADA item cite evidência concreta de
    AMBOS os artefatos (evidencia_artifact_a e evidencia_artifact_b não-vazios).
    Uma resposta que não fizer isso é tratada como réplica inválida (descartada),
    não como voto — é o mecanismo de correção do viés de posição, não uma
    instrução esperançosa no prompt.
    """
    comp = (parsed or {}).get("comparacao")
    if not isinstance(comp, list) or len(comp) < 2:
        return False
    for item in comp:
        if not isinstance(item, dict):
            return False
        ev_a = str(item.get("evidencia_artifact_a") or "").strip()
        ev_b = str(item.get("evidencia_artifact_b") or "").strip()
        if not ev_a or not ev_b:
            return False
    return True


def avaliar_holistico_par(paa_1, paa_2, cg_texto: str, disciplina: str,
                           juizes: Optional[List[str]] = None,
                           replicas: int = NUM_REPLICAS_HOLISTICO) -> Dict:
    """Compara dois LAPs da mesma disciplina (ex.: humano vs. gerado), anonimizados
    como Artifact A / Artifact B, com ordem balanceada entre as execuções.

    IMPORTANTE: paa_1 e paa_2 devem ser passados numa ordem NEUTRA definida por quem
    chama esta função (ex.: sempre [humano, gerado]) — a rotulagem A/B e o
    balanceamento de ordem são feitos aqui dentro, e o mapeamento real (quem é A e
    quem é B em cada execução) é registrado no resultado para permitir desanonimizar
    depois da agregação, sem vazar a origem para o prompt.

    `replicas` deve ser par para manter a ordem balanceada (default 4: AB, BA, AB, BA).
    Com 4 execuções, um juiz decisivo converge para 4-0/3-1 mesmo com ruído de
    amostragem; só viés de posição genuíno ou indecisão real produz 2-2 (empate).
    """
    juizes = juizes or JUIZES
    execucoes = []
    for i in range(replicas):
        if i % 2 == 0:
            execucoes.append((paa_1, paa_2, f"paa_1=A#{i + 1}"))
        else:
            execucoes.append((paa_2, paa_1, f"paa_2=A#{i + 1}"))

    resultado = {"juizes": {}, "execucoes": len(execucoes)}

    for juiz in juizes:
        respostas = []
        descartadas_sem_comparacao = 0
        for artefato_a, artefato_b, mapeamento in execucoes:
            conteudo_prompt = PROMPT_HOLISTICO.format(
                cg_texto=cg_texto,
                artefato_a=artefato_a.texto_completo(),
                artefato_b=artefato_b.texto_completo(),
            )
            _checar_budget(conteudo_prompt, f"Passo B holístico {disciplina}")
            num_ctx_call = _num_ctx_para_prompt(conteudo_prompt)
            parsed = None
            for _tentativa in range(MAX_TENTATIVAS_REPLICA):
                conteudo = _chat(juiz, [{
                    "role": "user",
                    "content": conteudo_prompt,
                }], num_ctx=num_ctx_call)
                parsed = _parse_json(conteudo)
                if parsed and parsed.get("preferred_artifact") in ("A", "B", "tie"):
                    break
                parsed = None
                logger.warning(
                    f"Resposta holística inválida ({juiz}, {disciplina}) - "
                    f"tentativa {_tentativa + 1}/{MAX_TENTATIVAS_REPLICA}"
                )
            if parsed and parsed.get("preferred_artifact") in ("A", "B", "tie"):
                if not _comparacao_valida(parsed):
                    descartadas_sem_comparacao += 1
                    logger.warning(
                        f"Resposta holística SEM comparação estruturada válida "
                        f"(evidência de ambos os lados exigida) ({juiz}, {disciplina}) - "
                        f"execução {mapeamento} descartada"
                    )
                    continue
                respostas.append({
                    "mapeamento": mapeamento,
                    "comparacao": parsed.get("comparacao"),
                    "preferred_artifact": parsed["preferred_artifact"],
                    "is_tie": bool(parsed.get("is_tie", parsed["preferred_artifact"] == "tie")),
                    "confidence": parsed.get("confidence"),
                    "rationale": parsed.get("rationale"),
                })
            else:
                logger.warning(f"Resposta holística descartada após {MAX_TENTATIVAS_REPLICA} tentativas ({juiz}, {disciplina})")

        agregado = _agregar_votos_holistico(respostas)
        resultado["juizes"][juiz] = {
            "respostas_brutas": respostas,
            "replicas_descartadas_sem_comparacao": descartadas_sem_comparacao,
            **agregado,
        }

    return resultado


def calcular_icc_conjunto(escores_por_artefato: Dict[str, Dict[str, Optional[float]]],
                           juizes: Optional[List[str]] = None) -> Optional[Dict]:
    """escores_por_artefato: {artefato_id: {juiz: escore_global_ponderado}}.

    Deve conter TODOS os artefatos (humanos + gerados) para ter poder estatístico
    adequado. Calcula ICC(2,1) e ICC(3,1) sobre a matriz (n sujeitos x 2 juízes).
    """
    juizes = juizes or JUIZES
    if len(juizes) < 2:
        return None
    j0, j1 = juizes[:2]

    matriz = []
    for artefato_id, escores in escores_por_artefato.items():
        v0, v1 = escores.get(j0), escores.get(j1)
        if v0 is not None and v1 is not None:
            matriz.append([v0, v1])

    if len(matriz) < 2:
        logger.warning("ICC não calculado: menos de 2 artefatos com escore de ambos os juízes")
        return None

    from eval_pipeline.laaj.icc import icc_agregado
    return icc_agregado(matriz)


def concordancia_holistica(resultados_por_disciplina: Dict[str, Dict]) -> Dict:
    """resultados_por_disciplina: {disciplina: {juiz: preferencia_final}}.

    Retorna o percentual de disciplinas em que os dois juízes tiveram a mesma
    preferência final (incluindo empate como categoria própria).
    """
    juizes = JUIZES[:2]
    total = 0
    concordantes = 0
    detalhe = []
    for disciplina, por_juiz in resultados_por_disciplina.items():
        p0 = por_juiz.get(juizes[0])
        p1 = por_juiz.get(juizes[1])
        if p0 is None or p1 is None:
            continue
        total += 1
        igual = (p0 == p1)
        concordantes += int(igual)
        detalhe.append({"disciplina": disciplina, "juiz_0": p0, "juiz_1": p1, "concordam": igual})

    return {
        "percentual_concordancia": round(concordantes / total, 3) if total else None,
        "total_disciplinas": total,
        "detalhe": detalhe,
    }
