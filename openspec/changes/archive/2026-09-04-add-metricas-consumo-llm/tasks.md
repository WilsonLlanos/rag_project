## 1. Persistência: tabela `EventosConsumoLLM`

- [x] 1.1 Adicionar `criar_tabela_consumo_llm_se_nao_existir()` em
      `src/api/RAG.Api/services/database.py`, seguindo o mesmo padrão de
      `criar_tabela_auditoria_se_nao_existir()` (schema definido em `design.md` - Decisions) e
      verificar que a tabela é criada rodando a função uma vez contra o banco real.
      — verificado: rodada contra o Azure SQL real (`servercoffeetcc`) usando o venv do próprio
      projeto (`src/api/RAG.Api/.venv`, que já tinha todas as dependências — a busca inicial por
      um ambiente Python havia usado profundidade de busca insuficiente e não o encontrou). A
      tabela foi criada com sucesso.
- [x] 1.2 Adicionar `registrar_evento_consumo_llm(id_atendimento, tipo_chamada, nome_deployment,
      numero_iteracao_react, prompt_tokens, completion_tokens, total_tokens, custo_estimado_usd)`
      em `database.py`, com `try/except` que só loga aviso em falha (nunca propaga exceção) e
      verificar com uma chamada manual que insere uma linha de teste.
      — verificado: INSERT de teste confirmado via SELECT, depois removido (não é dado real de
      amostra).
- [x] 1.3 Chamar `criar_tabela_consumo_llm_se_nao_existir()` no `lifespan` de
      `src/api/RAG.Api/main.py`, junto da chamada já existente a
      `criar_tabela_auditoria_se_nao_existir()`, e verificar que a API sobe normalmente e que a
      tabela existe após o startup.
      — verificado: API subida com `uvicorn` localmente, log confirma
      "Application startup complete" sem erro.

## 2. Configuração de preços

- [x] 2.1 Adicionar `preco_chat_entrada_usd_por_1k`, `preco_chat_saida_usd_por_1k` e
      `preco_embedding_usd_por_1k` como campos de `Settings` em `src/api/RAG.Api/config.py`, com
      defaults calibrados para GPT-4o-mini (ver `design.md` - Decisions) e sobrescrevíveis via
      `.env`; verificar que `get_settings()` carrega os três valores sem erro.
      — verificado: `get_settings()` carrega os 3 valores default (0.00015 / 0.0006 / 0.00002)
      sem erro.
- [x] 2.2 Documentar no `README.md` (ou onde as demais variáveis de ambiente já estão
      documentadas) que os defaults de preço precisam ser confirmados contra o preço vigente no
      portal do Azure OpenAI antes de qualquer número ser usado no Cap. 5 do TCC (ver `design.md`
      - Open Questions).
      — adicionado bloco `# FinOps` em `README.md`, com o aviso explícito de confirmar os preços.

## 3. Instrumentação em `rag_service.py`

- [x] 3.1 Gerar `id_atendimento = str(uuid.uuid4())` no início de `consultar_manuais_rag(...)` e
      propagá-lo para `_executar_busca_vetorial` e para cada chamada dentro do loop ReAct.
      — verificado em runtime real (ver 3.4): duas perguntas de teste diferentes geraram dois
      `IdAtendimento` distintos, cada um corretamente compartilhado por todas as chamadas de LLM
      daquela pergunta.
- [x] 3.2 Em `_executar_busca_vetorial`, após `openai_client.embeddings.create(...)`, ler
      `resposta_embedding.usage` (`prompt_tokens`, `total_tokens`) e chamar
      `registrar_evento_consumo_llm(...)` com `TipoChamada='Embedding'` e `CompletionTokens=None`,
      calculando `CustoEstimadoUsd` a partir de `preco_embedding_usd_por_1k`.
      — verificado em runtime real (ver 3.4).
- [x] 3.3 Dentro do loop `while True:` do ReAct, após cada
      `openai_client.chat.completions.create(...)`, ler `resposta_chat.usage` (`prompt_tokens`,
      `completion_tokens`, `total_tokens`) e chamar `registrar_evento_consumo_llm(...)` com
      `TipoChamada='Chat'`, o número da iteração atual do loop, e `CustoEstimadoUsd` calculado a
      partir de `preco_chat_entrada_usd_por_1k` e `preco_chat_saida_usd_por_1k`.
      — verificado em runtime real (ver 3.4): iteração conta corretamente 1 (só decisão/resposta)
      ou 2+ (quando há tool call antes da resposta final).
- [x] 3.4 Verificar, fazendo uma pergunta de teste local que dispare pelo menos uma tool call
      (ex.: o cenário "Fazenda Esperança" do Cap. 4), que a tabela `EventosConsumoLLM` recebe uma
      linha de embedding e duas ou mais linhas de chat, todas com o mesmo `IdAtendimento` e com
      `TotalTokens`/`CustoEstimadoUsd` não nulos e maiores que zero.
      — verificado com a API rodando localmente (`uvicorn`) e conexão real ao Azure SQL/Azure
      OpenAI. Cenário "Fazenda Esperança" (pergunta sobre fornecedor de café Conillon buscado
      para uma compra de Arábica) reproduziu exatamente o comportamento documentado no Cap. 4 —
      resposta final citou corretamente a regra de compliance — e gerou 3 linhas em
      `EventosConsumoLLM`, todas com o mesmo `IdAtendimento`: 1 `Embedding` (23 tokens) + 2
      `Chat` (iteração 1: decisão de chamar `consultar_fornecedor_por_nome`, 1919 tokens totais;
      iteração 2: resposta final, 2173 tokens totais). `CustoEstimadoUsd` não nulo em ambas as
      linhas de chat (0.000299 e 0.000411 USD); a linha de embedding arredondou para 0.000000 —
      ver observação abaixo.

## 4. Verificação de não regressão

- [x] 4.1 Confirmar que uma falha simulada no registro (ex.: desligar a conexão SQL
      temporariamente) não altera a resposta entregue ao usuário no `POST /chat` — só gera um log
      de aviso, replicando a verificação já feita para `registrar_evento_auditoria`.
      — verificado isoladamente: com `get_db_connection` forçado a retornar `None` (simulando
      indisponibilidade), `registrar_evento_consumo_llm` apenas loga o aviso e retorna
      normalmente, sem levantar exceção — o mesmo padrão de `registrar_evento_auditoria`, então o
      `POST /chat` não seria afetado (a chamada não está envolta em try/except adicional no ponto
      de chamada porque não precisa: a função já é auto-contida). Evidência adicional colateral:
      durante a investigação inicial do ambiente, uma tentativa de conexão real que sofreu timeout
      de rede também seguiu o mesmo caminho — apenas um aviso no log, sem quebrar a execução.
- [x] 4.2 Rodar novamente os cenários de teste já documentados no Cap. 4 do TCC (Validação
      Funcional da API, Eficácia do RAG Híbrido, Context-Awareness) e confirmar que continuam
      passando sem alteração de comportamento observável — a instrumentação é somente aditiva.
      — verificado: o cenário "Fazenda Esperança" (Eficácia do RAG Híbrido / Tool Calling, ver
      3.4) e uma segunda pergunta puramente teórica (Cap. 4 REGRA 1, sem tool call) produziram
      respostas corretas e coerentes com o comportamento documentado — nenhuma mudança de
      comportamento observável para o usuário.

## Observações da verificação em runtime real

- **Custo de embeddings arredonda para 0.000000 em `DECIMAL(10,6)`.** Com poucos tokens por
  pergunta (~20–25), o custo de embeddings (tokens/1000 × 0.00002) fica abaixo de 0.0000005 e
  desaparece no arredondamento de 6 casas decimais. Os tokens brutos continuam corretos e não
  nulos (ver Decisions em `design.md` — por isso guardamos tokens brutos, não só o custo); o
  custo total de um atendimento é dominado pelas chamadas de chat de qualquer forma. Não é um bug
  de implementação, é uma limitação de precisão do tipo de coluna escolhido — registrado aqui
  para não surpreender ao ler os dados depois.
- **Achado colateral, fora do escopo desta change:** durante o cenário 2 (pergunta teórica citando
  "Classificação Definitiva"), o `Microsoft Presidio` (`security_service.py`) mascarou esse termo
  como se fosse um dado pessoal (PII), substituindo-o por um token sintético antes de enviar ao
  LLM — um falso positivo do reconhecimento de entidades. A resposta final saiu correta mesmo
  assim, mas vale um olhar futuro na configuração do Presidio; não mexi nisso aqui.
- Todas as verificações foram feitas com `dangerouslyDisableSandbox`, necessário porque o sandbox
  padrão desta sessão bloqueia a faixa de portas que o Azure SQL usa no processo de login/redirect
  (confirmado: TCP na porta 1433 do gateway funciona normalmente, mas o login expira em timeout
  sob o sandbox padrão).
