## Context

A API é um único serviço FastAPI (`src/api/RAG.Api/main.py`). O acesso a SQL é feito via
`pyodbc` direto (`services/database.py`, sem ORM) — o padrão já estabelecido para persistência
de eventos é uma função `criar_tabela_<x>_se_nao_existir()` (`CREATE TABLE IF NOT EXISTS` cru,
chamada no `lifespan`) mais uma função `registrar_evento_<x>(...)` (INSERT com try/except que só
loga aviso em falha), hoje usado só para `EventosAuditoria`. A orquestração do LLM
(`services/rag_service.py`) chama `openai_client.chat.completions.create(...)` dentro de um loop
`while True:` (padrão ReAct — pode iterar mais de uma vez por pergunta do usuário) e
`openai_client.embeddings.create(...)` na busca vetorial; nenhuma das duas lê `.usage` hoje. Ver
`proposal.md` - Why para a motivação de negócio (Cap. 5 do TCC).

## Goals / Non-Goals

**Goals:**
- Capturar de forma confiável o consumo de tokens de toda chamada ao Azure OpenAI feita pela API,
  sem depender de infraestrutura externa (Application Insights, billing do Azure).
- Permitir somar o custo de uma pergunta do usuário mesmo quando ela dispara múltiplas chamadas
  ao modelo.
- Manter o mesmo padrão estrutural já usado no projeto para `EventosAuditoria`, para consistência
  e menor superfície de revisão.

**Non-Goals:**
- Não substitui nem se conecta à change `add-application-insights` (`apm-telemetry`) — aquela
  cobre telemetria técnica (latência, exceções, dependências) e seu `design.md` exclui
  explicitamente métricas de negócio; esta capability é sobre custo de consumo de LLM, uma
  preocupação de FinOps, não de APM.
- Não implementa dashboards, alertas ou monitoramento contínuo de produção — o objetivo é
  permitir rodar cenários de teste controlados e consultar a tabela via SQL para alimentar a
  análise de viabilidade econômica do TCC.
- Não busca preços de tokens dinamicamente de nenhuma API de billing do Azure — os preços são
  constantes configuráveis, definidas por quem opera o projeto.
- Não calcula custo de tool calls (chamadas SQL) — isso já é coberto, em duração, pela tabela
  `EventosAuditoria` existente; tool calls não consomem tokens de LLM diretamente.

## Decisions

- **Tabela nova (`EventosConsumoLLM`), não reaproveitar `EventosAuditoria`.** O schema de
  `EventosAuditoria` foi desenhado para tool calls (`NomeFerramenta`, `ArgumentosSeguro`) e o
  próprio código-fonte documenta que ela já tem um consumidor externo definido (o projeto de
  multiagentes de incidentes) — misturar um propósito diferente (custo de LLM) nesse schema
  arriscaria quebrar esse consumidor e forçaria colunas sem sentido semântico em metade das
  linhas. Alternativa descartada: adicionar colunas de tokens/custo em `EventosAuditoria` —
  rejeitada por esse motivo.

- **Guardar tokens brutos além do custo calculado.** `CustoEstimadoUsd` é calculado no momento do
  INSERT a partir dos preços vigentes em `config.py`, mas `PromptTokens`/`CompletionTokens`/
  `TotalTokens` também são persistidos — se o preço configurado precisar ser corrigido depois (ver
  Open Questions), o custo pode ser recalculado a partir dos tokens já capturados, sem precisar
  rodar os cenários de teste de novo.

- **`id_atendimento` gerado em `consultar_manuais_rag`, não em `main.py`.** É a função que já
  orquestra o loop ReAct e ambas as chamadas de LLM relevantes (via `_executar_busca_vetorial`
  para embeddings, e o `while True:` para chat); gerar o id ali evita ter que propagá-lo por uma
  camada HTTP que não precisa conhecer esse detalhe.

- **Schema de `EventosConsumoLLM`** (mesmo padrão de nomenclatura em português de
  `EventosAuditoria`):
  ```sql
  CREATE TABLE EventosConsumoLLM (
      Id INT IDENTITY(1,1) PRIMARY KEY,
      DataHora DATETIME2 DEFAULT SYSDATETIME(),
      IdAtendimento NVARCHAR(36) NOT NULL,
      TipoChamada NVARCHAR(20) NOT NULL,        -- 'Chat' ou 'Embedding'
      NomeDeployment NVARCHAR(100) NOT NULL,
      NumeroIteracaoReact INT NULL,             -- NULL para embedding
      PromptTokens INT NOT NULL,
      CompletionTokens INT NULL,                -- NULL para embedding
      TotalTokens INT NOT NULL,
      CustoEstimadoUsd DECIMAL(10,6) NOT NULL
  )
  ```

- **Settings de preço em `config.py`, com nomes genéricos e defaults calibrados para
  GPT-4o-mini** (modelo real em produção, confirmado pelo usuário): `preco_chat_entrada_usd_por_1k`,
  `preco_chat_saida_usd_por_1k`, `preco_embedding_usd_por_1k`. Os defaults seguem a tabela de
  preços pública do Azure OpenAI para GPT-4o-mini (deployment Standard/Global, sob demanda) no
  momento da escrita deste design — **precisam ser confirmados contra o preço vigente na região e
  no acordo de faturamento reais do usuário antes de qualquer número entrar no Cap. 5 do TCC** (ver
  Open Questions). Nomes genéricos (não amarrados a "gpt4o_mini") para não exigir renomear o
  schema se o deployment mudar de modelo no futuro.

- **Falha de registro não bloqueia a resposta.** Mesmo padrão de `registrar_evento_auditoria`:
  `try/except` ao redor do INSERT, só loga aviso — nunca propaga exceção para quem chamou
  `consultar_manuais_rag`.

## Risks / Trade-offs

- [Risco] Preço por token hardcoded em `config.py` fica desatualizado se o Azure reajustar preços
  → Mitigação: tokens brutos são sempre guardados (ver Decisions), permitindo recalcular o custo
  histórico sem precisar de nova coleta.
- [Risco] Chamada de embeddings não retorna `completion_tokens` (só `prompt_tokens` e
  `total_tokens`, que são iguais para embeddings) → Mitigação: coluna `CompletionTokens` é
  `NULL`-ável especificamente para esse caso, refletido na spec e no schema.
- [Risco] Gerar `id_atendimento` como `uuid` a cada chamada de `consultar_manuais_rag` tem custo
  de performance desprezível, mas precisa ser passado corretamente por todas as chamadas internas
  (fácil esquecer em uma delas e quebrar a correlação) → Mitigação: tarefa dedicada em `tasks.md`
  para revisar que as duas chamadas de LLM (`_executar_busca_vetorial` e o loop `while True:`)
  recebem o mesmo id.

## Migration Plan

Não há migração de dados existentes — tabela nova, criada automaticamente no primeiro startup da
API (mesmo padrão de `EventosAuditoria`). Rollback: remover a chamada de criação da tabela no
`lifespan` e a instrumentação em `rag_service.py`; a tabela `EventosConsumoLLM`, se já criada,
pode ser dropada manualmente sem afetar o restante do sistema (não tem nenhum consumidor externo
definido, ao contrário de `EventosAuditoria`).

## Open Questions

- **Confirmar os valores exatos de `preco_chat_entrada_usd_por_1k`, `preco_chat_saida_usd_por_1k`
  e `preco_embedding_usd_por_1k`** contra o preço vigente no portal do Azure OpenAI para a região
  e o acordo de faturamento reais do projeto, antes de usar qualquer custo calculado no Cap. 5 do
  TCC. Não muda a spec, o schema ou a divisão de tarefas — só o valor default em `config.py`, que
  pode ser ajustado depois de aplicado sem precisar recriar a tabela.
