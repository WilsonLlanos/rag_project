# consumo-llm Specification

## Purpose

Captura o consumo de tokens e o custo estimado de cada chamada ao Azure OpenAI feita pela API,
persistindo os dados para permitir análise de custo real da solução (base para a Análise de
Viabilidade Econômica do TCC associado a este projeto).

## Requirements

### Requirement: Captura de tokens em chamadas de chat
O sistema SHALL registrar, para cada chamada de chat ao Azure OpenAI feita dentro do
processamento de uma pergunta do usuário, os tokens de entrada (`prompt_tokens`), de saída
(`completion_tokens`) e o total (`total_tokens`) retornados pela API.

#### Scenario: Uma única chamada de chat resolve a pergunta
- **WHEN** o modelo responde a uma pergunta do usuário sem precisar de nenhuma chamada de
  ferramenta (Tool Calling)
- **THEN** o sistema registra um evento de consumo com os tokens de entrada, saída e total dessa
  chamada

#### Scenario: Múltiplas chamadas de chat na mesma pergunta
- **WHEN** o modelo precisa de mais de uma rodada de raciocínio (ReAct) — por exemplo, uma
  chamada que decide invocar uma ferramenta e outra que compõe a resposta final — para responder
  a uma única pergunta do usuário
- **THEN** o sistema registra um evento de consumo separado para cada chamada de chat realizada,
  identificando a qual pergunta do usuário cada uma pertence

### Requirement: Captura de tokens em chamadas de embeddings
O sistema SHALL registrar, para cada chamada de geração de embeddings usada na busca vetorial,
os tokens consumidos retornados pela API.

#### Scenario: Busca vetorial de uma pergunta
- **WHEN** o sistema gera o vetor de uma pergunta do usuário para buscar os manuais relevantes
- **THEN** o sistema registra um evento de consumo com os tokens consumidos por essa chamada de
  embeddings

### Requirement: Correlação entre chamadas de uma mesma pergunta
O sistema SHALL associar todos os eventos de consumo (chat e embeddings) originados do
processamento de uma mesma pergunta do usuário a um identificador de atendimento comum, permitindo
somar o custo total de uma pergunta mesmo quando ela dispara múltiplas chamadas ao modelo.

#### Scenario: Agrupar o custo de uma pergunta
- **WHEN** uma pergunta do usuário dispara uma chamada de embeddings e duas chamadas de chat
- **THEN** os três eventos de consumo registrados compartilham o mesmo identificador de
  atendimento, permitindo somar seus custos como o custo total daquela pergunta

### Requirement: Cálculo de custo estimado
O sistema SHALL calcular e persistir, junto de cada evento de consumo, um custo estimado em
dólares americanos, calculado a partir dos tokens consumidos e de preços por 1.000 tokens
configuráveis.

#### Scenario: Evento de consumo de chat
- **WHEN** um evento de consumo de uma chamada de chat é registrado
- **THEN** o custo estimado é calculado a partir dos tokens de entrada e de saída dessa chamada,
  usando os preços configurados para chamadas de chat

#### Scenario: Evento de consumo de embeddings
- **WHEN** um evento de consumo de uma chamada de embeddings é registrado
- **THEN** o custo estimado é calculado a partir dos tokens consumidos dessa chamada, usando o
  preço configurado para embeddings

### Requirement: Registro não bloqueante
O sistema SHALL responder normalmente ao usuário mesmo quando o registro de um evento de consumo
falhar (ex.: banco de dados indisponível) — a falha de registro SHALL NOT impedir ou atrasar
perceptivelmente a resposta da pergunta do usuário.

#### Scenario: Banco de dados indisponível no momento do registro
- **WHEN** o sistema tenta registrar um evento de consumo e a conexão com o banco de dados falha
- **THEN** a resposta à pergunta do usuário é entregue normalmente, e a falha de registro é
  apenas registrada em log
