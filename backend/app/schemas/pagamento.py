from datetime import date
from decimal import Decimal

from app.models import StatusPagamento
from app.schemas.common import InputSchema, ReadSchema, ValorPositivo


class PagamentoCreate(InputSchema):
    data_pagamento: date
    valor: ValorPositivo


class PagamentoRead(ReadSchema):
    id: int
    titulo_id: int
    data_pagamento: date
    valor: Decimal
    status: StatusPagamento
