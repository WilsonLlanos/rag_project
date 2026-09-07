## Context

A API é um único serviço FastAPI (`src/api/RAG.Api/main.py`) com um `lifespan` que hoje só
garante a existência da tabela `EventosAuditoria` (auditoria de negócio, já existente e fora
deste change). O acesso a SQL é feito via `pyodbc` direto (`services/database.py`, sem ORM), o
Azure AI Search e o Azure OpenAI são chamados a partir de `services/rag_service.py`, e
`services/security_service.py` mascara PII antes de qualquer dado sensível circular pelo
sistema. Ver `proposal.md` - Why para a motivação.

## Goals / Non-Goals

**Goals:**
- Habilitar telemetria de APM (requisições, exceções, dependências) com o mínimo de código,
  usando a distro oficial da Microsoft para Python.
- Garantir que nenhuma PII chegue à telemetria, mesmo que só de forma acidental no futuro.
- Não quebrar a aplicação quando o recurso Application Insights ainda não estiver provisionado.

**Non-Goals:**
- Não mexe na tabela `EventosAuditoria` (auditoria de negócio) nem duplica seu conteúdo.
- Não implementa tracing distribuído entre múltiplos serviços (há apenas um serviço).
- Não cria dashboards ou alertas customizados no Azure — isso é configuração no portal, fora do
  código.

## Decisions

- **Usar `azure-monitor-opentelemetry` (a distro oficial) em vez de montar
  OpenTelemetry SDK + exporter manualmente.** É o caminho recomendado pela Microsoft para
  Python, resume a configuração a uma chamada (`configure_azure_monitor()`) e já inclui
  auto-instrumentação de FastAPI, `requests`/`urllib3` (usados pelos SDKs do Azure) e exceções.
  Alternativa descartada: `opentelemetry-sdk` + `azure-monitor-opentelemetry-exporter` puros —
  mais código de configuração sem ganho real para este projeto.

- **Nome da variável de ambiente: `APPLICATIONINSIGHTS_CONNECTION_STRING`.** É o nome padrão
  que `configure_azure_monitor()` já lê automaticamente, e segue o mesmo padrão de nomenclatura
  usado hoje para `AZURE_SQL_CONNECTION_STRING` em `database.py`.

- **Inicialização condicional em `main.py`, antes da criação do `app = FastAPI(...)`.**
  `configure_azure_monitor()` só é chamado se a variável de ambiente estiver definida — isso
  satisfaz o requisito de spec "Telemetria opcional e não bloqueante" sem precisar de try/except
  ao redor de toda a inicialização.

- **Nenhum atributo customizado de span com conteúdo de request/resposta.** A
  auto-instrumentação padrão do FastAPI já registra apenas rota, método e status — não o corpo
  da requisição. A regra para qualquer código futuro que adicionar telemetria manual (spans ou
  atributos customizados) é: nunca incluir `pergunta`, argumentos de tools, ou qualquer valor
  vindo do `cofre` de PII (`security_service.py`) como atributo de span.

## Risks / Trade-offs

- [Risco] `pyodbc` pode não estar entre as bibliotecas auto-instrumentadas pela distro (a lista
  oficial cobre principalmente `psycopg2`, `pymysql`, `sqlite3`) → Mitigação: validar durante a
  implementação rodando uma consulta real e conferindo se aparece como dependência SQL no
  Application Insights; se não aparecer, envolver `get_db_connection()`/as chamadas de query com
  instrumentação manual (`opentelemetry-instrumentation-dbapi`).
- [Risco] Volume de telemetria pode gerar custo de ingestão conforme o tráfego cresce →
  Mitigação: a distro suporta sampling via parâmetro de configuração; não é necessário agora
  (volume baixo, projeto de TCC), mas fica documentado aqui para quando escalar.
- [Risco] Vazamento futuro de PII se alguém adicionar telemetria manual sem seguir a convenção
  acima → Mitigação: convenção documentada nesta decisão de design; qualquer PR futuro que
  adicione `span.set_attribute` deve ser revisado contra esta regra.

## Migration Plan

Não há migração de dados ou schema. Passos de deploy: instalar a dependência, o usuário
provisiona o recurso Application Insights no Azure (fora deste change) e define
`APPLICATIONINSIGHTS_CONNECTION_STRING` no ambiente de produção. Rollback: remover a chamada
`configure_azure_monitor()` e a dependência — não há estado persistido para desfazer.

## Open Questions

- Confirmar se `pyodbc` é coberto pela auto-instrumentação da distro ou exige instrumentação
  manual — resolvido durante o apply (ver Risco acima), não muda a spec nem a divisão de
  tarefas.
