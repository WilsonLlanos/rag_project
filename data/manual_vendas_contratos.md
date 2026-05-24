# Manual de Operação - Sistema Café-Trade (Módulo Comercial)

## Tela: Vendas e Emissão de Contratos
**Objetivo:** Registrar a saída de lotes de café para o mercado nacional ou internacional, vinculando a qualidade do lote às exigências do cliente final.

---

### 1. Parametrização da Venda (Campos Principais)
O preenchimento correto define o fluxo fiscal e logístico do contrato:

| Campo | Descrição | Observações de Regra de Negócio |
| :--- | :--- | :--- |
| **Tipo de Operação** | Destino da mercadoria. | Opções: **Mercado Interno** ou **Exportação**. |
| **Cliente / Importador** | Entidade compradora. | Deve possuir cadastro ativo e limite de crédito aprovado. |
| **Número do Lote** | Origem física do café. | Só permite selecionar lotes com **Laudo Técnico** finalizado. |
| **Moeda** | Unidade monetária. | Interno: **BRL (Real)** | Exportação: **USD (Dólar)**. |
| **Porto de Embarque** | Local de saída (Exportação). | Ex: Porto de Santos ou Porto de Vitória. |
| **Incoterm** | Termo de venda internacional. | Ex: **FOB** (Free on Board) ou **CFR** (Cost and Freight). |
| **Preço por Saca** | Valor da negociação. | No mercado interno inclui impostos; na exportação é "Tax Free". |

---

### 2. Fluxo de Operação (Processo Comercial)
1. Acesse o menu **Vendas > Gerenciar Contratos**.
2. Clique em **"Novo Contrato de Venda"**.
3. Selecione o **Tipo de Operação**:
   - Se **Mercado Interno**: O sistema habilitará o cálculo de ICMS conforme a UF de destino.
   - Se **Exportação**: O sistema abrirá os campos de Porto, Navio e Documentação Cambial.
4. Informe o **Número do Lote**. O sistema carregará automaticamente a **Nota da Prova (SCA)** e a **Peneira** para conferência.
5. Insira a quantidade de sacas e o preço acordado.
6. Selecione a **Modalidade de Frete**.
7. Clique em **Gerar Minuta de Contrato**.

---

### 3. Guia Rápido de Suporte (FAQ)
> **Pergunta:** Por que não consigo selecionar um lote específico para a venda?
> **Resposta:** Verifique se o lote já possui um **Laudo Técnico** aprovado. Lotes "Em Trânsito" ou "Aguardando Classificação" não ficam disponíveis para venda para garantir o padrão de qualidade entregue ao cliente.
>
> **Pergunta:** Como proceder se a venda for em Dólar (USD) para o mercado interno?
> **Resposta:** O sistema Café-Trade não permite faturamento em USD para o mercado nacional. A negociação deve ser convertida para BRL utilizando a taxa PTAX do dia anterior ao faturamento.
>
> **Pergunta:** O que significa o status "Aguardando Drawback"?
> **Resposta:** Este status aparece apenas em **Vendas de Exportação** que utilizam benefícios fiscais de importação de insumos. O financeiro deve liberar a trava antes do embarque.