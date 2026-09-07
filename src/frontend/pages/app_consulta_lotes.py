import streamlit as st
import requests
import pandas as pd
import os

st.set_page_config(page_title="Consulta de estoque", layout="wide", page_icon="📦")

# --- AJUSTE DE CSS: Trava a largura do Popover ---
st.markdown(
    """
    <style>
    div[data-testid="stPopoverBody"] {
        width: 450px !important;
        max-width: 90vw !important;
    }
    div[data-testid="stPopoverBody"] * {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

status_tela = "Painel de Consulta de Lotes e Saldos"
st.title(f"📦 Sistema Café-Trade: {status_tela}")
st.markdown("---")

# 1. Busca os dados do Backend
lotes_data = []

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

try:
    response = requests.get(f"{API_BASE_URL}/lotes", timeout=20)
    if response.status_code == 200:
        lotes_data = response.json().get("lotes", [])
except Exception:
    st.error("API FastAPI Offline. Não foi possível carregar a base de dados.")

# 2. Área do Relatório Visual (A Tabela)
col_relatorio, col_suporte = st.columns([0.7, 0.3])

with col_relatorio:
    st.markdown("### 📊 Inventário Geral de Lotes")
    
    # Campo de Filtro Rápido
    filtro_pesquisa = st.text_input("🔍 Filtrar por Código do Lote (Ex: L-0001)", placeholder="Digite o código para isolar um lote na tabela...")
    
    if lotes_data:
        df_lotes = pd.DataFrame(lotes_data)
        
        if filtro_pesquisa:
            df_lotes = df_lotes[df_lotes['Código do Lote'].str.contains(filtro_pesquisa, case=False, na=False)]
        
        st.dataframe(df_lotes, width="stretch", hide_index=True)
        st.caption(f"Mostrando {len(df_lotes)} lote(s) encontrados.")
    else:
        st.info("Nenhum lote encontrado no banco de dados no momento.")

col_espaco, col_suporte = st.columns([0.7, 0.3])

with col_suporte:
    with st.popover("Dúvidas? Fale com a IA", use_container_width=True):
        st.markdown("### 🤖 Assistente")
    
        if "mensagens_chat" not in st.session_state:
            st.session_state.mensagens_chat = [
                {"role": "assistant", "content": "Olá! Como posso ajudar?"}
            ]

        caixa_chat = st.container(height=300)
        with caixa_chat:
            for msg in st.session_state.mensagens_chat:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        if prompt_usuario := st.chat_input("Digite sua mensagem aqui..."):
            
            with caixa_chat:
                with st.chat_message("user"):
                    st.write(prompt_usuario)
            st.session_state.mensagens_chat.append({"role": "user", "content": prompt_usuario})
            
            payload = {
                "pergunta": prompt_usuario,
                "telaAtual": status_tela,
                "dadosContextuais": {
                    "filtro_digitado_na_tela": filtro_pesquisa
                },
                "historico": st.session_state.mensagens_chat[:-1] 
            }
            
            api_url = f"{API_BASE_URL}/chat"
            
            with caixa_chat:
                with st.chat_message("assistant"):
                    with st.spinner("Analisando..."):
                        try:
                            response_ia = requests.post(api_url, json=payload, timeout=40)
                            if response_ia.status_code == 200:
                                dados_json = response_ia.json()
                                resposta_texto = dados_json.get("resposta")
                                erro_mensagem = dados_json.get("erro")

                                if resposta_texto:
                                    st.write(resposta_texto)
                                    st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_texto})
                                
                                    if "sucesso" in resposta_texto.lower():
                                        st.info("Atualize a tela para ver os novos saldos na tabela.")
                                elif erro_mensagem:
                                    st.error(f"Erro na resposta da IA: {erro_mensagem}")
                            else:
                                st.error(f"Erro na API (Status {response_ia.status_code}): {response_ia.text}")
                        except Exception as e:
                            st.error(f"Falha de conexão: {e}")

st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("WL Trading - Módulo de Gestão de Estoque v1.1 (PoC)")