## 1. Dependência e configuração

- [x] 1.1 Adicionar `azure-monitor-opentelemetry` às dependências do backend
      (`src/api/RAG.Api/requirements.txt` ou equivalente) e verificar que `pip install` conclui
      sem erro
- [x] 1.2 Documentar a variável de ambiente `APPLICATIONINSIGHTS_CONNECTION_STRING` (ex.: em
      `.env.example`, se existir) e verificar que o app sobe normalmente sem ela definida
      — documentada no `README.md` (não existe `.env.example` no projeto); confirmado via
      `python -c "import main"` sem a variável definida (import limpo, sem erro).

## 2. Instrumentação no startup

- [x] 2.1 Chamar `configure_azure_monitor()` em `main.py`, condicionalmente (só se
      `APPLICATIONINSIGHTS_CONNECTION_STRING` estiver definida), antes da criação de
      `app = FastAPI(...)`; verificar que a aplicação inicializa normalmente tanto com quanto
      sem a variável definida
      — IMPORTANTE (achado durante a implementação, não previsto no design.md original): não
      basta chamar antes de `app = FastAPI(...)`; precisa rodar antes do próprio
      `from fastapi import FastAPI`, porque `configure_azure_monitor()` instrumenta via
      monkey-patch do atributo `fastapi.FastAPI`, e `from X import Y` já copia a referência
      antiga se executado antes. Confirmado experimentalmente: com a ordem errada,
      `type(app).__name__` ficava `FastAPI` (não instrumentado); reordenando, vira
      `_InstrumentedFastAPI`. `main.py` foi ajustado para importar/chamar
      `configure_azure_monitor()` no topo do arquivo, antes de qualquer import do FastAPI.
- [ ] 2.2 Confirmar que a auto-instrumentação do FastAPI está ativa rodando a API localmente
      com a connection string configurada, fazendo uma requisição de teste e checando se o
      span de requisição aparece no Application Insights
      — requer recurso Application Insights real; verificação manual do usuário.

## 3. Verificação de dependências externas rastreadas

- [ ] 3.1 Verificar se chamadas via `requests`/`urllib3` (Azure AI Search, Azure OpenAI) em
      `rag_service.py` aparecem automaticamente como dependências no Application Insights
      — requer recurso real; verificação manual do usuário.
- [ ] 3.2 Verificar se consultas via `pyodbc` (`database.py`) aparecem como dependências SQL; se
      não aparecerem, envolver `get_db_connection()`/as chamadas de query com instrumentação
      manual (`opentelemetry-instrumentation-dbapi`) e verificar novamente
      — fallback já escrito e comentado em `database.py` (não ativo por padrão); requer
      verificação com recurso real antes de habilitar. `opentelemetry-instrumentation-dbapi`
      confirmado como dependência transitiva já instalada pela distro (versão beta).

## 4. Verificação de segurança (sem PII na telemetria)

- [x] 4.1 Revisar todo código de instrumentação adicionado e confirmar que nenhum
      `span.set_attribute` inclui `pergunta`, argumentos de tools ou valores do `cofre` de PII
      (`security_service.py`), conforme a convenção definida em `design.md`
      — confirmado via grep em `src/api/RAG.Api/`: nenhum `span.set_attribute`,
      `request_hook`/`response_hook` ou `capture_headers` customizado adicionado; apenas
      instrumentação automática padrão (sem captura de corpo de requisição/resposta).
- [ ] 4.2 Fazer uma requisição de teste ao `POST /chat` com um dado pessoal (ex.: CNPJ) no corpo
      e verificar manualmente no Application Insights que o dado não aparece em texto claro em
      nenhum span registrado
      — requer recurso real; verificação manual do usuário.

## 5. Tratamento de exceções

- [ ] 5.1 Forçar um erro não tratado (ex.: desligar a conexão SQL temporariamente) e verificar
      que a exceção correspondente aparece registrada no Application Insights com tipo e stack
      trace, e que a API ainda responde ao cliente com o erro tratado
      — requer recurso real; verificação manual do usuário.
