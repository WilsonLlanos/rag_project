import json
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from config import settings
from services.database import consultar_saldo_contrato, ajustar_residuo_lote_por_codigo_lote, consultar_fornecedor_por_nome

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
            "name": "consultar_saldo_contrato",
            "description": "Consulta o saldo atual, status e histórico de movimentações de um lote. Pode pesquisar pelo número do contrato (ex: 'CTR-2026-A101') OU pelo ID do lote (ex: 1045).",
            "parameters": {
                "type": "object",
                "properties": {
                    "numero_contrato": {
                        "type": "string",
                        "description": "O número de referência do contrato (ex: 'CTR-2026-A101')"
                    },
                    "codigo_lote": {
                        "type": "string",
                        "description": "O código do lote (ex: 'L-0001')"
                    }
                },
                # Não colocamos "required" porque a IA pode mandar um OU outro.
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
                        "description": "O nome ou parte do nome da fazenda/fornecedor (ex: 'Fazenda São José'). Extraia esta informação do contexto da tela ou da pergunta."
                    }
                },
                "required": ["nome_fornecedor"]
            }
        }
    }
]

def _executar_busca_vetorial(pergunta_usuario: str):
    """Função auxiliar oculta para buscar nos manuais em Markdown."""
    resposta_embedding = openai_client.embeddings.create(
        input=pergunta_usuario,
        model=settings.azure_openai_embedding_deployment
    )
    vetor_pergunta = resposta_embedding.data[0].embedding

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


def consultar_manuais_rag(pergunta_usuario: str, dados_tela: dict = None, historico_conversa: list = None):
    """
    Orquestrador Principal: Gere a conversa, decide se busca manuais ou se executa ferramentas SQL.
    """
    try:
        # Passo 1: Traz os manuais vetoriais para o contexto
        contexto_manuais = _executar_busca_vetorial(pergunta_usuario)

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
        while True:
            resposta_chat = openai_client.chat.completions.create(
                model=settings.azure_openai_chat_deployment,
                messages=mensagens_conversa,
                tools=ferramentas_disponiveis,
                tool_choice="auto", # Deixa a IA decidir se precisa usar ou não
                temperature=0.2
            )

            mensagem_assistente = resposta_chat.choices[0].message
            mensagens_conversa.append(mensagem_assistente) 

            # Se a IA não pediu para chamar ferramentas, o raciocínio terminou! Sai do ciclo.
            if not mensagem_assistente.tool_calls:
                break

            # Se a IA pediu para chamar ferramentas, executa o código!
            for tool_call in mensagem_assistente.tool_calls:
                nome_funcao = tool_call.function.name
                # Extrai os argumentos que a IA decidiu usar e transforma em dicionário Python
                argumentos = json.loads(tool_call.function.arguments)
                
                print(f"DEBUG: A IA decidiu chamar a função '{nome_funcao}' com os dados: {argumentos}")

                # # Executa a função física real no nosso sistema
                # if nome_funcao == "consultar_saldo_contrato":
                #     resultado_db = consultar_saldo_contrato(argumentos["numero_contrato"])
                # elif nome_funcao == "ajustar_residuo_lote_por_codigo_lote":
                #     resultado_db = ajustar_residuo_lote_por_codigo_lote(argumentos["lote_id"])
                # else:
                #     resultado_db = {"erro": "Ferramenta desconhecida."}

                # Executa a função física real no nosso sistema
                if nome_funcao == "consultar_saldo_contrato":
                    num_contrato = argumentos.get("numero_contrato")
                    codigo_lote = argumentos.get("codigo_lote")
                    resultado_db = consultar_saldo_contrato(num_contrato, codigo_lote)
                elif nome_funcao == "ajustar_residuo_lote_por_codigo_lote":
                    resultado_db = ajustar_residuo_lote_por_codigo_lote(argumentos["codigo_lote"])
                elif nome_funcao == "consultar_fornecedor_por_nome":
                    resultado_db = consultar_fornecedor_por_nome(argumentos["nome_fornecedor"])
                else:
                    resultado_db = {"erro": "Ferramenta desconhecida."}

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