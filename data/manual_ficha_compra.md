# Manual de Operação - Sistema Café-Trade (Módulo de Compras)

## Tela: Ficha de Compra
**Objetivo:** Registrar a aquisição de lotes de café diretamente com produtores e fazendas para o estoque da empresa.

---

### 1. Descrição dos Campos Técnicos
Abaixo estão as orientações para o preenchimento obrigatório de cada campo:

| Campo | Descrição | Regras de Negócio |
| :--- | :--- | :--- |
| **Preço do Contrato** | Valor acordado por saca. | Deve ser inserido em formato numérico (ex: 1200,50). |
| **Tipo de Café** | Estado do produto. | Opções válidas: **Em Grão** ou **Cereja**. |
| **Qualidade** | Classificação botânica. | Opções válidas: **Arábica** ou **Conillon**. |
| **Quantidade (Sacas)** | Volume do lote. | A unidade de medida padrão é a **Saca de 60kg**. |
| **Cidade de Origem** | Local de produção. | Essencial para rastreabilidade e logística. |
| **Fornecedor** | Nome da Fazenda/Produtor. | Deve estar previamente cadastrado no sistema. |
| **Modalidade de Frete** | Tipo de transporte. | Definir se a responsabilidade é do vendedor ou comprador. |
| **Funcionário Comprador** | Responsável técnico. | Nome do colaborador que fechou a negociação. |

---

### 2. Fluxo de Operação (Passo a Passo)
1. No menu principal, navegue até **Compras > Ficha de Compra**.
2. Clique no botão **"Nova Ficha"**.
3. Selecione o **Fornecedor** e informe a **Cidade de Origem**.
4. Defina se o café é **Arábica** ou **Conillon** e se o estado é **Grão** ou **Cereja**.
5. Insira a quantidade exata em **Sacas de 60kg**.
6. Informe o **Preço do Contrato** e a **Modalidade de Frete**.
7. O campo **Funcionário Comprador** será preenchido automaticamente com seu login, mas pode ser alterado se necessário.
8. Clique em **Salvar** para gerar o número do contrato.

---

### 3. Perguntas Frequentes (FAQ)
> **Pergunta:** O que fazer se a saca não for de 60kg?
> **Resposta:** O sistema Café-Trade é padronizado. Você deve realizar a conversão matemática para o equivalente a 60kg antes de inserir a quantidade no sistema.
>
> **Pergunta:** Posso cadastrar uma compra sem o nome do fornecedor?
> **Resposta:** Não. O campo fornecedor é uma chave primária para o módulo financeiro e de rastreabilidade.