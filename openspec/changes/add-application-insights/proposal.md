## Why

O rag_project ainda não tem visibilidade de APM: latência de requisições, exceções não
tratadas e desempenho das dependências externas (Azure SQL, Azure AI Search, Azure OpenAI) não
são monitorados sistematicamente. Isso dificulta diagnosticar problemas de performance e
detectar falhas silenciosas em produção. A tabela `EventosAuditoria` já existente cobre
auditoria de negócio (o que a IA fez em cada tool call), mas não cobre a saúde técnica da
aplicação como um todo.

## What Changes

- Adicionar Application Insights / Azure Monitor à API FastAPI via OpenTelemetry (pacote
  `azure-monitor-opentelemetry`).
- Instrumentar automaticamente requisições HTTP recebidas, exceções não tratadas e chamadas de
  dependência (Azure SQL, Azure AI Search, chamadas HTTP ao Azure OpenAI).
- Configurar a conexão via variável de ambiente com a connection string do Application Insights
  (o provisionamento do recurso no Azure é responsabilidade do usuário, fora do escopo deste
  change).
- Garantir que a telemetria fique desabilitada de forma segura se a variável de ambiente não
  estiver definida, sem quebrar a aplicação em ambiente local/dev.

## Capabilities

### New Capabilities
- `apm-telemetry`: telemetria de APM (latência, exceções, dependências) da API via Application
  Insights/OpenTelemetry.

### Modified Capabilities
(nenhuma — a tabela `EventosAuditoria` de auditoria de negócio já existe e não faz parte deste
change)

## Impact

- `src/api/RAG.Api/main.py` — inicialização do Azure Monitor/OpenTelemetry no startup/lifespan
  da aplicação FastAPI.
- `src/api/RAG.Api/services/database.py`, `rag_service.py` — chamadas a SQL, Azure AI Search e
  Azure OpenAI passam a ser rastreadas automaticamente como dependências pela instrumentação,
  sem necessariamente alterar a lógica de negócio existente.
- Nova dependência de projeto: `azure-monitor-opentelemetry`.
- Nova variável de ambiente: connection string do Application Insights.
