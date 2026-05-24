import os
import uuid
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SimpleField, SearchableField, SearchField, SearchFieldDataType,
    SearchIndex, VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile
)
from openai import AzureOpenAI
from config import settings

# Sobe 3 níveis: RAG.Api -> api -> src -> rag_project, e depois entra em /data
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))

print(f"DEBUG: O script está procurando os arquivos em: {DATA_PATH}")

# 1. Inicializa os Clientes
openai_client = AzureOpenAI(
    azure_endpoint=settings.azure_openai_endpoint,
    api_key=settings.azure_openai_api_key,
    api_version="2024-02-01"
)

search_credential = AzureKeyCredential(settings.azure_search_key)
index_client = SearchIndexClient(endpoint=settings.azure_search_endpoint, credential=search_credential)
search_client = SearchClient(endpoint=settings.azure_search_endpoint, index_name=settings.azure_search_index, credential=search_credential)

def create_index_if_not_exists():
    """Cria o índice no Azure Search com suporte a vetores (IaC)"""
    index_name = settings.azure_search_index
    try:
        index_client.get_index(index_name)
        print(f" Índice '{index_name}' já existe.")
    except Exception:
        print(f" Criando índice '{index_name}'...")
        
        # Definição das colunas do banco vetorial
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="filename", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchField(
                name="content_vector", 
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True, 
                vector_search_dimensions=1536, # Tamanho do vetor do text-embedding-3-small
                vector_search_profile_name="myHnswProfile"
            )
        ]
        
        # Configuração do motor de busca vetorial
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="myHnsw")],
            profiles=[VectorSearchProfile(name="myHnswProfile", algorithm_configuration_name="myHnsw")]
        )
        
        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
        index_client.create_index(index)
        print(" Índice criado com sucesso!")

def get_embedding(text: str):
    """Chama o Azure OpenAI para converter texto em vetor"""
    response = openai_client.embeddings.create(
        input=text,
        model=settings.azure_openai_embedding_deployment
    )
    return response.data[0].embedding

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100):
    """Função simples para quebrar o Markdown em blocos menores (sem LangChain)"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def run_indexer():
    create_index_if_not_exists()
    
    print(f" Lendo arquivos da pasta: {DATA_PATH}")
    documents_to_upload = []
    
    # Varre a pasta data em busca de arquivos markdown
    if not os.path.exists(DATA_PATH):
        print(" Pasta 'data' não encontrada. Verifique o caminho.")
        return

    for filename in os.listdir(DATA_PATH):
        if filename.endswith(".md"):
            filepath = os.path.join(DATA_PATH, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            print(f" Processando: {filename}")
            chunks = chunk_text(content)
            
            for i, chunk in enumerate(chunks):
                # Cria um ID único para cada chunk
                nome_limpo = filename.replace(".md", "").replace(" ", "_")
                vector = get_embedding(chunk)
                
                documents_to_upload.append({
                    "id": f"{nome_limpo}_{i}",
                    "filename": filename,
                    "content": chunk,
                    "content_vector": vector
                })
    
    # Sobe os dados em lote para o Azure
    if documents_to_upload:
        print(f" Enviando {len(documents_to_upload)} blocos para o Azure AI Search...")
        search_client.upload_documents(documents=documents_to_upload)
        print(" Upload concluído com sucesso!")
    else:
        print(" Nenhum documento Markdown encontrado para indexar.")

if __name__ == "__main__":
    run_indexer()