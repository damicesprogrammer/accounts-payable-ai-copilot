# Regras de pagamentos

## Registro de pagamento

- Pagamentos só podem ser registrados para títulos `APROVADO`.
- Título `PENDENTE` ou `ERRO` recusa pagamento com o erro `TITULO_NAO_APROVADO`.
- Título `CANCELADO` recusa pagamento com o erro `TITULO_CANCELADO`.
- Título `PAGO` recusa novos pagamentos com o erro `TITULO_JA_PAGO`.
- O valor do pagamento deve ser maior que zero.
- A data do pagamento não pode ser anterior à data de emissão do título (erro `DATA_PAGAMENTO_INVALIDA`).
- Todo pagamento registrado nasce com o status `CONFIRMADO`.

## Saldo pendente e pagamentos parciais

- O saldo pendente é o valor total do título menos a soma dos pagamentos confirmados. Pagamentos estornados não entram na conta.
- Um título pode ser pago em várias parcelas (pagamentos parciais).
- Um pagamento não pode ultrapassar o saldo pendente. Se ultrapassar, é recusado com o erro `PAGAMENTO_EXCEDE_SALDO`, que informa o valor total, o já pago e o saldo.
- Exemplo: em um título de 3.000,00 com 1.200,00 pagos, o saldo é 1.800,00; um pagamento de 2.000,00 é recusado.
- Pagamentos simultâneos no mesmo título são processados um de cada vez, então juntos também não conseguem ultrapassar o saldo.

## Quitação automática

- Quando os pagamentos confirmados atingem exatamente o valor total, o título passa automaticamente para `PAGO`, na mesma operação do último pagamento.
- Não existe ação manual para marcar um título como pago. Um título só fica `PAGO` com pagamentos que quitam o valor total (garantia `PAGAMENTOS_NAO_QUITAM_TITULO`).

## Título PAGO

- Não aceita novos pagamentos.
- Não aceita edição de dados nem alteração de rateios.
- Não pode ser cancelado, porque tem pagamentos confirmados.
- A única operação permitida é estornar um pagamento confirmado.

## Estorno de pagamento

- Somente pagamentos `CONFIRMADO` podem ser estornados. Estornar um pagamento já estornado gera o erro `PAGAMENTO_JA_ESTORNADO`.
- O estorno só é permitido em títulos `APROVADO` ou `PAGO` (erro `ESTORNO_NAO_PERMITIDO` nos demais estados).
- O pagamento estornado não é apagado: ele permanece no histórico com o status `ESTORNADO` e deixa de contar no valor pago.
- Em um título `APROVADO`, o estorno mantém o status `APROVADO` e apenas recalcula o saldo pendente.
- O estorno é registrado na trilha de auditoria.

## Estorno de título PAGO

- Quando um pagamento de um título `PAGO` é estornado, o título volta para `PENDENTE`, e não para `APROVADO`.
- A mudança de status acontece na mesma operação do estorno.
- Os demais pagamentos confirmados do título continuam confirmados e contam no valor pago.
- Exemplo: um título de 2.000,00 pago em duas parcelas de 1.000,00 tem uma parcela estornada. Ele volta a `PENDENTE` com 1.000,00 pagos e 1.000,00 de saldo.

## Nova aprovação após estorno

- Como volta para `PENDENTE`, o título reaberto precisa ser aprovado novamente antes de receber novos pagamentos.
- Enquanto estiver `PENDENTE`, o título pode ser editado, mas o valor total não pode ficar abaixo do já pago (erro `VALOR_MENOR_QUE_PAGO`).
- A nova aprovação segue a regra normal: rateio de exatamente 100% do valor total.
- Depois de aprovado de novo, o título aceita pagamentos até o saldo pendente e volta a ser quitado automaticamente.
