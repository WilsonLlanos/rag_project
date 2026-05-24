from openai import AzureOpenAI
from config import settings

def test_llm_connection(message: str):
    """
    Testa a conexão com o Azure OpenAI usando o SDK nativo.
    """
    try:
        # 1. Instancia o cliente do Azure OpenAI
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version="2024-02-01" # Versão estável da API
        )

        # 2. Faz a chamada passando o nome do seu deployment no parâmetro 'model'
        response = client.chat.completions.create(
            model=settings.azure_openai_chat_deployment,
            messages=[
                {"role": "system", "content": "Você é um assistente de IA focado em testes. Responda de forma amigável, curta e direta."},
                {"role": "user", "content": message}
            ],
            temperature=0.7, # Controla a criatividade (0.0 a 1.0)
            max_tokens=800
        )

        # 3. Extrai o texto da resposta
        return response.choices[0].message.content

    except Exception as e:
        return f"Erro ao conectar com Azure OpenAI: {str(e)}"