# Manual financeiro do AP Copilot

## Visão geral

O AP Copilot é um módulo simplificado de contas a pagar. Ele controla:

- fornecedores e centros de custo (cadastros);
- títulos a pagar, com o ciclo de vida de status;
- rateios do valor de cada título entre centros de custo;
- pagamentos, inclusive parciais, e estornos;
- a trilha de auditoria de todas as alterações relevantes.

## Fluxo principal

O caminho normal de um título é `PENDENTE` → `APROVADO` → `PAGO`.

```
PENDENTE ──aprovar──► APROVADO ──(pagamentos = valor total)──► PAGO
```

1. Lançar o título. Ele nasce `PENDENTE`.
2. Ratear 100% do valor total entre centros de custo ativos.
3. Aprovar o título. A aprovação exige rateio de exatamente 100%.
4. Registrar os pagamentos, em uma ou mais parcelas, sem ultrapassar o saldo pendente.
5. Quando os pagamentos confirmados somam o valor total, o título passa automaticamente para `PAGO`.

## Fluxo de cancelamento

```
PENDENTE / APROVADO / ERRO ──cancelar(motivo)──► CANCELADO
```

- O cancelamento exige motivo e só é possível sem pagamentos confirmados.
- `CANCELADO` é final: o título não volta e não recebe pagamentos.

## Fluxo de erro de integração

```
PENDENTE / APROVADO ──falha de integração──► ERRO ──reprocessar──► PENDENTE
```

- Quando o ERP de destino rejeita o título, ele vai para `ERRO` e a mensagem fica na auditoria.
- Em `ERRO`, os dados e rateios podem ser corrigidos.
- O reprocessamento devolve o título para `PENDENTE`; depois é preciso aprovar de novo.
- Um título em `ERRO` também pode ser cancelado.

## Fluxo de estorno

```
PAGO ──estorno de pagamento──► PENDENTE ──aprovar──► APROVADO
```

- Estornar um pagamento de um título `PAGO` reabre o título como `PENDENTE`.
- O título precisa ser aprovado de novo antes de receber novos pagamentos.
- Em um título `APROVADO`, o estorno apenas recalcula o saldo e o status continua `APROVADO`.

## Cadastros

- Fornecedores têm CNPJ validado pelos dígitos verificadores e único no sistema (erro `CNPJ_DUPLICADO`).
- Centros de custo têm código único (erro `CODIGO_CENTRO_CUSTO_DUPLICADO`).
- Fornecedores e centros de custo não são excluídos, apenas inativados, preservando o histórico.
- Fornecedor inativo não recebe novos títulos; centro de custo inativo não recebe novos rateios.

## Auditoria

- Toda alteração relevante gera um registro na trilha de auditoria, gravado na mesma operação: se a operação falhar, o registro também é descartado.
- Tipos de registro: `CRIACAO`, `ATUALIZACAO`, `MUDANCA_STATUS`, `RATEIO`, `PAGAMENTO`, `INTEGRACAO` e `CADASTRO`.
- Mudanças de status registram o status anterior, o novo status e o motivo.
- A trilha de um título é consultada em `GET /titulos/{id}/logs`.

## Fora do escopo do AP Copilot

O AP Copilot não possui:

- cálculo de juros, multa, desconto ou correção monetária;
- alçadas ou níveis de aprovação por valor (qualquer aprovação segue apenas a regra de rateio de 100%);
- emissão de boletos, remessa bancária ou conciliação;
- retenção de impostos;
- autenticação e perfis de usuário nesta versão.
