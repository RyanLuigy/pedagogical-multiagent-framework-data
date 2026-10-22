import os
import sys

caminho_raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) 
sys.path.insert(0, caminho_raiz)

import time
import json
import pandas as pd
import ollama
import psutil
from datetime import datetime
from rouge_score import rouge_scorer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.agents.agent_03 import AgenteCriadorUnidadesCrewAI
from src.agents.agent_01 import MemoriaVetorialUnica

# Tenta inicializar monitoramento de GPU NVIDIA
try:
    from pynvml import *
    nvmlInit()
    HAS_GPU = True
except:
    HAS_GPU = False

class BenchmarkCriacaoUA1:
    def __init__(self, criador_instancia, disciplina_input, gabarito_json):
        self.criador = criador_instancia
        self.disciplina = disciplina_input
        self.gabarito = gabarito_json
        self.resultados_bench = []
        self.scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)

    def _get_vram(self):
        if HAS_GPU:
            handle = nvmlDeviceGetHandleByIndex(0)
            info = nvmlDeviceGetMemoryInfo(handle)
            return info.used / 1024**2 # MB
        return 0

    def calcular_metricas_qualidade(self, gerado):
        """Compara o JSON gerado com o Gabarito"""
        # 1. Completude (Quantas chaves do gabarito existem no gerado)
        chaves_gabarito = set(self.gabarito.keys())
        chaves_geradas = set(gerado.keys())
        completude = len(chaves_gabarito.intersection(chaves_geradas)) / len(chaves_gabarito)

        # 2. Fidelidade e Relevância (Baseado no conteúdo formativo da UA1)
        texto_gabarito = str(self.gabarito.get('temas', [{}])[0])
        texto_gerado = str(gerado.get('temas', [{}])[0])
        
        rouge_score = self.scorer.score(texto_gabarito, texto_gerado)['rougeL'].fmeasure
        
        # Similaridade de Cosseno (Acurácia Semântica)
        vectorizer = TfidfVectorizer().fit_transform([texto_gabarito, texto_gerado])
        sim_semantica = cosine_similarity(vectorizer)[0][1]

        return {
            "Completude": round(completude, 2),
            "Fidelidade_ROUGE": round(rouge_score, 3),
            "Acuracia_Semantica": round(sim_semantica, 3),
            "Valido_JSON": 1 if gerado else 0
        }

    def rodar_benchmark_completo(self):
        # Lista modelos do Ollama
        modelos = [m['name'] for m in ollama.list()['models']]
        print(f"Iniciando Benchmark em {len(modelos)} modelos...")

        for modelo in modelos:
            print(f"--- 🧪 Testando Modelo: {modelo} ---")
            
            # CONFIGURAÇÃO: Aqui você deve atualizar o modelo no seu objeto criador
            # Exemplo: self.criador.agent.model = f"ollama/{modelo}"
            self.criador(llm_model=modelo) 
            
            vram_inicial = self._get_vram()
            inicio = time.perf_counter()
            
            # Nota: O TTFT em pipelines complexos é o tempo da primeira resposta do primeiro agente.
            # Como o run_geracao_completa_ua1 é síncrono, mediremos a latência total.
            try:
                # EXECUÇÃO DO SEU MÉTODO
                resultado_ua1 = self.criador.run_geracao_completa_ua1(
                    self.disciplina,
                    progress_callback=lambda m, p: None # Silencia o progresso
                )
                
                fim = time.perf_counter()
                latencia = fim - inicio
                vram_final = self._get_vram()
                
                # Cálculo de Métricas Técnicas
                # Em sistemas multi-agente, o throughput médio é total_tokens / tempo
                # Aqui usamos uma estimativa de caracteres/tempo se o token_count não estiver acessível
                throughput_estimado = len(str(resultado_ua1)) / 4 / latencia 

                # Métricas de Qualidade
                qualidade = self.calcular_metricas_qualidade(resultado_ua1)

                self.resultados_bench.append({
                    "Modelo": modelo,
                    "Latencia_s": round(latencia, 2),
                    "VRAM_Consumo_MB": round(vram_final - vram_inicial, 2),
                    "Tokens_s_Estimado": round(throughput_estimado, 2),
                    **qualidade,
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M")
                })
                print(f"✅ Concluído: {latencia:.2f}s | Qualidade: {qualidade['Acuracia_Semantica']}")

            except Exception as e:
                print(f"❌ Falha no modelo {modelo}: {e}")

    def salvar_xlsx(self, nome_arquivo="benchmark_ua1_ollama.xlsx"):
        df = pd.DataFrame(self.resultados_bench)
        df.to_excel(nome_arquivo, index=False)
        print(f"💾 Arquivo salvo: {nome_arquivo}")

# --- COMO USAR ---
# 1. Carregue seu JSON disciplina e Gabarito
# 2. Instancie sua classe original (a que tem o método run_geracao_completa_ua1)
# 3. Rode o benchmark

if __name__ ==  "__main__":
    disciplina_exemplo = {
        "DIRETRIZES DO COMPONENTE CURRICULAR": {
            "COMPONENTE CURRICULAR": "Banco de Dados",
            "CÓDIGO": "EADGRD-ADS-0059",
            "CH TOTAL": "60",
            "CH TEÓRICA": "60",
            "CH PRÁTICA": "0",
            "PERFIL": "Conhecimento",
            "PRÉ-REQUISITOS": "Programação Orientada à Objeto"
        },
        "EMENTA": "Estudo dos sistemas de bancos de dados. Estudos da arquitetura de um SGBD. Compreensão dos principais conceitos relacionados à modelagem de dados. Compreensão sobre transformação entre modelos de dados. Aplicação de técnicas de dependência funcional e normalização na construção de bancos de dados. Estudo sobre álgebra relacional, cálculo relacional e Structured Query Language (SQL). Compreensão sobre linguagem procedural em banco de dados. Compreensão sobre processamento de consultas. Utilização de ferramentas e linguagens procedurais em bancos de dados, para realização de consultas, transações e processamento de dados em geral. Implementação de Bancos de dados Não-Relacionais.",
        "COMPETÊNCIAS": [
            "Desenvolver raciocínio analítico para resolução de problemas.",
            "Desenvolver pensamento crítico e criativo em diferentes contextos e situações.",
            "Liderar, integrar equipes com vistas ao alcance de resultados."
        ],
        "CRITÉRIOS DE AVALIAÇÃO (Resumo)": "O processo avaliativo se dá por meio de 3 unidades avaliativas, AV1 (25%), AV2 (25%) e AV3 (30%), e o Exame de Desempenho dos Alunos de Graduação (EDAG) com peso de 20%.",
        "CONTEÚDOS FORMATIVOS": [
            "1. Sistema de banco de dados",
            "    - Banco de dados; sistema gerenciador de banco de dados; metadados; usuários.",
            "2. Arquitetura de SGBD",
            "    - Categoria de modelos de dados; esquemas e instâncias; independências de dados de SGBD's.",
            "3. Modelo conceitual de dados",
            "    - Modelagem conceitual com abordagem E-R; entidade; relacionamentos; atributos; cardinalidade e condicionalidade.",
            "4. Modelos lógico de dados",
            "    - Tabelas, atributos; restrições de domínio; chave primária, secundária, estrangeira.",
            "5. Transformação de modelos de dados",
            "    - Técnicas para conversão do modelo conceitual para o lógico e vice-versa.",
            "6. Dependência funcional e normalização",
            "    - Semântica de atributos de relação; anomalias de atualizações, remoção e informação redundante.",
            "    - Dependência funcional; forma de Boyce-Codd; 1FN, 2FN e 3FN.",
            "7. Álgebra Relacional e Cálculo Relacional",
            "    - Operações SELECT, PROJECT, JOIN e DIVISION.",
            "    - Sequência de operações; renomeando atributos; operações da Teoria dos Conjuntos.",
            "    - Funções de agregação; cálculo relacional de tuplas e de domínio.",
            "8. Structured Query Language - SQL",
            "    - Subconjuntos de Classificação da Linguagem (DML, DDL, DCL, DTL).",
            "    - Operações com strings; ordenação; subconsultas aninhadas.",
            "9. Linguagem procedural em banco de dados",
            "    - Comandos básicos; procedures; funções; gatilhos.",
            "10. Processamento de consultas",
            "    - Índices; otimização de consultas.",
            "11. Processamento de transação",
            "    - Propriedades ACID; recuperação à falhas; controle de concorrência.",
            "12. Bancos de dados não-relacionais",
            "    - Categorias e modelagem de estrutura não-relacional.",
            "    - Migração de dados e operações em bancos orientados à documentos."
        ]
    }

    gabarito_exemplo = {
        "competencias": [
            "A/ B/ C"
        ],
        "temas": [
            {
                "ua": "UA01",
                "titulo": "Fundamentos de Sistemas de Banco de Dados e Arquitetura de SGBD",
                "recursos": [
                    {
                        "id": "RECURSO-122332FF",
                        "tipo": "OVA",
                        "titulo": "Fundamentos de Bancos de Dados",
                        "minutagem": "50",
                        "conteudo_formativo": [
                            "Sistemas de bancos de dados",
                            "Sistema gerenciador de banco de dados",
                            "Usuários",
                            "Metadados",
                            "Sistema de banco de dados",
                            "Arquitetura de SGBD",
                            "Categorias de modelos de dados",
                            "Esquemas e instâncias",
                            "Independência de dados de SGBDs"
                        ],
                        "objetivos": [
                            "Obj1. Explicar o conceito de banco de dados, reconhecendo suas características fundamentais.\nObj2. Descrever as diferenças entre sistemas de banco de dados e sistemas baseados em arquivos, a partir de suas formas de organização e gerenciamento da informação.\nObj3. Descrever o papel do Sistema Gerenciador de Banco de Dados (SGBD) no armazenamento e na organização dos dados.\nObj4. Explicar as principais funções desempenhadas pelo SGBD, incluindo recuperação, controle e gerenciamento do acesso aos dados.\nObj5. Identificar os principais tipos de usuários de um banco de dados, reconhecendo suas responsabilidades e formas de interação com o SGBD."
                        ]
                    },
                    {
                        "id": "RECURSO-09FEA213",
                        "tipo": "Texto (HTML)",
                        "titulo": "Evolução dos Banco de Dados",
                        "minutagem": "30",
                        "conteudo_formativo": [
                            "Sistemas de bancos de dados",
                            "Sistema gerenciador de banco de dados",
                            "Usuários",
                            "Metadados",
                            "Sistema de banco de dados",
                            "Arquitetura de SGBD",
                            "Categorias de modelos de dados",
                            "Esquemas e instâncias",
                            "Independência de dados de SGBDs"
                        ],
                        "objetivos": [
                            "Obj6. Descrever as principais fases da evolução dos sistemas de banco de dados a partir das limitações dos sistemas baseados em arquivos.\nObj7. Explicar os principais problemas dos sistemas baseados em arquivos que motivaram o surgimento dos Sistemas Gerenciadores de Banco de Dados (SGBDs).\nObj8. Explicar como a evolução dos sistemas de banco de dados contribuiu para a melhoria da organização, do controle e do compartilhamento das informações."
                        ]
                    },
                    {
                        "id": "RECURSO-D0036EC1",
                        "tipo": "Roteiro de Atividade (HTML)",
                        "titulo": "Arquitetura e Organização dos Sistemas de Banco de Dados",
                        "minutagem": "100",
                        "conteudo_formativo": [
                            "Sistemas de bancos de dados",
                            "Sistema gerenciador de banco de dados",
                            "Usuários",
                            "Metadados",
                            "Sistema de banco de dados",
                            "Arquitetura de SGBD",
                            "Categorias de modelos de dados",
                            "Esquemas e instâncias",
                            "Independência de dados de SGBDs"
                        ],
                        "objetivos": [
                            "Obj9. Descrever o conceito de metadados, compreendendo sua função na estrutura e no gerenciamento de bancos de dados.\nObj10. Diferenciar esquemas e instâncias de banco de dados, relacionando esses conceitos ao ciclo de vida das informações.\nObj11. Explicar o conceito de independência de dados, distinguindo independência lógica e independência física em SGBDs.\nObj12. Classificar os principais modelos de dados utilizados em SGBDs, reconhecendo suas categorias conforme a arquitetura do sistema.\nObj 13. Analisar a arquitetura de um SGBD, identificando seus componentes fundamentais e suas funções no processamento de dados."
                        ]
                    },
                    {
                        "id": "RECURSO-0C211522",
                        "tipo": "NA",
                        "titulo": "Aula Síncrona",
                        "minutagem": "100",
                        "conteudo_formativo": [
                            "Sistemas de bancos de dados",
                            "Sistema gerenciador de banco de dados",
                            "Usuários",
                            "Metadados",
                            "Sistema de banco de dados",
                            "Arquitetura de SGBD",
                            "Categorias de modelos de dados",
                            "Esquemas e instâncias",
                            "Independência de dados de SGBDs"
                        ],
                        "objetivos": [
                            "Obj4. Explicar as principais funções desempenhadas pelo SGBD, incluindo recuperação, controle e gerenciamento do acesso aos dados.\nObj8. Explicar como a evolução dos sistemas de banco de dados contribuiu para a melhoria da organização, do controle e do compartilhamento das informações.\nObj 13. Analisar a arquitetura de um SGBD, identificando seus componentes fundamentais e suas funções no processamento de dados."
                        ]
                    },
                    {
                        "id": "RECURSO-DF7BBB5D",
                        "tipo": "Quiz",
                        "titulo": "Quiz",
                        "minutagem": "20",
                        "conteudo_formativo": [
                            "Sistemas de bancos de dados",
                            "Sistema gerenciador de banco de dados",
                            "Usuários",
                            "Metadados",
                            "Sistema de banco de dados",
                            "Arquitetura de SGBD",
                            "Categorias de modelos de dados",
                            "Esquemas e instâncias",
                            "Independência de dados de SGBDs"
                        ],
                        "objetivos": [
                            "G1: Obj4. Explicar as principais funções desempenhadas pelo SGBD, incluindo recuperação, controle e gerenciamento do acesso aos dados.\nG2: Obj8. Explicar como a evolução dos sistemas de banco de dados contribuiu para a melhoria da organização, do controle e do compartilhamento das informações.\nG3: Obj 13. Analisar a arquitetura de um SGBD, identificando seus componentes fundamentais e suas funções no processamento de dados."
                        ]
                    }
                ],
                "conteudo_formativo": [
                    "Sistemas de bancos de dados",
                    "Sistema gerenciador de banco de dados",
                    "Usuários",
                    "Metadados",
                    "Sistema de banco de dados",
                    "Arquitetura de SGBD",
                    "Categorias de modelos de dados",
                    "Esquemas e instâncias",
                    "Independência de dados de SGBDs"
                ]
            },
            {
                "ua": "UA02",
                "titulo": "Modelagem Conceitual de Dados",
                "recursos": [],
                "conteudo_formativo": [
                    "Modelo conceitual de dados:",
                    "Modelagem conceitual com abordagem E-R",
                    "Entidade",
                    "Relacionamentos",
                    "Atributos",
                    "Cardinalidade",
                    "Condicionalidade"
                ]
            },
            {
                "ua": "UA03",
                "titulo": "Modelagem Lógica",
                "recursos": [],
                "conteudo_formativo": [
                    "Modelo lógico de dados",
                    "Tabelas",
                    "Atributos",
                    "Restrições de domínio",
                    "Chave primária",
                    "Chave secundária",
                    "Chave estrangeira",
                    "Transformação de modelos de dados",
                    "Técnicas para conversão do modelo conceitual para o lógico e vice-versa"
                ]
            },
            {
                "ua": "UA04",
                "titulo": "Dependência Funcional e Normalização",
                "recursos":[],
                "conteudo_formativo": [
                    "Dependência funcional e normalização",
                    "Semântica de atributos de relação",
                    "Anomalias de atualizações",
                    "Anomalias de remoção",
                    "Informação redundante em tuplas",
                    "Valores null em tuplas",
                    "Tuplas espúrias",
                    "Dependência funcional",
                    "Primeira Forma Normal - 1FN",
                    "Segunda Forma Normal - 2FN",
                    "Terceira Forma Normal - 3FN",
                    "Forma de Boyce-Codd"
                ]
            },
            {
                "ua": "UA05",
                "titulo": "Álgebra Relacional e Cálculo Relacional",
                "recursos": [],
                "conteudo_formativo": [
                    "Álgebra Relacional e Cálculo Relacional",
                    "Operações SELECT e PROJECT",
                    "Sequência de operações",
                    "Renomeando atributos",
                    "Operações da teoria dos conjuntos",
                    "Cálculo relacional de tuplas",
                    "Cálculo relacional de domínio",
                    "Operação JOIN",
                    "Operação DIVISION",
                    "Funções de agregação"
                ]
            },
            {
                "ua": "UA06",
                "titulo": "Structured Query Language - SQL",
                "recursos": [],
                "conteudo_formativo": [
                    "Structured Query Language - SQL",
                    "Subconjuntos de classificação da linguagem",
                    "Linguagem de Manipulação de Dados - DML",
                    "Linguagem de Definição de Dados - DDL",
                    "Linguagem de Controle de Dados - DCL",
                    "Linguagem de Transação de Dados - DTL",
                    "Operações com strings",
                    "Ordenação",
                    "Subconsultas aninhadas",
                    "Linguagem Procedural em Bancos de Dados",
                    "Comandos básicos",
                    "Procedures",
                    "Funções",
                    "Gatilhos"
                ]
            },
            {
                "ua": "UA07",
                "titulo": "Processamento de Consultas e Transações",
                "recursos": [],
                "conteudo_formativo": [
                    "Processamento de Consultas",
                    "Índices",
                    "Otimização de consultas",
                    "Processamento de Transação",
                    "Propriedades ACID",
                    "Recuperação de falhas",
                    "Controle de concorrência"
                ]
            },
            {
                "ua": "UA08",
                "titulo": "Bancos de Dados Não-Relacionais (NoSQL)",
                "recursos": [],
                "conteudo_formativo": [
                    "Bancos de Dados Não-Relacionais",
                    "Categorias",
                    "Bancos de dados não-relacionais",
                    "Modelagem de uma estrutura de bancos de dados não relacional",
                    "Migração de dados para banco de dados não relacional",
                    "Operações de manipulação de dados em bancos de dados orientados a documentos."
                ]
            }
        ]
    }

    meu_criador = AgenteCriadorUnidadesCrewAI(memoria_vetorial=MemoriaVetorialUnica)

    bench = BenchmarkCriacaoUA1(meu_criador, disciplina_exemplo, gabarito_exemplo)
    bench.rodar_benchmark_completo()
    bench.salvar_xlsx()