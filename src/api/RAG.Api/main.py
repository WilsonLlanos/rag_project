import os
from azure.monitor.opentelemetry import configure_azure_monitor

# Application Insights / OpenTelemetry: só ativa se a connection string estiver configurada
# (evita erro em desenvolvimento local sem recurso Azure Monitor provisionado).
# PRECISA rodar antes do "from fastapi import FastAPI" abaixo: configure_azure_monitor()
# instrumenta FastAPI trocando o atributo fastapi.FastAPI por uma subclasse instrumentada
# (monkey-patch); se o nome FastAPI já tiver sido importado antes disso, o import local
# fica preso à classe antiga e a instrumentação automática de requisições não funciona.
if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from services.openai_service import test_llm_connection
from services.rag_service import consultar_manuais_rag
from services.database import (
    listar_fornecedores_filtrados,
    listar_todos_os_lotes,
    criar_tabela_auditoria_se_nao_existir,
    criar_tabela_consumo_llm_se_nao_existir,
)
from services.security_service import anonimiza_e_tokeniza, reidratar_texto

# # IMPORT CORRIGIDO:   
# from services.openai_service import test_llm_connection 

# 1. Classe para tipar a estrutura do histórico
class MensagemChat(BaseModel):
    role: str
    content: Optional[str] = None

# Define o formato do JSON que a API espera receber no POST
class PerguntaRequest(BaseModel):
    pergunta: str
    telaAtual: str
    dadosContextuais: Optional[Dict[str, Any]] = {}
    historico: Optional[List[MensagemChat]] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Garante a existência da tabela de auditoria (observabilidade para o projeto multiagentes)
    criar_tabela_auditoria_se_nao_existir()
    # Garante a existência da tabela de consumo de LLM (FinOps, Cap. 5 do TCC)
    criar_tabela_consumo_llm_se_nao_existir()
    yield

app = FastAPI(title="API Suporte IA - RAG Híbrido", lifespan=lifespan)

@app.get("/")
def read_root():
    return {"status": "Online", "projeto": "Suporte N1"}

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
    pergunta_segura, cofre = anonimiza_e_tokeniza(request.pergunta)

    # LOG DE SEGURANÇA mostrando o texto original e o texto seguro no terminal
    print("--- LOG DE SEGURANÇA ---")
    print(f"Texto Original : {request.pergunta}")
    print(f"Texto Seguro   : {pergunta_segura}")
    print(f"Cofre Gerado   : {cofre}") # Vai imprimir: {'<BR_CNPJ_1>': '12.345.678/0001-95', ...}
    print("------------------------")

    historico_dict = [{"role": m.role, "content": m.content} for m in request.historico]

    # ORQUESTRAÇÃO: A IA pensa que o usuário digitou o dado sintético
    # resultado = consultar_manuais_rag(request.pergunta)
    # aceita o 'cofre' como parâmetro se ela for fazer Tool Calling (para reidratar os argumentos do SQL).
    resposta_ia_segura = consultar_manuais_rag(
        pergunta_usuario=pergunta_segura, 
        dados_tela=request.dadosContextuais,
        historico_conversa=historico_dict,
        cofre=cofre  #Enviando o cofre para o RAG
    )

    # Prevenção: Se o RAG retornar um erro (ex: falha no banco), devolvemos direto
    if "erro" in resposta_ia_segura:
        return {"erro": resposta_ia_segura["erro"]}

    texto_ia_seguro = resposta_ia_segura.get("resposta", "")

    # 3. REIDRATAÇÃO: Desfaz a máscara na resposta da IA
    resposta_final_limpa = reidratar_texto(texto_ia_seguro, cofre)

    return {"resposta": resposta_final_limpa}

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