import streamlit as st

st.set_page_config(
    page_title="Portal - Suporte",
    page_icon="☕",
    layout="wide"
)

st.title("☕ Bem-vindo ao Portal de Suporte")
st.markdown("""
    Use o menu lateral à esquerda para navegar entre as ferramentas do sistema:
    
    * **Consulta de Lotes:** Verifique saldos e históricos.
    * **Classificação:** Criação de lotes.
    * **Ficha de Compra:** Criar contratos.
""")

st.info("Selecione uma opção no menu ao lado para começar.")