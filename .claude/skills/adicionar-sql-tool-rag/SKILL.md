---
name: adicionar-sql-tool-rag
description: Adiciona uma nova ferramenta (tool) de acesso a SQL para o GPT-4o usar via tool calling neste projeto RAG. Use sempre que o usuário pedir para "criar uma tool", "adicionar uma function", "expor uma consulta SQL para a IA", "deixar a IA consultar/atualizar tal tabela", ou descrever uma nova pergunta/ação que a IA do chat deveria conseguir responder consultando o banco (Azure SQL) — mesmo que o usuário não use a palavra "tool" explicitamente, por exemplo "quero que a IA consiga dizer quantos lotes tal fornecedor já entregou" ou "a IA precisa poder cancelar um lote". Cobre as três edições coordenadas em database.py e rag_service.py, mais o reforço opcional via manual .md indexado no Azure AI Search — não use para endpoints REST simples do Streamlit que não passam pelo GPT-4o (esses são só uma função em database.py + uma rota em main.py, sem tool calling).
---

# Adicionar uma SQL tool ao RAG híbrido

## O que é este sistema

O backend (`src/api/RAG.Api/`) é um RAG híbrido: Azure AI Search (manuais em Markdown,
busca vetorial) + Azure SQL exposto ao GPT-4o como *tools* no formato OpenAI function-calling.
Não existe framework de agentes nem registro por decorator — tudo é fiado à mão em dois
arquivos, com um terceiro cuidando de PII automaticamente:

- **`services/database.py`** — o corpo de cada tool: função Python que abre conexão, roda
  SQL parametrizado, devolve um `dict`.
- **`services/rag_service.py`** — três coisas: a lista `ferramentas_disponiveis` (schema
  JSON que ensina ao modelo quais tools existem e como chamá-las), as regras `REGRA N` no
  `prompt_sistema` (que ensinam *quando* chamar cada uma), e o laço dispatcher que de fato
  executa a função Python quando o modelo pede.
- **`services/security_service.py`** — anonimização/tokenização de PII (Presidio). É
  genérico: intercepta os argumentos de qualquer tool automaticamente antes da execução.
  Você só mexe aqui se a nova tool precisar de uma regra de rehidratação diferente do padrão.

Uma tool nova é **sempre um conjunto de edições nesses arquivos existentes**, nunca um
arquivo novo — não há convenção de "uma tool por arquivo" neste projeto.

Antes de editar, releia `services/database.py` (função `filtrar_lotes`, é o template mais
limpo) e `services/rag_service.py` inteiro para pegar o estilo exato: nomes em português,
snake_case, comentários explicando a regra de negócio embutida na query.

## Passo 0 — Confirme que é mesmo uma tool de IA

Duas categorias diferentes usam `database.py`, e só uma precisa de todo este fluxo:

- **Tool do GPT-4o**: a IA decide sozinha quando chamar, via tool calling no `/chat`.
  Precisa dos passos 1–4 abaixo.
- **Endpoint REST direto**: código do Streamlit chama a rota do FastAPI diretamente
  (ex.: `GET /fornecedores` → `listar_fornecedores_filtrados`). É só uma função em
  `database.py` + uma rota em `main.py`. Não mexe em `rag_service.py`.

Se o pedido do usuário é "a IA deveria conseguir responder/fazer X", é a primeira categoria.
Se é "a tela precisa mostrar/filtrar X", é a segunda — pare aqui e trate como uma rota comum.

## Passo 1 — Função SQL em `database.py`

Adicione a função na seção `# --- FERRAMENTAS DO RAG HÍBRIDO (TOOL CALLING) ---`. Siga
exatamente o padrão observado em toda função existente ali (`filtrar_lotes`,
`consultar_fornecedor_por_nome`, `ajustar_residuo_lote_por_codigo_lote`):

```python
def nome_da_tool(parametro_obrigatorio: str, parametro_opcional: str = None):
    """
    Descrição curta do que a função faz e por que a IA a usaria.
    """
    conn = get_db_connection()
    if not conn:
        return {"erro": "Falha na conexão com o banco de dados."}

    try:
        cursor = conn.cursor()
        query = "SELECT ... FROM ... WHERE ..."
        cursor.execute(query, (parametro_obrigatorio,))
        # ... monta o resultado
        return {"chave_dos_dados": resultado}
    except Exception as e:
        return {"erro": f"Erro na consulta SQL: {str(e)}"}
    finally:
        if conn:
            conn.close()
```

Por que este formato exatamente, e não outro que também "funcionaria":

- **Query sempre parametrizada (`?` + tupla/lista)** — é a única defesa contra SQL
  injection neste projeto; não existe camada de validação separada. Nunca monte a query
  com f-string usando valor do usuário.
- **Retorno é sempre um `dict` simples**, nunca uma exceção que escapa da função. O
  dispatcher em `rag_service.py` espera `resultado_db["erro"]` para decidir o status de
  auditoria — uma função que lança exceção sem capturar quebra esse contrato.
- **`try/except/finally` com `conn.close()` no finally** — evita conexão pendurada mesmo em
  erro.
- Se a tool **escreve** no banco (UPDATE/INSERT/DELETE), adicione `conn.rollback()` no
  `except` e `conn.commit()` só depois do sucesso, e embuta a regra de negócio que autoriza
  a escrita diretamente na cláusula `WHERE` (veja `ajustar_residuo_lote_por_codigo_lote`,
  que só encerra um lote se `QuantidadeSacas <= 0.01`) — é assim que este projeto impede a
  IA de fazer updates fora do que é permitido, já que não existe serviço de permissão à
  parte.

**Cuidado com nome duplicado**: `database.py` já tem uma função definida duas vezes por
acidente (`ajustar_residuo_lote_por_codigo_lote`, linhas ~260 e ~397 — Python fica só com a
segunda, silenciosamente). Confira com Grep que o nome escolhido não colide com nada
existente antes de adicionar.

## Passo 2 — Schema da tool em `rag_service.py`

Adicione um item à lista `ferramentas_disponiveis` (topo do arquivo), no formato OpenAI
function-calling:

```python
{
    "type": "function",
    "function": {
        "name": "nome_da_tool",
        "description": "Frase objetiva dizendo quando usar, com exemplos concretos entre aspas (ex: 'CTR-2026-A101').",
        "parameters": {
            "type": "object",
            "properties": {
                "parametro_obrigatorio": {
                    "type": "string",
                    "description": "O que é, com um exemplo real."
                }
            },
            "required": ["parametro_obrigatorio"]
            # Omita "required" se todos os parâmetros forem opcionais.
        }
    }
}
```

O campo `description` não é documentação decorativa — é o que o GPT-4o lê para decidir
*se* e *como* chamar a tool (`tool_choice="auto"` dá autonomia total ao modelo). Escreva-o
com o mesmo cuidado que as descrições existentes: frase direta, em português, com exemplo
de valor real entre aspas para cada parâmetro.

**O `"name"` aqui precisa ser idêntico, caractere por caractere**, ao nome da função em
`database.py` e à string comparada no dispatcher (passo 4). É a única coisa que amarra os
três lugares — não há import type-checked nem enum validando isso.

## Passo 3 — Ensinar quando usar, no `prompt_sistema`

Se a tool tem uma condição de uso que não é óbvia só pelo `description` do schema — por
exemplo, exige confirmação explícita do usuário antes de rodar (caso de toda tool que
escreve no banco), ou só deve ser chamada depois de outra tool, ou compete com outra tool
parecida — adicione uma nova `REGRA N:` ao `prompt_sistema` em `consultar_manuais_rag`,
seguindo o estilo das REGRA 1–5 existentes (frase imperativa, cita o nome da tool entre
aspas simples). Veja a REGRA 3 como modelo de tool que exige confirmação, e a REGRA 4/5
como modelo de tool que deve ser chamada obrigatoriamente sob certa condição.

Se a `description` do passo 2 já deixa claro o suficiente (tool de leitura simples, sem
ambiguidade de quando usar), pode pular este passo — nem toda tool precisa de uma REGRA
dedicada.

## Passo 4 — Import + dispatcher em `rag_service.py`

1. Adicione a função ao bloco de import no topo:
   ```python
   from services.database import (
       filtrar_lotes,
       ajustar_residuo_lote_por_codigo_lote,
       consultar_fornecedor_por_nome,
       nome_da_tool,
       registrar_evento_auditoria
   )
   ```
2. Adicione um `elif` no laço de execução (dentro do `for tool_call in mensagem_assistente.tool_calls:`, junto aos existentes):
   ```python
   elif nome_funcao == "nome_da_tool":
       resultado_db = nome_da_tool(argumentos["parametro_obrigatorio"])
   ```
   Use `argumentos["x"]` para parâmetros obrigatórios (um `KeyError` aqui é capturado pelo
   `try/except` que envolve todo o bloco e vira um evento de auditoria com status "Erro" —
   não precisa de tratamento extra) e `argumentos.get("x")` com default para parâmetros
   opcionais, igual ao `filtrar_lotes` já faz.

**Não precisa mexer em mais nada para PII ou auditoria** — o interceptor de rehidratação
(logo antes do `print(f"DEBUG: ...")`) e o `registrar_evento_auditoria` já envolvem
genericamente qualquer tool que passe por este laço. A única regra a respeitar: nunca deixe
`argumentos` (já rehidratado com dados reais) ir para o log de auditoria — sempre a cópia
`argumentos_seguro_para_log` feita antes da rehidratação. Se a nova tool não mexe com esse
fluxo, não há nada a fazer aqui.

## Passo 5 — Reforço via manual .md (opcional, mas recomendado se a tool tem gatilho ambíguo)

Este projeto também ensina o modelo por meio dos manuais indexados no Azure AI Search — veja
`data/manual_consulta_lote.md`, que instrui explicitamente "sempre que o usuário perguntar
X, acione a função `filtrar_lotes`". Isso reforça a REGRA do prompt via busca vetorial,
útil quando o gatilho da tool é uma pergunta de usuário mais variada do que o
`description` consegue cobrir sozinho.

Se a nova tool se beneficia disso, crie/atualize um `data/manual_<algo>.md` curto seguindo
esse mesmo formato (visão geral → regra de negócio → exemplo de fluxo de chamada citando o
nome exato da função). Depois, para o chunk entrar de fato na busca vetorial, é preciso
rodar o indexer manualmente:

```
cd src/api/RAG.Api
python indexer.py
```

Isso sobe os `.md` de `data/` para o índice do Azure AI Search (não roda sozinho, não faz
parte do deploy). Avise o usuário que este passo requer as credenciais do Azure configuradas
(`config.py`/`.env`) e que ele pode preferir rodar isso manualmente em vez de você rodar por
ele, já que grava dados num serviço Azure real.

## Testando

Não há suíte de testes automatizada neste projeto (nenhum `pytest`, nada em `tests/`). O
jeito real de verificar:

1. `cd src/api/RAG.Api && uvicorn main:app --reload`
2. Abra `http://localhost:8000/docs` (Swagger) e chame `POST /chat` com uma pergunta que
   deveria disparar a nova tool.
3. Acompanhe o terminal: a linha `DEBUG: A IA decidiu chamar a função '...'` confirma que o
   modelo escolheu a tool certa com os argumentos certos.
4. Se quiser confirmar a auditoria, consulte a tabela `EventosAuditoria` no Azure SQL — todo
   evento de chamada de tool (sucesso ou erro) é gravado lá automaticamente.

Isso exige credenciais reais de Azure SQL/OpenAI/AI Search configuradas — se não estiverem
disponíveis no ambiente atual, diga isso explicitamente ao usuário em vez de alegar que
testou.
