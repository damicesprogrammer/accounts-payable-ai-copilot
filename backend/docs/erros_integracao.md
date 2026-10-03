# Erros de integração

## Integração com o ERP de destino

Os títulos do AP Copilot são enviados a um ERP de destino. Quando o ERP rejeita um título, o AP Copilot marca o título com o status `ERRO` e grava a mensagem de rejeição na trilha de auditoria.

- Títulos `PENDENTE` ou `APROVADO` podem ir para `ERRO`.
- O registro de auditoria da falha tem o tipo `INTEGRACAO` e o status `ERRO`.
- Nesta versão a integração é simulada: os erros são gerados pelos dados de demonstração, sem comunicação com um ERP real.

## Título em ERRO

- Um título em `ERRO` não recebe pagamentos (erro `TITULO_NAO_APROVADO`).
- Seus dados e rateios podem ser alterados, para corrigir a causa da rejeição.
- Ele continua em aberto: se a data de vencimento já passou, aparece como vencido.
- Pode ser cancelado, desde que não tenha pagamentos confirmados.
- Não pode ser aprovado diretamente: precisa ser reprocessado antes.

## Fornecedor não cadastrado no ERP

Exemplo de mensagem: "Integração ERP rejeitou o título: fornecedor CNPJ 11222333000181 não cadastrado no ERP de destino."

- Causa: o fornecedor existe no AP Copilot, mas o CNPJ não está cadastrado no ERP de destino.
- Correção: cadastrar o fornecedor no ERP de destino (fora do AP Copilot) e depois reprocessar o título.

## Centro de custo inexistente no ERP

Exemplo de mensagem: "Integração ERP rejeitou o título: centro de custo 1001 inexistente no ERP de destino."

- Causa: um rateio do título usa um centro de custo que não existe no ERP de destino.
- Correção: cadastrar o centro de custo no ERP de destino, ou remover o rateio e ratear o valor em um centro de custo existente no ERP. Como o título está em `ERRO`, os rateios podem ser alterados. Depois, reprocessar o título.

## Reprocessamento

- O reprocessamento é feito em `POST /titulos/{id}/reprocessar` e muda o título de `ERRO` para `PENDENTE`.
- Só títulos em `ERRO` podem ser reprocessados. Em qualquer outro estado, a operação é recusada com o erro `TRANSICAO_STATUS_INVALIDA`.
- O título volta para `PENDENTE`, não para `APROVADO`. Ele precisa ser aprovado de novo, com rateio de 100%, para receber pagamentos.
- O AP Copilot não verifica se a causa foi corrigida no ERP: o reprocessamento apenas reabre o fluxo. Corrija a causa antes de reprocessar.

## Como investigar um erro de integração

1. Consulte a trilha de auditoria do título em `GET /titulos/{id}/logs`.
2. Localize o registro do tipo `INTEGRACAO` com status `ERRO`; a descrição traz a mensagem do ERP.
3. Identifique a causa (fornecedor ou centro de custo) e corrija.
4. Reprocesse o título e aprove-o novamente.
