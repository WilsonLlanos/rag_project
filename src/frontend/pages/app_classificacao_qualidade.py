import streamlit as st
import requests
import os

# 1. Configuração da página
st.set_page_config(page_title="Classificação de Lote", layout="wide", page_icon="🔬")

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

# Título e Contexto Global
status_tela = "Classificação de Lote"
st.title(f"🔬 Sistema Café-Trade: {status_tela}")
st.markdown("---")

# 2. Formulário do Laudo Técnico
col1, col2 = st.columns(2)

with col1:
    lote_referencia = st.text_input("Número do Lote ou Ficha de Compra", placeholder="Ex: LOTE-2026-001")
    umidade = st.number_input("Umidade do Grão (%)", min_value=0.0, max_value=100.0, format="%.2f", step=0.5)
    peneira = st.selectbox("Peneira (Granulometria)", ["", "17/18", "15/16", "13/14", "Moca"])
    
with col2:
    defeitos = st.number_input("Defeitos (Pontos por 300g)", min_value=0, step=1)
    tipo_bebida = st.selectbox("Tipo de Bebida (Prova de Xícara)", ["", "Estritamente Mole", "Mole", "Apenas Mole", "Dura", "Riado", "Rio", "Rio Zona"])
    nota_sca = st.number_input("Nota da Prova (SCA Score)", min_value=0.0, max_value=100.0, format="%.2f", step=0.5)

# --- LÓGICA DE VALIDAÇÃO DETERMINÍSTICA (HARDCODED) ---
bloqueio_qualidade = False
st.markdown("<br>", unsafe_allow_html=True)

# Regra 3 do manual: Acima de 13% gera bloqueio por risco de mofo
if umidade > 13.0:
    st.error("⛔ ERRO DE COMPLIANCE: Umidade acima de 13% detectada. Risco de Mofo. O lote está bloqueado para venda.")
    bloqueio_qualidade = True

# Regra implícita do FAQ: Mais de 360 defeitos gera alerta visual (não bloqueia, mas avisa)
if defeitos > 360:
    st.warning("⚠️ ALERTA: Amostra com mais de 360 defeitos. Verifique a destinação do lote (PVA).")

# Botão de Ação
if st.button("✅ Finalizar Laudo", type="primary", disabled=bloqueio_qualidade):
    if not lote_referencia:
        st.warning("Por favor, informe o Número do Lote para vincular o laudo.")
    else:
        st.success(f"Laudo do lote {lote_referencia} finalizado e registrado com sucesso!")

st.markdown("---")

# 3. --- ÁREA DO CHATBOT ---
col_espaco, col_ajuda = st.columns([0.7, 0.3])

with col_ajuda:
    with st.popover("Dúvidas? Fale com a IA", use_container_width=True):
        st.markdown("### 🤖 Assistente Técnico")
        
        # INICIALIZA A MEMÓRIA DA TELA
        if "mensagens_chat_laudo" not in st.session_state:
            st.session_state.mensagens_chat_laudo = [
                {"role": "assistant", "content": "Olá! Sou seu assistente de classificação. Como posso ajudar com o laudo deste lote?"}
            ]

        # CONTAINER DO CHAT: Exibe todo o histórico gravado na tela
        caixa_chat = st.container(height=300)
        with caixa_chat:
            for msg in st.session_state.mensagens_chat_laudo:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        # INPUT DE CHAT: A barra de digitação que envia automaticamente ao apertar Enter
        if prompt_usuario := st.chat_input("Digite sua dúvida sobre a classificação..."):
            
            # 1. Mostra a mensagem do usuário na tela e salva no estado
            with caixa_chat:
                with st.chat_message("user"):
                    st.write(prompt_usuario)
            st.session_state.mensagens_chat_laudo.append({"role": "user", "content": prompt_usuario})
            
            # 2. Prepara o Payload Contextual
            payload = {
                "pergunta": prompt_usuario,
                "telaAtual": status_tela,
                "dadosContextuais": {
                    "lote_referencia": lote_referencia,
                    "umidade_informada": umidade,
                    "peneira": peneira,
                    "total_defeitos": defeitos,
                    "tipo_bebida": tipo_bebida,
                    "nota_sca": nota_sca,
                    "status_bloqueio_tela": bloqueio_qualidade
                },
                "historico": st.session_state.mensagens_chat_laudo[:-1]
            }
            
            api_url = os.getenv("API_URL", "http://localhost:8000/chat")
            
            # 3. Chama a API e mostra a resposta da IA
            with caixa_chat:
                with st.chat_message("assistant"):
                    with st.spinner("Analisando padrões da COB e manuais de qualidade..."):
                        try:
                            response_ia = requests.post(api_url, json=payload, timeout=40)
                            
                            if response_ia.status_code == 200:
                                dados_json = response_ia.json()
                                resposta_texto = dados_json.get("resposta")
                                erro_mensagem = dados_json.get("erro")

                                if resposta_texto:
                                    st.write(resposta_texto)
                                    # Salva a resposta da IA na memória para a próxima rodada
                                    st.session_state.mensagens_chat_laudo.append({"role": "assistant", "content": resposta_texto})
                                elif erro_mensagem:
                                    st.error(f"Erro na resposta da IA: {erro_mensagem}")
                            else:
                                st.error(f"Erro na API (Status {response_ia.status_code}): {response_ia.text}")
                        except Exception as e:
                            st.error(f"Falha de conexão: {e}")

st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("WL Trading - Módulo Técnico v1.1 (PoC)")