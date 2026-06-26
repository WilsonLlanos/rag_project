from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from services.openai_service import test_llm_connection
from services.rag_service import consultar_manuais_rag
from services.database import listar_fornecedores_filtrados, listar_todos_os_lotes
from services.security_service import anonimiza_texto

# # IMPORT CORRIGIDO:   
# from services.openai_service import test_llm_connection 

# 1. Classe para tipar a estrutura do histórico
class MensagemChat(BaseModel):
    role: str
    content: str

# Define o formato do JSON que a API espera receber no POST
class PerguntaRequest(BaseModel):
    pergunta: str
    telaAtual: str
    dadosContextuais: Optional[Dict[str, Any]] = {}
    historico: Optional[List[MensagemChat]] = []

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
    pergunta_segura = anonimiza_texto(request.pergunta)

    # LOG DE SEGURANÇA mostrando o texto original e o texto seguro no terminal
    print("--- LOG DE SEGURANÇA ---")
    print(f"Texto Original : {request.pergunta}")
    print(f"Texto Seguro   : {pergunta_segura}")
    print("------------------------")

    historico_dict = [{"role": m.role, "content": m.content} for m in request.historico]
    # resultado = consultar_manuais_rag(request.pergunta)
    resposta_ia = consultar_manuais_rag(pergunta_segura, request.dadosContextuais, historico_dict)
    return resposta_ia

@app.get("/fornecedores")
def obter_fornecedores(tipo_cafe: str, estado: str):
    """
    Endpoint para listar fornecedores filtrados por tipo de café e estado.
    Exemplo de uso: /fornecedores?tipo_cafe=Arábica&estado=Minas%20Gerais
    """
    fornecedores = listar_fornecedores_filtrados(tipo_cafe, estado)
    return {"fornecedores": fornecedores}

@app.get("/lotes")
def obter_todos_os_lotes():
    """Endpoint para popular a tabela do painel de controle."""
    lotes = listar_todos_os_lotes()
    return {"lotes": lotes}