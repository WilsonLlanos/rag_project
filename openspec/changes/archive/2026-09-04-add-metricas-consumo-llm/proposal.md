## Why

O rag_project não tem hoje nenhuma visibilidade sobre o consumo de tokens e o custo das chamadas
ao Azure OpenAI. A chamada de chat dentro do loop ReAct (`consultar_manuais_rag`) e a chamada de
embeddings (`_executar_busca_vetorial`) descartam o campo `.usage` da resposta da API — nenhum
token consumido é lido, somado ou persistido. Isso impede qualquer análise de custo real da
solução, necessária para a Análise de Viabilidade Econômica (Cap. 5) do TCC associado a este
projeto, que hoje só tem uma premissa de volume (1.000 chamados/mês) sem nenhum dado de custo
efetivo por atendimento. A tabela `EventosAuditoria` já existente cobre auditoria de tool calls
(o que a IA fez no banco relacional), mas não cobre o consumo do próprio modelo de linguagem.

## What Changes

- Capturar os tokens (`prompt_tokens`, `completion_tokens`, `total_tokens`) de cada chamada ao
  Azure OpenAI: a chamada de chat (pode ocorrer mais de uma vez por requisição, uma por iteração
  do loop ReAct) e a chamada de embeddings da busca vetorial.
- Gerar um identificador de atendimento (`id_atendimento`) por requisição de `/chat`, propagado a
  todas as chamadas de LLM que ela dispara, permitindo agrupar o custo total de uma pergunta do
  usuário mesmo quando ela envolve múltiplas chamadas ao modelo.
- Persistir cada chamada capturada em uma tabela nova, `EventosConsumoLLM`, com o custo estimado
  já calculado a partir de preços por 1.000 tokens configuráveis.
- Adicionar as configurações de preço (entrada de chat, saída de chat, embeddings) como novos
  campos de `Settings`, com valores default calibrados para o modelo em produção (GPT-4o-mini).
- Garantir que uma falha ao registrar o evento de consumo nunca derrube a resposta ao usuário
  (mesmo padrão de tolerância a falha já usado na auditoria de tool calls).

## Capabilities

### New Capabilities
- `consumo-llm`: captura, cálculo de custo estimado e persistência do consumo de tokens de cada
  chamada ao Azure OpenAI (chat e embeddings) feita pela API.

### Modified Capabilities
(nenhuma — a tabela `EventosAuditoria` de auditoria de tool calls já existe e não é alterada por
este change; este change também não estende `apm-telemetry`, que cobre telemetria técnica via
Application Insights e explicitamente não cobre métricas de negócio/custo)

## Impact

- `src/api/RAG.Api/services/rag_service.py` — leitura do `.usage` nas duas chamadas ao Azure
  OpenAI e geração/propagação do `id_atendimento`.
- `src/api/RAG.Api/services/database.py` — nova função `criar_tabela_consumo_llm_se_nao_existir()`
  e nova função `registrar_evento_consumo_llm(...)`.
- `src/api/RAG.Api/main.py` — chamada da nova função de criação de tabela no `lifespan`, junto da
  já existente `criar_tabela_auditoria_se_nao_existir()`.
- `src/api/RAG.Api/config.py` — três novos campos de preço em `Settings` (entrada de chat, saída
  de chat, embeddings), sobrescrevíveis via `.env`.
- Nenhuma nova dependência de projeto (usa apenas o SDK do `openai` já instalado).
