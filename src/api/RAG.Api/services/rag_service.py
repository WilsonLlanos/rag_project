import json
import time
import uuid
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from config import settings
from services.database import (
    filtrar_lotes,
    ajustar_residuo_lote_por_codigo_lote,
    consultar_fornecedor_por_nome,
    registrar_evento_auditoria,
    registrar_evento_consumo_llm
)

# 1. Instancia os clientes (OpenAI e AI Search)
openai_client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version="2024-02-01"
)

search_credential = AzureKeyCredential(settings.azure_search_key)
search_client = SearchClient(
    endpoint=settings.azure_search_endpoint, 
    index_name=settings.azure_search_index, 
    credential=search_credential
)

# 2. Definição do JSON Schema das Ferramentas (Tool Calling)
# Isto ensina ao GPT-4o QUAIS ferramentas ele tem e COMO usá-las.
ferramentas_disponiveis = [
   {
        "type": "function",
        "function": {
            "name": "filtrar_lotes",
            "description": "Consulta o saldo atual, status, qualidade e histórico de movimentações de um lote. Pode pesquisar pelo número do contrato (ex: 'CTR-2026-A101'), pelo ID do lote (ex: 1045), pela qualidade (ex: 'Árabica'), pelo status (ex: 'Ativo' para lotes com saldo existente, 'Encerrado' para lotes com saldo igual a zero) ou pelo saldo residual (ex: 0.005).",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo_lote": {
                    "type": "string",
                    "description": "O código do lote, sempre no formato 'L-XXXX' (ex: 'L-0001', 'L-0007'). NUNCA é um nome de fornecedor ou de fazenda, mesmo que o usuário use a palavra 'lote' perto de outro nome."
                },
                "fornecedor_nome": {
                    "type": "string",
                    "description": "O nome ou parte do nome do fornecedor (ex: 'João da Silva')"
                },
                "qualidade": {
                    "type": "string",
                    "description": "A qualidade do produto (ex: 'Arábica', 'Conillon')"
                },
                "status": {
                    "type": "string",
                    "description": "O status do lote (ex: 'Aberto', 'Encerrado')"
                },
                "apenas_com_residuos": {
                    "type": "boolean",
                    "description": "Se verdadeiro (true), filtra apenas lotes que possuem saldo residual (maior que 0 e menor ou igual a 0.01 sacas)."
                }
                },
                # Sem "required" porque a IA pode mandar um ou outro.
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ajustar_residuo_lote_por_codigo_lote",
            "description": "Corrige resíduos decimais e encerra um lote no banco de dados. OBRIGATÓRIO: Só utilize esta função se o utilizador tiver pedido EXPRESSAMENTE para corrigir, zerar ou ajustar o saldo do lote após uma consulta.",
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo_lote": {
                        "type": "string",
                        "description": "O código do lote (ex: 'L-0001')."
                    }
                },
                "required": ["codigo_lote"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_fornecedor_por_nome",
            "description": "Consulta os dados de um fornecedor a partir do nome. Use esta função sempre que o utilizador relatar problemas para encontrar um fornecedor na tela, ou se quiser confirmar que tipo de café (Arábica ou Conillon) um fornecedor específico vende.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_fornecedor": {
                        "type": "string",
                        "description": "O nome ou parte do nome da fazenda/fornecedor (ex: 'Fazenda São José'). Extraia esta informação do contexto da tela ou da pergunta. NUNCA um código no formato 'L-XXXX' — esse padrão é sempre um código de lote, use 'filtrar_lotes' nesse caso."
                    }
                },
                "required": ["nome_fornecedor"]
            }
        }
    }
]

def _executar_busca_vetorial(pergunta_usuario: str, id_atendimento: str):
    """Função auxiliar oculta para buscar nos manuais em Markdown."""
    resposta_embedding = openai_client.embeddings.create(
        input=pergunta_usuario,
        model=settings.azure_openai_embedding_deployment
    )
    vetor_pergunta = resposta_embedding.data[0].embedding

    # FinOps: captura o consumo de tokens desta chamada de embeddings (Cap. 5 do TCC)
    uso_embedding = resposta_embedding.usage
    custo_embedding = (uso_embedding.total_tokens / 1000) * settings.preco_embedding_usd_por_1k
    registrar_evento_consumo_llm(
        id_atendimento=id_atendimento,
        tipo_chamada="Embedding",
        nome_deployment=settings.azure_openai_embedding_deployment,
        numero_iteracao_react=None,
        prompt_tokens=uso_embedding.prompt_tokens,
        completion_tokens=None,
        total_tokens=uso_embedding.total_tokens,
        custo_estimado_usd=custo_embedding
    )

    vetor_query = VectorizedQuery(
        vector=vetor_pergunta, 
        k_nearest_neighbors=3,
        fields="content_vector"
    )
    
    resultados = search_client.search(
        search_text=None,
        vector_queries=[vetor_query],
        select=["filename", "content"]
    )

    contexto_textual = ""
    for doc in resultados:
        contexto_textual += f"\n[Arquivo: {doc['filename']}]\n{doc['content']}\n"
    
    return contexto_textual


def consultar_manuais_rag(pergunta_usuario: str, dados_tela: dict = None, historico_conversa: list = None, cofre: dict = None):
    """
    Orquestrador Principal: Gere a conversa, decide se busca manuais ou se executa ferramentas SQL.
    """
    # FinOps: identifica todas as chamadas de LLM desta pergunta do usuário (Cap. 5 do TCC)
    id_atendimento = str(uuid.uuid4())

    try:
        # Passo 1: Traz os manuais vetoriais para o contexto
        contexto_manuais = _executar_busca_vetorial(pergunta_usuario, id_atendimento)

        # Transforma os dados da tela em um texto formatado para a IA ler
        contexto_tela_str = json.dumps(dados_tela, indent=2, ensure_ascii=False) if dados_tela else "Nenhum dado preenchido na tela."

        prompt_sistema = f"""Você é um assistente de suporte Nível 1 para uma trading de commodities agrícolas.
        Seu objetivo é resolver dúvidas dos usuários.
        
        Você tem acesso a:
        1. Manuais operacionais anexados abaixo.
        2. Ferramentas (Tools) para acessar e modificar a base de dados SQL.
        
        REGRA 1: Se a dúvida for teórica/procedimental, responda EXCLUSIVAMENTE com os manuais.
        REGRA 2: Se o usuário fornecer um número de contrato, utilize a ferramenta 'consultar_saldo_contrato'.
        REGRA 3: NUNCA atualize ou corrija um lote sem permissão explícita do usuário. Se você consultar o saldo e verificar que há um resíduo <= 0.01 sacas, INFORME o usuário e PERGUNTE se ele deseja que você execute a correção. Só utilize a ferramenta 'ajustar_residuo_lote_por_codigo_lote' se o usuário responder 'sim'.
        REGRA 4: AUDITORIA DE FORNECEDORES. Se o usuário mencionar o nome de um fornecedor que não está aparecendo na tela, você é OBRIGADO a executar a ferramenta 'consultar_fornecedor_por_nome' usando o nome fornecido na pergunta ANTES de dar qualquer resposta.
            - NUNCA tente adivinhar. Não gere a resposta sem antes ler o retorno da ferramenta.
            - Após a ferramenta retornar os dados reais do banco, compare todos os dados preenchidos na tela com os dados que você tem do banco.
            - Use as regras do Manual de Compliance EISA para explicar ao usuário, de forma técnica e exata, por que os filtros da tela bloquearam aquele fornecedor.
        REGRA 5: VISÃO GERAL DE LOTES E SALDOS. Se o usuário perguntar de forma genérica quais lotes possuem saldo ou resíduo (sem especificar fornecedor ou contrato):
            - INFORME que a própria tela do sistema possui um filtro nativo para visualizar essas informações rapidamente.
            - OFEREÇA ajuda dizendo que, se ele quiser saber os lotes com resíduos, você pode buscar essa informação.
            - Caso ele confirme que deseja que você busque, utilize OBRIGATORIAMENTE a ferramenta 'filtrar_lotes' com o parâmetro 'apenas_com_residuos' definido como true.
            - Se o usuário solicitar correção de resíduos no saldo dos lotes, utilize a ferramenta 'ajustar_residuo_lote_por_codigo_lote' APENAS se ele tiver confirmado explicitamente que deseja que você faça a correção.
        REGRA 6: DISTINÇÃO ENTRE CÓDIGO DE LOTE E NOME DE FORNECEDOR. Um identificador no formato 'L-XXXX' (ex: 'L-0007') é SEMPRE um código de lote, mesmo que apareça ao lado de palavras como "saldo", "resíduo" ou "verificar" — use 'filtrar_lotes' com o parâmetro 'codigo_lote'. NUNCA passe esse identificador como 'nome_fornecedor'. Nomes próprios ou de fazendas (ex: 'Fazenda Esperança', 'João da Silva') são fornecedores — use 'consultar_fornecedor_por_nome'.

        DADOS ATUAIS DA TELA DO USUÁRIO:
        {contexto_tela_str}

        MANUAIS RECUPERADOS:
        {contexto_manuais}
        """

        # Prepara a lista de mensagens que será gerida no ciclo
        mensagens_conversa = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": pergunta_usuario}
        ]

        # INJEÇÃO DE MEMÓRIA: Adiciona o histórico de chat anterior
        if historico_conversa:
            for msg in historico_conversa:
                # Pega apenas o role e o content para não poluir o modelo com lixo de UI
                mensagens_conversa.append({"role": msg["role"], "content": msg["content"]})

        # Adiciona a nova pergunta do usuário no final
        mensagens_conversa.append({"role": "user", "content": pergunta_usuario})

        # Passo 2: O Ciclo de Chamada (ReAct Pattern)
        # O modelo pode precisar chamar várias ferramentas em sequência.
        numero_iteracao_react = 0
        while True:
            numero_iteracao_react += 1
            resposta_chat = openai_client.chat.completions.create(
                model=settings.azure_openai_chat_deployment,
                messages=mensagens_conversa,
                tools=ferramentas_disponiveis,
                tool_choice="auto", # Deixa a IA decidir se precisa usar ou não
                temperature=0.2
            )

            # FinOps: captura o consumo de tokens desta rodada do ReAct (Cap. 5 do TCC)
            uso_chat = resposta_chat.usage
            custo_chat = (
                (uso_chat.prompt_tokens / 1000) * settings.preco_chat_entrada_usd_por_1k
                + (uso_chat.completion_tokens / 1000) * settings.preco_chat_saida_usd_por_1k
            )
            registrar_evento_consumo_llm(
                id_atendimento=id_atendimento,
                tipo_chamada="Chat",
                nome_deployment=settings.azure_openai_chat_deployment,
                numero_iteracao_react=numero_iteracao_react,
                prompt_tokens=uso_chat.prompt_tokens,
                completion_tokens=uso_chat.completion_tokens,
                total_tokens=uso_chat.total_tokens,
                custo_estimado_usd=custo_chat
            )

            mensagem_assistente = resposta_chat.choices[0].message
            mensagens_conversa.append(mensagem_assistente)

            # Se a IA não pediu para chamar ferramentas, o raciocínio terminou! Sai do ciclo.
            if not mensagem_assistente.tool_calls:
                break

            # Se a IA pediu para chamar ferramentas, executa o código!
            for tool_call in mensagem_assistente.tool_calls:
                nome_funcao = tool_call.function.name
                # Extrai argumentos que a IA decidiu usar e transforma em dicionário Python
                argumentos = json.loads(tool_call.function.arguments)

                # Cópia dos argumentos ANTES da reidratação de PII, para auditoria.
                # Nunca logar os argumentos já reidratados (dados reais).
                argumentos_seguro_para_log = dict(argumentos)

                # =================================================================
                # ---> O INTERCEPTOR (REHIDRATAÇÃO DE PII) ---
                # =================================================================
                if cofre:
                    for chave,valor in argumentos.items():
                        # verifica se valor é uma string pra poder usar .replace()
                        if isinstance(valor, str):
                            nome_valor = valor
                            # Procura qualquer token sintético do cofre dentro da string do argumento
                            for token_sintetico, valor_real in cofre.items():
                                if token_sintetico in nome_valor:
                                    print(f"desincriptando argumento {chave}: {token_sintetico} -> {valor_real}")
                                    # Substitui o dado sintético pelo real
                                    nome_valor = nome_valor.replace(token_sintetico, valor_real)
                            # Atualiza o dicionário de argumentos com o valor real
                            argumentos[chave] = nome_valor
                # =================================================================

                print(f"DEBUG: A IA decidiu chamar a função '{nome_funcao}' com os dados: {argumentos}")

                # # Executa a função física real no nosso sistema
                # if nome_funcao == "consultar_saldo_contrato":
                #     resultado_db = consultar_saldo_contrato(argumentos["numero_contrato"])
                # elif nome_funcao == "ajustar_residuo_lote_por_codigo_lote":
                #     resultado_db = ajustar_residuo_lote_por_codigo_lote(argumentos["lote_id"])
                # else:
                #     resultado_db = {"erro": "Ferramenta desconhecida."}

                # Executa a função física real no nosso sistema, medindo duração para auditoria
                inicio_execucao = time.perf_counter()
                try:
                    if nome_funcao == "filtrar_lotes":
                        codigo = argumentos.get("codigo_lote")
                        fornecedor = argumentos.get("fornecedor_nome")
                        qualidade = argumentos.get("qualidade")
                        status = argumentos.get("status")
                        apenas_residuos = argumentos.get("apenas_com_residuos", False)

                        resultado_db = filtrar_lotes(codigo_lote=codigo, fornecedor_nome=fornecedor, qualidade=qualidade, status=status, apenas_com_residuos=apenas_residuos)

                    elif nome_funcao == "ajustar_residuo_lote_por_codigo_lote":
                        resultado_db = ajustar_residuo_lote_por_codigo_lote(argumentos["codigo_lote"])
                    elif nome_funcao == "consultar_fornecedor_por_nome":
                        resultado_db = consultar_fornecedor_por_nome(argumentos["nome_fornecedor"])
                    else:
                        resultado_db = {"erro": "Ferramenta desconhecida."}

                    status_auditoria = "Erro" if "erro" in resultado_db else "Sucesso"
                    mensagem_erro_auditoria = resultado_db.get("erro") if status_auditoria == "Erro" else None
                except Exception as e:
                    resultado_db = {"erro": f"Falha ao executar ferramenta: {str(e)}"}
                    status_auditoria = "Erro"
                    mensagem_erro_auditoria = str(e)
                finally:
                    duracao_ms = int((time.perf_counter() - inicio_execucao) * 1000)
                    registrar_evento_auditoria(
                        nome_ferramenta=nome_funcao,
                        argumentos_seguro=argumentos_seguro_para_log,
                        status=status_auditoria,
                        duracao_ms=duracao_ms,
                        mensagem_erro=mensagem_erro_auditoria
                    )

                # Devolve o resultado do SQL para a memória da IA
                mensagens_conversa.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": nome_funcao,
                    "content": json.dumps(resultado_db) # Transforma o Python Dictionary de volta para texto para a IA ler
                })                
                
        # Quando o ciclo quebra, a última mensagem do assistente é a resposta final em texto
        return {
            "resposta": mensagem_assistente.content
        }

    except Exception as e:
        return {"erro": f"Falha na orquestração: {str(e)}"}