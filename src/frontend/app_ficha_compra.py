import streamlit as st
import requests

# 1. Configuração da página
st.set_page_config(page_title="EISA - Ficha de Compra", layout="wide", page_icon="☕")

# Título e Contexto Global
status_tela = "Ficha de Compra"
st.title(f"☕ Sistema Café-Trade: {status_tela}")
st.markdown("---")

# 2. Formulário da Ficha de Compra
col1, col2 = st.columns(2)

with col1:
    fornecedor = st.text_input("Fornecedor", placeholder="Nome da Fazenda ou Produtor")
    cidade = st.text_input("Cidade de Origem")
    tipo_cafe = st.selectbox("Tipo de Café", ["Em Grão", "Cereja"])
    qualidade = st.selectbox("Qualidade", ["Arábica", "Conillon"])

with col2:
    preco = st.number_input("Preço do Contrato (R$)", min_value=0.0, format="%.2f")
    quantidade = st.number_input("Quantidade (Sacas de 60kg)", min_value=0.0)
    frete = st.selectbox("Modalidade de Frete", ["CIF", "FOB"])
    comprador = st.text_input("Funcionário Comprador")

st.markdown("---")

# 3. --- ÁREA DO SUPORTE (OCULTA/EXPANSÍVEL) ---
# Usando o Popover para um visual moderno e limpo
col_espaco, col_ajuda = st.columns([0.7, 0.3])

with col_ajuda:
    with st.popover("💬 Precisa de Ajuda com esta Ficha?", use_container_width=True):
        st.markdown("### 🤖 Assistente EISA")
        st.caption(f"Contexto: {status_tela}")
        
        pergunta = st.text_area(
            "Descreva sua dúvida ou o erro:",
            placeholder="Ex: Qual a regra de frete para este fornecedor?",
            key="campo_pergunta"
        )
        
        if st.button("Consultar IA", use_container_width=True):
            if not pergunta:
                st.warning("Por favor, descreva sua dúvida.")
            else:
                # O "Pulo do Gato" para o seu TCC: O Snapshot Completo
                payload = {
                    "pergunta": pergunta,
                    "telaAtual": status_tela,
                    "dadosContextuais": {
                        "fornecedor": fornecedor,
                        "cidade": cidade,
                        "tipoCafe": tipo_cafe,
                        "qualidade": qualidade,
                        "preco": preco,
                        "quantidade": quantidade,
                        "frete": frete,
                        "comprador": comprador
                    }
                }
                
                # Endereço da sua API C#
                api_url = "http://localhost:5024/api/Chat/pergunta" 
                
                try:
                    with st.spinner("Consultando manuais e regras de negócio..."):
                        # Chamada real para sua API
                        response = requests.post(api_url, json=payload, timeout=30)
                        
                        if response.status_code == 200:
                            st.success("**Orientação da IA:**")
                            st.write(response.json().get("resposta"))
                        else:
                            st.error(f"Erro na API: {response.status_code}")
                except Exception as e:
                    st.error("API C# Offline. Verifique se o projeto RAG.Proj.Api está rodando.")

# Rodapé simples para fechar o layout
st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("WL Trading - Módulo de Aquisição v1.0 (PoC MBA USP)")