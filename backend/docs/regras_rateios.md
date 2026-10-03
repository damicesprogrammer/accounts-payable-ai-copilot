# Regras de rateio

## O que é rateio

Rateio é a distribuição do valor de um título entre centros de custo. Cada rateio informa um centro de custo e um valor maior que zero.

- Um título pode ter vários rateios, mas no máximo um por centro de custo. Repetir o centro de custo no mesmo título gera o erro `RATEIO_DUPLICADO`.
- O rateio é feito em valor (não em percentual). O percentual de cobertura é a soma dos rateios dividida pelo valor total do título.
- Os rateios do título podem ser consultados em `GET /titulos/{id}/rateios`.

## Limite pelo valor do título

- A soma dos rateios nunca pode ultrapassar o valor total do título.
- Um rateio que ultrapasse o valor disponível é recusado com o erro `RATEIO_EXCEDE_VALOR_TITULO`, que informa o valor total, o já rateado e o disponível.
- Exemplo: em um título de 1.000,00 com 800,00 já rateados, o próximo rateio pode ser de no máximo 200,00.
- A regra também vale no sentido inverso: o valor do título não pode ser reduzido para menos que o total já rateado (erro `VALOR_MENOR_QUE_RATEIO`).

## Rateio de 100% para aprovação

- A aprovação exige que a soma dos rateios seja exatamente igual ao valor total do título, ou seja, 100% rateado.
- Título sem rateio ou parcialmente rateado não pode ser aprovado (erro `RATEIO_INCOMPLETO`).
- Para corrigir, adicione rateios até cobrir o valor faltante informado no erro e então aprove novamente.

## Centro de custo ativo

- Somente centros de custo ativos podem receber novos rateios. Um rateio para centro de custo inativo é recusado com o erro `CENTRO_CUSTO_INATIVO`.
- Centros de custo não são excluídos, apenas inativados, para preservar o histórico.
- Rateios criados antes da inativação continuam no título e não são removidos automaticamente. Eles não impedem a aprovação.
- Para trocar o centro de custo de um rateio, remova o rateio e crie outro em um centro ativo, enquanto o título ainda puder ser alterado.

## Quando o rateio pode ser alterado

- Rateios só podem ser adicionados ou removidos quando o título está `PENDENTE` ou `ERRO` (erro `TITULO_NAO_EDITAVEL` nos demais estados).
- Depois da aprovação, os rateios ficam congelados, pois a aprovação conferiu os 100%.
- Remover um rateio que não pertence ao título gera o erro `RATEIO_NAO_ENCONTRADO`.
- Toda inclusão e remoção de rateio é registrada na trilha de auditoria do título.
