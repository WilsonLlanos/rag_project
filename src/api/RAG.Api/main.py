from fastapi import FastAPI
from pydantic import BaseModel
from services.openai_service import test_llm_connection
from services.rag_service import consultar_manuais_rag

# # IMPORT CORRIGIDO: 
# from services.openai_service import test_llm_connection 

# Define o formato do JSON que a API espera receber no POST
class PerguntaRequest(BaseModel):
    pergunta: str

app = FastAPI(title="API Suporte IA - RAG Híbrido")

@app.get("/")
def read_root():
    return {"status": "Online", "projeto": "TCC MBA IA & Big Data"}

@app.get("/test-llm")
def test_openai(mensagem: str = "Diga um oi para confirmar que a conexão funcionou!"):
    resposta = test_llm_connection(mensagem)
    return {
        "teste": "Azure OpenAI",
        "mensagem_enviada": mensagem,
        "resposta_da_ia": resposta
    }

@app.post("/chat")
def chat_com_manuais(request: PerguntaRequest):
    """
    Recebe a pergunta do usuário (ex: do Streamlit) e processa via RAG Híbrido.
    """
    resultado = consultar_manuais_rag(request.pergunta)
    return resultado