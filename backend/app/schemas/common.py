from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Valor monetário: estritamente positivo, até 2 casas decimais (regra 6 na borda da API).
ValorPositivo = Annotated[Decimal, Field(gt=0, max_digits=14, decimal_places=2)]

TextoObrigatorio = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class InputSchema(BaseModel):
    """Base dos schemas de entrada: rejeita campos desconhecidos."""

    model_config = ConfigDict(extra="forbid")


class ReadSchema(BaseModel):
    """Base dos schemas de saída: lê atributos de objetos ORM."""

    model_config = ConfigDict(from_attributes=True)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict


class ErrorResponse(BaseModel):
    error: ErrorDetail
