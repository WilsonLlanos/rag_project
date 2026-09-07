---
name: revisar-tcc
description: >
  Escreve, adiciona ou revisa seções e capítulos do TCC (tese em LaTeX, template
  USPSC/abnTeX2, em docs/) do projeto rag_project — uma Prova de Conceito de RAG
  híbrido (Azure AI Search vetorial + Azure SQL via Tool Calling) para suporte N1
  numa trading de commodities de café. Use esta skill sempre que o usuário pedir
  para escrever uma seção sobre algo no TCC, revisar ou enriquecer um capítulo,
  adicionar ou ajustar uma referência bibliográfica do TCC, melhorar um parágrafo
  da fundamentação teórica/metodologia/avaliação/conclusão, ou avaliar se algo
  "entraria bem" ou "enriqueceria" a tese — mesmo sem a palavra "TCC" explícita,
  por exemplo "isso merece uma nota no capítulo de metodologia" ou "vamos
  documentar essa decisão na fundamentação teórica". NÃO use para tarefas de
  código do rag_project em si (ver a skill adicionar-sql-tool-rag) nem para
  discussões que não vão virar texto na tese.
---

# Revisar/escrever o TCC (rag_project)

Esta skill escreve para um documento acadêmico avaliado por banca. O risco central
não é gramática — é afirmar algo que a implementação real não sustenta. Trate cada
edição como uma citação: se não dá para apontar de onde veio, não entra como fato.

## Mapa do documento

Tudo fica em `docs/` (relativo à raiz do `rag_project`):

| Arquivo | Conteúdo |
|---|---|
| `docs/USPSC-modelo-ICMC-PORTUGUÊS.tex` | Arquivo principal (compilar este) |
| `docs/USPSC-TA-Textual/USPSC-Cap1-Introducao.tex` | Introdução |
| `docs/USPSC-TA-Textual/USPSC-Cap2-Fundamentacao_Teorica.tex` | `\label{Cap:Fund_Teo}` |
| `docs/USPSC-TA-Textual/USPSC-Cap3-Metodologia.tex` | `\label{Cap:Metodologia}` |
| `docs/USPSC-TA-Textual/USPSC-Cap4-Avaliacao_Experimental.tex` | `\label{Cap:Ava_Exp}` |
| `docs/USPSC-TA-Textual/USPSC-Cap5-Viabilidade.tex` | `\label{Cap:Viabilidade}` |
| `docs/USPSC-TA-Textual/USPSC-Cap6-Conclusao.tex` | `\label{Cap:Conclusoes}` |
| `docs/USPSC-bib/USPSC-modelo-references.bib` | Bibliografia |

**Onde cada tipo de conteúdo entra** — antes de escrever, decida o capítulo certo:

- **Cap. 2 (Fund. Teórica)**: conceitos e teoria que sustentam uma escolha de
  arquitetura (ex.: por que RAG, por que HNSW, o que é *Tool Calling*). Conecta
  literatura a uma decisão do projeto, mas não descreve a implementação em si.
- **Cap. 3 (Metodologia)**: a stack, a arquitetura efetivamente construída, decisões
  de implementação e suas justificativas técnicas.
- **Cap. 4 (Avaliação Experimental)**: evidências de testes/validações **já
  realizados**, com print, log ou resultado real. Nunca um resultado hipotético.
- **Cap. 5 (Viabilidade)**: ROI, custo, impacto operacional.
- **Cap. 6 (Conclusão)**: síntese final e a seção "Trabalhos Futuros" — é para lá
  que vai qualquer limitação ou ideia de estudo que você identificar no processo de
  escrever (ex.: "isso mereceria um teste de carga, mas não foi feito ainda").

Se o pedido do usuário não deixar claro o capítulo, pergunte ou proponha o mais
provável e diga por quê — errar o capítulo é mais caro de corrigir depois do que
uma pergunta agora.

## A regra de ouro: ancorar no artefato real

Nunca escreva um número (latência, recall, custo, contagem de documentos, taxa de
sucesso) ou uma afirmação de comportamento ("o sistema faz X") sem uma fonte
verificável. As fontes válidas, em ordem de preferência:

1. **O código do projeto** — sobretudo `src/api/RAG.Api/services/rag_service.py`
   (orquestração, prompts, tools), `src/api/RAG.Api/indexer.py` (ingestão/chunking),
   `src/api/RAG.Api/services/database.py` (consultas SQL reais) e
   `src/api/RAG.Api/config.py` (o que é configurável). Leia o trecho relevante antes
   de descrevê-lo — não escreva de memória de uma conversa anterior.
2. **Dados reais que o usuário cola na conversa** (ex.: JSON de config do Azure AI
   Search, print de log, resultado de teste).
3. **Documentação oficial** (Microsoft Learn, papers) — só para afirmações
   conceituais/genéricas sobre a tecnologia, não sobre o comportamento *deste*
   projeto.

Quando o dado não existe em nenhum desses lugares: **pergunte ao usuário**, ou
escreva a frase como limitação/estimativa/trabalho futuro em vez de fato — nunca
complete a lacuna com um número plausível. Uma seção mais curta e honesta vale mais
para a banca do que uma seção completa com um dado inventado.

## Convenções do template (USPSC/abnTeX2)

Siga o que já está em uso nos capítulos existentes — não introduza um estilo novo:

- `\textit{...}` para estrangeirismos (*RAG*, *embeddings*, *chunk*, nomes de
  produtos como *Azure AI Search*), não `\textbf` nem aspas.
- `---` (três hífens) para travessão, não `--` nem `-`.
- Figuras: `\begin{figure}[H] ... \label{fig:algo} ... \end{figure}`, sempre com
  `\caption` descritivo e `\label` referenciado no texto por `\ref`.
- Subseções que vão ser referenciadas de outro capítulo levam
  `\label{subsec:algo}`.
- `\cite{chave}` para toda afirmação apoiada em literatura ou documentação externa.

### Bibliografia

Antes de adicionar uma referência, **cheque se ela já existe** no `.bib` — chaves já
cadastradas: `vaswani2017attention`, `lewis2020retrieval`, `davenport1998working`,
`kleppmann2017designing`, `nonaka1995knowledge`, `saltzer1975protection`,
`jurafsky2023speech`, `baeza2011modern`, `yao2022react`, `owasp2023llm`,
`microsoft_presidio`, `azure_openai`, `brasil2018lgpd`, `malkov2018efficient`,
`malkov2014approximate`, `aumuller2020ann`, `microsoft_aisearch_vectors`, `nbr6028`.

Se precisar de uma nova, siga o formato minimalista já usado (veja o `.bib`):
`@article`/`@book` com `title`, `author`, `year` e os campos mínimos da fonte;
`@misc` para documentação/site, sempre com `url` e `note={Acesso em: <data de
hoje>}`. Não adicione campos que as entradas existentes não usam.

## Depois de editar: sempre verificar a compilação

Uma edição em `.tex`/`.bib` só está pronta depois de compilar e checar o resultado
— citação quebrada ou figura estourando a página só aparece assim. Rode:

```bash
bash .claude/skills/revisar-tcc/scripts/verificar_build.sh docs
```

Isso compila com `latexmk` e já filtra o log por citação/referência indefinida. Se
o script reportar erro de compilação, leia o `build.log` que ele gera em `docs/` e
corrija antes de considerar a edição concluída.

Se a edição **adicionou ou alterou uma figura**, confira visualmente — LaTeX não
avisa sobre uma figura cortada ou um diagrama ilegível:

```bash
bash .claude/skills/revisar-tcc/scripts/ver_pagina.sh "<termo que só aparece nessa figura/página>" "$SCRATCHPAD_DIR" docs
```

Use um termo do `\caption` ou do texto ao redor da figura. O script salva os PNGs
das páginas encontradas no diretório indicado (use o scratchpad da sessão) — em
seguida, leia a imagem com a ferramenta Read para inspecionar o layout.

## Nunca commitar sozinho

Edite os arquivos e pare aí. `docs/` (o TCC) foi propositalmente removido do
rastreamento remoto do repositório — o usuário decide se e quando versionar essas
mudanças. Não rode `git add`/`git commit`/`git push` sobre `docs/` a menos que seja
pedido explicitamente.
