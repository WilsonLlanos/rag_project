# Manual: Tela de Consulta de Lotes

## Visão Geral
Esta tela destina-se à consulta centralizada de lotes de estoque. O principal objetivo é permitir que os usuários verifiquem quais lotes ainda possuem saldo disponível.

## Regras de Negócio e Operação
1. **Consulta de Saldo:** A função primordial desta tela é exibir os lotes ativos e seus respectivos saldos atuais.
2. **Identificação de Erros (Saldo Quebrado):** - O sistema deve monitorar o saldo dos lotes.
   - Caso seja identificado um "saldo quebrado" (valores decimais inconsistentes ou divergentes da unidade de medida esperada), isso é um indicativo de erro sistêmico ou de lançamento que deve ser investigado.

## Integração com Inteligência Artificial (LLM)
Para garantir respostas precisas e consistentes sobre o estado dos lotes, o sistema de IA deve seguir as seguintes diretrizes:

* **Requisição de Informações:** Sempre que um usuário realizar uma pergunta sobre informações específicas de qualquer lote (status, quantidade, data de validade, etc.), o sistema **deve obrigatoriamente** acionar a função `filtrar_lotes`.

### Exemplo de Fluxo de Chamada da Função:
Se o usuário perguntar: "Qual é o saldo do lote X?"
- **Ação:** O LLM deve executar `filtrar_lotes(identificador_lote='X')`.
- **Análise:** Verificar se o retorno indica saldo normal ou se o saldo apresenta inconsistências ("quebrado").
