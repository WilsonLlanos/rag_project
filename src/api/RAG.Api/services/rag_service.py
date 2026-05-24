from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from config import settings

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

def consultar_manuais_rag(pergunta_usuario: str):
    """
    Executa o RAG: Transforma a pergunta em vetor, busca no AI Search e gera a resposta com GPT-4o.
    """
    try:
        # Passo 1: Converter a pergunta do usuário num vetor (Embedding)
        resposta_embedding = openai_client.embeddings.create(
            input=pergunta_usuario,
            model=settings.azure_openai_embedding_deployment
        )
        vetor_pergunta = resposta_embedding.data[0].embedding

        # Passo 2: Procurar no Azure AI Search os trechos mais similares
        vetor_query = VectorizedQuery(
            vector=vetor_pergunta, 
            k_nearest_neighbors=3, # Pega os 3 trechos de Markdown mais relevantes
            fields="content_vector"
        )
        
        resultados = search_client.search(
            search_text=None, # Busca puramente vetorial
            vector_queries=[vetor_query],
            select=["filename", "content"]
        )

        # Passo 3: Montar o contexto com os documentos encontrados
        contexto_textual = ""
        documentos_recuperados = [] # Para sabermos de onde a IA tirou a resposta
        
        for doc in resultados:
            contexto_textual += f"\n[Arquivo: {doc['filename']}]\n{doc['content']}\n"
            if doc['filename'] not in documentos_recuperados:
                documentos_recuperados.append(doc['filename'])

        # Se não encontrou nada, avisa para evitar alucinação
        if not contexto_textual.strip():
            return {"resposta": "Não encontrei informações sobre isso nos manuais indexados."}

        # Passo 4: Enviar para o GPT-4o (O Grounding)
        prompt_sistema = f"""Você é um assistente de suporte Nível 1 para uma trading de commodities agrícolas.
        Responda à dúvida do usuário utilizando EXCLUSIVAMENTE as informações do contexto abaixo.
        Se a resposta não estiver no contexto, diga que não tem a informação e oriente a abrir um chamado N2.
        
        CONTEXTO RECUPERADO DOS MANUAIS:
        {contexto_textual}
        """

        resposta_chat = openai_client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": pergunta_usuario}
            ],
            temperature=0.2 # Temperatura baixa para o RAG ser analítico e não criativo
        )

        return {
            "resposta": resposta_chat.choices[0].message.content,
            "fontes": documentos_recuperados
        }

    except Exception as e:
        return {"erro": f"Falha ao executar o RAG: {str(e)}"}