import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="EISA - Gestão de Lotes", layout="wide", page_icon="📦")

status_tela = "Painel de Consulta de Lotes e Saldos"
st.title(f"📦 Sistema Café-Trade: {status_tela}")
st.markdown("---")

# 1. Busca os dados do Backend
lotes_data = []
try:
    response = requests.get("http://localhost:8000/lotes", timeout=5)
    if response.status_code == 200:
        lotes_data = response.json().get("lotes", [])
except Exception:
    st.error("API FastAPI Offline. Não foi possível carregar a base de dados.")

# 2. Área do Relatório Visual (A Tabela)
col_relatorio, col_suporte = st.columns([0.7, 0.3])

with col_relatorio:
    st.markdown("### 📊 Inventário Geral de Lotes")
    
    # Campo de Filtro Rápido (Funciona no Streamlit)
    filtro_pesquisa = st.text_input("🔍 Filtrar por Código do Lote (Ex: L-0001)", placeholder="Digite o código para isolar um lote na tabela...")
    
    if lotes_data:
        # Transforma o JSON em um DataFrame do Pandas para exibir na tela
        df_lotes = pd.DataFrame(lotes_data)
        
        # Se o usuário digitou algo no filtro, a gente filtra o DataFrame
        if filtro_pesquisa:
            # O .str.contains permite busca parcial, case-insensitive (False)
            df_lotes = df_lotes[df_lotes['Código do Lote'].str.contains(filtro_pesquisa, case=False, na=False)]
        
        # Exibe a tabela interativa
        st.dataframe(df_lotes, use_container_width=True, hide_index=True)
        
        # Resumo
        st.caption(f"Mostrando {len(df_lotes)} lote(s) encontrados.")
    else:
        st.info("Nenhum lote encontrado no banco de dados no momento.")

with col_suporte:
    st.markdown("### 🤖 Assistente EISA")
    
    # INICIALIZA A MEMÓRIA DA TELA
    # O Streamlit recarrega a página toda vez que clica em algo. 
    # O session_state faz com que o histórico não seja apagado.
    if "mensagens_chat" not in st.session_state:
        st.session_state.mensagens_chat = [
            {"role": "assistant", "content": "Olá! Como posso ajudar?"}
        ]

    # CONTAINER DO CHAT: Exibe todo o histórico gravado na tela
    caixa_chat = st.container(height=400)
    with caixa_chat:
        for msg in st.session_state.mensagens_chat:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

    # INPUT DE CHAT: A barra de digitação que fica embaixo
    if prompt_usuario := st.chat_input("Digite sua mensagem aqui..."):
        
        # 1. Mostra a mensagem do usuário na tela e salva no estado
        with caixa_chat:
            with st.chat_message("user"):
                st.write(prompt_usuario)
        st.session_state.mensagens_chat.append({"role": "user", "content": prompt_usuario})
        
        # 2. Prepara o Payload para a API (Enviando o histórico junto!)
        payload = {
            "pergunta": prompt_usuario,
            "telaAtual": status_tela,
            "dadosContextuais": {
                "filtro_digitado_na_tela": filtro_pesquisa
            },
            # Enviamos tudo, EXCETO a última mensagem que acabamos de colocar, 
            # pois ela já vai no campo "pergunta"
            "historico": st.session_state.mensagens_chat[:-1] 
        }
        
        api_url = "http://localhost:8000/chat"
        
        # 3. Chama a API e mostra a resposta da IA
        with caixa_chat:
            with st.chat_message("assistant"):
                with st.spinner("Analisando..."):
                    try:
                        response_ia = requests.post(api_url, json=payload, timeout=40)
                        if response_ia.status_code == 200:
                            resposta_texto = response_ia.json().get("resposta")
                            st.write(resposta_texto)
                            # Salva a resposta da IA na memória para a próxima rodada
                            st.session_state.mensagens_chat.append({"role": "assistant", "content": resposta_texto})
                            
                            # Dica visual se houver sucesso num update
                            if "sucesso" in resposta_texto.lower():
                                st.info("🔄 Atualize a tela para ver os novos saldos na tabela.")
                        else:
                            st.error(f"Erro na API (Status {response_ia.status_code}): {response_ia.text}")
                    except Exception as e:
                        st.error(f"Falha de conexão: {e}")

st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("WL Trading - Módulo de Gestão de Estoque v1.1 (PoC MBA USP)")