from typing import Annotated

from pydantic import Field, StringConstraints

from app.schemas.common import InputSchema, ReadSchema, TextoObrigatorio

Codigo = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20, to_upper=True)
]


class CentroCustoCreate(InputSchema):
    codigo: Codigo = Field(examples=["1001"])
    descricao: Annotated[TextoObrigatorio, Field(max_length=200)]


class CentroCustoUpdate(InputSchema):
    """O código não muda: ele é a referência usada em integrações e rateios.

    Inativar (ativo=false) impede novos rateios (regra 4) sem apagar o histórico.
    """

    descricao: Annotated[TextoObrigatorio, Field(max_length=200)]
    ativo: bool


class CentroCustoRead(ReadSchema):
    id: int
    codigo: str
    descricao: str
    ativo: bool
