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

    # Configuração para ler o arquivo .env
    model_config = SettingsConfigDict(env_file=".env")

@lru_cache # Isso garante que as configurações sejam lidas apenas uma vez (performance)
def get_settings():
    return Settings()

# Instância global para facilitar o uso
settings = get_settings()