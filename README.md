# Suporte Inteligente N1 com RAG

Este projeto apresenta uma Prova de Conceito (PoC) de um sistema para suporte de Nível 1, usando arquitetura **RAG (Retrieval-Augmented Generation)** Híbrida que utiliza banco vetorial que armazena documentação e regras dos sistema e negócio, e banco relacional para consultas e alterações específicas ativadas pelo LLM através de Tool Callings. Esta solução integra boas práticas de Engenharia de Dados, IA e segurança da informação

## Arquitetura da Solução

A solução foi desenvolvida visando microsserviços ágeis, nativos e integrados ao ecossistema Azure:

* **Frontend**: Streamlit (Python) para simulação de interfaces e injeção do "Estado da Tela" no contexto da IA.
* **Backend**: API REST em **FastAPI** (Python) atuando como orquestrador. Utiliza os SDKs nativos do Azure para *Tool Calling/Function Calling* via JSON Schemas com o LLM.
* **IA e Busca**: Azure OpenAI (GPT-4o) para raciocínio e Azure AI Search para busca vetorial de manuais (Markdown).
* **Banco de Dados**: Azure SQL Database (camada Serverless/Basic) gerindo o negócio (Lotes e Resíduos Decimais), isolado da IA pelo Princípio do Menor Privilégio.
* **Governança e Segurança**: **Microsoft Presidio** rodando localmente no backend para detecção de PII (via NER) e anonimização em tempo real, garantindo conformidade com a LGPD.

## Tecnologias Utilizadas

* Python 3.10+
* FastAPI & Uvicorn (Backend e Swagger UI nativo)
* Streamlit (Interface do Usuário)
* Azure OpenAI SDK & Azure AI Search SDK (Python)
* Microsoft Presidio (Anonimização de Dados)
* PyODBC (Conexão Segura com Azure SQL)

## Estrutura do Repositório

rag_project/
├── src/
│   ├── api/              # Backend Inteligente (FastAPI)
│   │   ├── main.py       # Configuração das rotas (Endpoints via Pydantic)
│   │   ├── rag_service.py # Cérebro: Tool Calling, System Prompt e Integração OpenAI
│   │   └── indexer.py    # ETL Vetorial (Fatiamento e Upsert para o Azure AI Search)
│   └── frontend/         # Interface e captura de contexto de tela
│       └── app.py        # Aplicação Streamlit
├── docs/                 # Documentação acadêmica (LaTeX/TCC - Padrão USPSC)
├── .env                  # Variáveis de ambiente (ignorado no Git)
├── .gitignore            # Proteção de chaves e arquivos temporários
└── README.md

Como Executar (Ambiente de Desenvolvimento)

## Pré-requisitos do Sistema
Devido à integração com o SQL Server via pyodbc, é necessário que o ambiente possua o driver ODBC correto instalado no SO antes da instalação das dependências Python:

Windows/Linux/macOS: Instalação do Microsoft ODBC Driver 18 for SQL Server - https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver17

1. Backend (FastAPI)
Navegue até a pasta da API, instale as dependências e inicie o servidor:

cd src/api
pip install -r requirements.txt
uvicorn main:app --reload

A API fica disponível em http://localhost:8000

2. Documentação da API (Swagger Interativo)
O FastAPI gera a documentação interativa automaticamente. Para testar os endpoints de IA de forma isolada, acesse:
http://localhost:8000/docs

3. Frontend (Streamlit)
Em um novo terminal, navegue até a pasta do frontend, instale as dependências (caso seja um arquivo separado) e execute o app:

cd src/frontend
pip install -r requirements.txt
streamlit run app.py

Configuração e Segurança
O projeto adota uma prática de Privacy by Design. Nenhuma chave ou dado sensível é exposto. Crie um arquivo .env na raiz do projeto (ou na pasta da API) baseado no modelo abaixo para se conectar aos serviços do Azure:

# Azure OpenAI
AZURE_OPENAI_ENDPOINT="SUA_URL_DO_OPENAI"
AZURE_OPENAI_API_KEY="SUA_CHAVE_DO_OPENAI"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o"
OPENAI_API_VERSION="2024-02-15-preview"

# Azure AI Search
AZURE_SEARCH_ENDPOINT="SUA_URL_DO_SEARCH"
AZURE_SEARCH_API_KEY="SUA_CHAVE_ADMIN_DO_SEARCH"
AZURE_SEARCH_INDEX_NAME="indice-manuais-cafe"

# Azure SQL Database
SQL_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=tcp:seu-servidor.database.windows.net,1433;Database=seu-banco;Uid=seu-usuario;Pwd=sua-senha;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"