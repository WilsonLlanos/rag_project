## Purpose

Fornece telemetria de APM (latência de requisições, exceções e dependências externas) da API
do rag_project via Application Insights, permitindo diagnosticar problemas de performance e
falhas em produção sem depender de logs manuais.

## ADDED Requirements

### Requirement: Rastreamento de requisições HTTP
O sistema SHALL registrar no Application Insights, para cada requisição HTTP recebida pela API,
a rota, o método, o código de status e a duração.

#### Scenario: Requisição bem-sucedida
- **WHEN** um cliente faz uma requisição HTTP a qualquer endpoint da API
- **THEN** o Application Insights recebe um registro de requisição com rota, método, status
  HTTP e duração

### Requirement: Captura de exceções não tratadas
O sistema SHALL enviar ao Application Insights qualquer exceção não tratada ocorrida durante o
processamento de uma requisição, incluindo o tipo da exceção e o stack trace.

#### Scenario: Erro inesperado durante o processamento
- **WHEN** ocorre uma exceção não tratada ao processar uma requisição
- **THEN** o Application Insights recebe um registro de exceção com tipo e stack trace, e a
  resposta HTTP de erro ainda é retornada normalmente ao cliente

### Requirement: Rastreamento de dependências externas
O sistema SHALL registrar no Application Insights cada chamada a uma dependência externa (Azure
SQL, Azure AI Search, Azure OpenAI), incluindo o tipo de dependência, a duração e se houve
sucesso ou falha.

#### Scenario: Consulta ao Azure SQL
- **WHEN** o backend executa uma consulta ao Azure SQL
- **THEN** o Application Insights recebe um registro de dependência do tipo SQL com duração e
  resultado (sucesso ou falha)

### Requirement: Telemetria opcional e não bloqueante
O sistema SHALL funcionar normalmente, sem erro de inicialização, quando a variável de ambiente
da connection string do Application Insights não estiver configurada — a telemetria SHALL
apenas ficar desabilitada.

#### Scenario: Ambiente local sem connection string configurada
- **WHEN** a aplicação é iniciada sem a variável de ambiente da connection string do
  Application Insights
- **THEN** a aplicação inicializa e responde requisições normalmente, sem enviar telemetria

### Requirement: Nenhum dado sensível na telemetria
O sistema SHALL NOT enviar à telemetria de APM valores de PII real (ex.: nomes, e-mails,
documentos) capturados em argumentos de requisições ou dependências — apenas metadados técnicos
(rota, duração, status, tipo de erro).

#### Scenario: Requisição contendo dado pessoal do usuário
- **WHEN** uma requisição ao chat contém um dado pessoal do usuário no corpo
- **THEN** o registro de telemetria correspondente no Application Insights não contém esse dado
  pessoal em texto claro
