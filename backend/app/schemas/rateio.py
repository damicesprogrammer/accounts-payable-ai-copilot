from decimal import Decimal

from app.schemas.common import InputSchema, ReadSchema, ValorPositivo


class RateioCreate(InputSchema):
    centro_custo_id: int
    valor: ValorPositivo


class CentroCustoResumo(ReadSchema):
    id: int
    codigo: str
    descricao: str
    ativo: bool


class RateioRead(ReadSchema):
    id: int
    titulo_id: int
    centro_custo_id: int
    centro_custo: CentroCustoResumo
    valor: Decimal
