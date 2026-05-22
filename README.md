# Suporte Inteligente N1 com RAG

Este projeto apresenta uma Prova de Conceito (PoC) de um sistema de suporte técnico de Nível 1, utilizando arquitetura **RAG (Retrieval-Augmented Generation)** para resolver a carência de documentação em sistemas de trading de café.

## 🚀 Arquitetura da Solução
A solução é composta por uma estrutura de microserviços integrada ao ecossistema Azure:
- **Frontend:** Streamlit (Python) para simulação de interfaces e interação com o usuário.
- **Backend:** Web API em .NET 9 utilizando **Semantic Kernel** para orquestração de LLM.
- **IA/Dados:** Azure OpenAI (GPT-4o) e Azure AI Search (Vector Store).

## 🛠️ Tecnologias Utilizadas
- .NET 9 SDK
- Python 3.10+ (Streamlit)
- Microsoft Semantic Kernel
- Azure OpenAI Service & Azure AI Search

## 📋 Como Executar (Ambiente de Desenvolvimento)

### 1. Backend (.NET)
Navegue até a pasta da API e restaure as dependências:
```bash
cd src/api/SuporteIA.Api
dotnet restore
dotnet run
