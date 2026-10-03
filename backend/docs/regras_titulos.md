# Regras de títulos a pagar

## O que é um título a pagar

Um título a pagar representa uma obrigação da empresa com um fornecedor. Ele tem número, fornecedor, descrição, data de emissão, data de vencimento e valor total.

- O número do título é único por fornecedor. Cadastrar o mesmo número duas vezes para o mesmo fornecedor gera o erro `TITULO_DUPLICADO`.
- O valor total deve ser maior que zero.
- A data de vencimento não pode ser anterior à data de emissão.
- Fornecedor inativo não pode receber novos títulos (erro `FORNECEDOR_INATIVO`). Títulos lançados antes da inativação continuam válidos.
- Todo título nasce com o status `PENDENTE`.

## Estados do título

O título possui cinco estados:

- `PENDENTE`: título lançado, aguardando rateio completo e aprovação.
- `APROVADO`: rateio conferido; o título está liberado para receber pagamentos.
- `PAGO`: os pagamentos confirmados somam exatamente o valor total.
- `CANCELADO`: título encerrado sem pagamento. É um estado final.
- `ERRO`: a integração com o ERP de destino rejeitou o título.

Transições permitidas:

- `PENDENTE` → `APROVADO`, `CANCELADO` ou `ERRO`
- `APROVADO` → `PAGO`, `CANCELADO` ou `ERRO`
- `ERRO` → `PENDENTE` (reprocessamento) ou `CANCELADO`
- `PAGO` → `PENDENTE`, somente por estorno de pagamento
- `CANCELADO` → nenhuma

Qualquer outra transição é recusada com o erro `TRANSICAO_STATUS_INVALIDA`. Não existe operação para devolver um título `APROVADO` diretamente para `PENDENTE`.

## Aprovação

A aprovação libera o título para pagamento.

- Só é possível aprovar um título `PENDENTE`. Um título em `ERRO` precisa ser reprocessado (voltando a `PENDENTE`) antes de ser aprovado.
- O rateio precisa cobrir exatamente 100% do valor total. Se faltar valor, a aprovação é recusada com o erro `RATEIO_INCOMPLETO`, que informa o valor total, o valor rateado e o valor faltante.
- Exemplo: um título de 10.000,00 com 6.000,00 rateados não pode ser aprovado; faltam 4.000,00.
- Depois de aprovado, o título fica congelado: dados e rateios não podem mais ser alterados.

## Cancelamento

- O cancelamento exige um motivo, registrado na trilha de auditoria.
- Pode ser feito a partir de `PENDENTE`, `APROVADO` ou `ERRO`.
- Um título com pagamentos confirmados não pode ser cancelado (erro `TITULO_COM_PAGAMENTOS`). É preciso estornar os pagamentos antes. Pagamentos já estornados não impedem o cancelamento.
- Um título `PAGO` sempre tem pagamentos confirmados, portanto não pode ser cancelado.
- `CANCELADO` é final: o título não volta a nenhum outro estado e não recebe pagamentos (erro `TITULO_CANCELADO`).

## Edição de dados

- Número, descrição, datas e valor total só podem ser alterados quando o título está `PENDENTE` ou `ERRO`. Em outros estados a alteração é recusada com o erro `TITULO_NAO_EDITAVEL`.
- O status nunca é alterado por edição; ele muda apenas pelas ações de aprovar, cancelar, reprocessar, pagar e estornar.
- O valor total não pode ficar abaixo do valor já rateado (erro `VALOR_MENOR_QUE_RATEIO`). Ajuste os rateios antes de reduzir o valor.
- O valor total não pode ficar abaixo do valor já pago (erro `VALOR_MENOR_QUE_PAGO`). Isso pode ocorrer em um título reaberto por estorno que ainda tem outros pagamentos confirmados.

## Título vencido

- Um título está vencido quando está em aberto (`PENDENTE`, `APROVADO` ou `ERRO`) e a data de vencimento é anterior à data de hoje.
- Um título que vence hoje ainda não está vencido.
- Títulos `PAGO` e `CANCELADO` nunca são considerados vencidos.
- A lista de vencidos pode ser consultada em `GET /titulos?vencidos=true`.
- O AP Copilot não calcula juros, multa nem correção monetária sobre títulos vencidos, e o vencimento não bloqueia aprovação nem pagamento.
