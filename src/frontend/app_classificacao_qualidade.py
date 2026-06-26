import streamlit as st
import requests

# 1. Configuração da página
st.set_page_config(page_title="EISA - Classificação de Lote", layout="wide", page_icon="🔬")

# Título e Contexto Global
status_tela = "Classificação de Lote (Laudo Técnico)"
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

# 3. --- ÁREA DO SUPORTE INTELIGENTE (RAG) ---
col_espaco, col_ajuda = st.columns([0.7, 0.3])

with col_ajuda:
    with st.popover("💬 Dúvidas sobre a Classificação?", use_container_width=True):
        st.markdown("### 🤖 Assistente EISA - Nível Técnico")
        st.caption(f"Contexto: {status_tela}")
        
        pergunta = st.text_area(
            "Descreva a situação:",
            placeholder="Ex: O sistema bloqueou meu laudo. O que faço com esse café?",
            key="campo_pergunta_laudo"
        )
        
        if st.button("Consultar IA Técinca", use_container_width=True):
            if not pergunta:
                st.warning("Por favor, descreva sua dúvida.")
            else:
                # Payload Contextual: Fotografia do estado atual da tela do classificador
                payload = {
                    "pergunta": pergunta,
                    "telaAtual": status_tela,
                    "dadosContextuais": {
                        "lote_referencia": lote_referencia,
                        "umidade_informada": umidade,
                        "peneira": peneira,
                        "total_defeitos": defeitos,
                        "tipo_bebida": tipo_bebida,
                        "nota_sca": nota_sca,
                        "status_bloqueio_tela": bloqueio_qualidade
                    }
                }
                
                api_url = "http://localhost:8000/chat"
                
                try:
                    with st.spinner("Analisando padrões da COB e manuais de qualidade..."):
                        response = requests.post(api_url, json=payload, timeout=30)
                        
                        if response.status_code == 200:
                            st.success("**Diagnóstico da IA:**")
                            st.write(response.json().get("resposta"))
                        else:
                            st.error(f"Erro na API: {response.status_code}")
                except Exception:
                    st.error("API FastAPI Offline. Verifique se o backend está rodando na porta 8000.")

st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("WL Trading - Módulo Técnico v1.0 (PoC)")