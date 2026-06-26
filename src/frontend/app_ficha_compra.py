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
    # ordem: o usuário escolhe a qualidade e o estado primeiro
    qualidade = st.selectbox("Qualidade (Tipo de Café)", ["", "Arábica", "Conillon"])
    estado = st.selectbox("Estado de Origem", ["", "SP", "MG", "ES", "BA", "PR", "RO"])
    cidade = st.text_input("Cidade de Origem")
    tipo_cafe = st.selectbox("Estado do Produto (Embalagem)", ["Em Grão", "Cereja"])
    
# --- LÓGICA DE FILTRAGEM DINÂMICA VIA API ---
fornecedores_disponiveis = []
fornecedor_bloqueado = True
label_placeholder = "Selecione primeiro a Qualidade e o Estado"

# Só dispara o GET para a API se ambos os campos estiverem preenchidos pelo usuário
if qualidade != "" and estado != "":
    try:
        # Faz a chamada GET para o FastAPI passando os parâmetros na URL
        api_get_url = f"http://localhost:8000/fornecedores?tipo_cafe={qualidade}&estado={estado}"
        response_get = requests.get(api_get_url, timeout=5)
        
        if response_get.status_code == 200:
            fornecedores_disponiveis = response_get.json().get("fornecedores", [])
            
            if len(fornecedores_disponiveis) > 0:
                fornecedor_bloqueado = False
                label_placeholder = "Selecione um fornecedor homologado"
            else:
                label_placeholder = "Nenhum fornecedor ativo atende estes critérios"
    except Exception:
        st.error("Falha ao carregar fornecedores: O backend FastAPI está offline.")

with col1:
    # O selectbox herda as propriedades dinâmicas e o estado de bloqueado (disabled)
    if bloqueado_fornecedor_ou_vazio := fornecedor_bloqueado:
        fornecedor = st.selectbox("Fornecedor", [label_placeholder], disabled=True)
    else:
        fornecedor = st.selectbox("Fornecedor", fornecedores_disponiveis)


with col2:
    preco = st.number_input("Preço do Contrato (R$)", min_value=0.0, format="%.2f")
    quantidade = st.number_input("Quantidade (Sacas de 60kg)", min_value=0.0)
    frete = st.selectbox("Modalidade de Frete", ["CIF", "FOB"])
    comprador = st.text_input("Funcionário Comprador")

st.markdown("---")

# 3. --- ÁREA DO SUPORTE (CHATBOT COM MEMÓRIA) ---
col_espaco, col_ajuda = st.columns([0.6, 0.4])

with col_ajuda:
    with st.popover("💬 Precisa de Ajuda com esta Ficha?", use_container_width=True):
        st.markdown("### 🤖 Assistente EISA - Aquisição")
        st.caption(f"Contexto: {status_tela}")
        
        # INICIALIZA A MEMÓRIA DO CHAT
        if "mensagens_chat_ficha" not in st.session_state:
            st.session_state.mensagens_chat_ficha = [
                {"role": "assistant", "content": "Olá! Como posso ajudar?"}
            ]

        # CONTAINER DO CHAT: Exibe histórico gravado
        caixa_chat = st.container(height=350)
        with caixa_chat:
            for msg in st.session_state.mensagens_chat_ficha:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
        
        # INPUT DE CHAT 
        if prompt_usuario := st.chat_input("Ex: Qual a regra de frete para este fornecedor?"):
            
            # 1. Mostra a mensagem do usuário na tela e salva no estado
            with caixa_chat:
                with st.chat_message("user"):
                    st.write(prompt_usuario)
            st.session_state.mensagens_chat_ficha.append({"role": "user", "content": prompt_usuario})
            
            # 2. Prepara o Payload para a API - Snapshot Completo + Histórico
            payload = {
                "pergunta": prompt_usuario,
                "telaAtual": status_tela,
                "dadosContextuais": {
                    "fornecedor": fornecedor if not fornecedor_bloqueado else "Nenhum selecionado",
                    "cidade": cidade,
                    "estado": estado,
                    "tipoCafe": tipo_cafe,
                    "qualidade": qualidade,
                    "preco": preco,
                    "quantidade": quantidade,
                    "frete": frete,
                    "comprador": comprador
                },
                # Envia tudo, EXCETO a última mensagem que acabou de colocar
                "historico": st.session_state.mensagens_chat_ficha[:-1]
            }
            
            api_url = "http://localhost:8000/chat"
            
            # 3. Chama a API e mostra a resposta da IA
            with caixa_chat:
                with st.chat_message("assistant"):
                    with st.spinner("Consultando regras de negócio..."):
                        try:
                            response = requests.post(api_url, json=payload, timeout=40)
                            
                            if response.status_code == 200:
                                resposta_ia = response.json().get("resposta")
                                st.write(resposta_ia)
                                # Salva a resposta da IA na memória
                                st.session_state.mensagens_chat_ficha.append({"role": "assistant", "content": resposta_ia})
                            else:
                                st.error(f"Erro na API (Status {response.status_code}): {response.text}")
                        except Exception as e:
                            st.error(f"Falha de conexão com o backend FastAPI: {e}")

# Rodapé pra fechar layout
st.markdown("<br><br>", unsafe_allow_html=True)
st.caption("WL Trading - Módulo de Aquisição v1.2")