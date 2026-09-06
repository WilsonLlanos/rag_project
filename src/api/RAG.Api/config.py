from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # SQL Azure
    azure_sql_connection_string: str
    
    # Azure OpenAI
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    
    # Azure AI Search
    azure_search_endpoint: str
    azure_search_key: str
    azure_search_index: str

    # FinOps: preço por 1.000 tokens (USD), usado para estimar o custo de cada
    # chamada ao Azure OpenAI (ver EventosConsumoLLM). Nomes genéricos (não
    # amarrados ao nome do modelo) para não exigir alterar o schema se o
    # deployment mudar. Defaults calibrados para GPT-4o-mini (modelo real em
    # produção deste projeto), conforme a tabela pública de preços do Azure
    # OpenAI (deployment Standard/Global, sob demanda) no momento da escrita.
    # IMPORTANTE: confirmar contra o preço vigente na região e no acordo de
    # faturamento reais antes de usar qualquer custo calculado no Cap. 5 do
    # TCC — ver openspec/changes/add-metricas-consumo-llm/design.md (Open
    # Questions). Sobrescrevível via .env.
    preco_chat_entrada_usd_por_1k: float = 0.00015
    preco_chat_saida_usd_por_1k: float = 0.00060
    preco_embedding_usd_por_1k: float = 0.00002

    # Configuração para ler o arquivo .env
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache # Isso garante que as configurações sejam lidas apenas uma vez (performance)
def get_settings():
    return Settings()

# Instância global para facilitar o uso
settings = get_settings()