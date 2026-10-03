from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, Field

from app.core import cnpj as cnpj_utils
from app.schemas.common import InputSchema, ReadSchema, TextoObrigatorio


def _validar_cnpj(valor: str) -> str:
    digitos = cnpj_utils.normalizar(valor)
    if not cnpj_utils.is_valido(digitos):
        raise ValueError("CNPJ inválido")
    return digitos


CNPJ = Annotated[str, AfterValidator(_validar_cnpj)]


class FornecedorCreate(InputSchema):
    nome: Annotated[TextoObrigatorio, Field(max_length=200)]
    cnpj: CNPJ = Field(examples=["11.222.333/0001-81"])


class FornecedorUpdate(InputSchema):
    """CNPJ é a identidade fiscal do fornecedor e não pode ser alterado.

    Não existe exclusão física: inativar (ativo=false) preserva o histórico de
    títulos e impede novos lançamentos (regra 3).
    """

    nome: Annotated[TextoObrigatorio, Field(max_length=200)]
    ativo: bool


class FornecedorRead(ReadSchema):
    id: int
    nome: str
    cnpj: str
    ativo: bool
    created_at: datetime


class FornecedoresResumo(ReadSchema):
    """Fornecedores do filtro pedido; `quantidade` é calculada pelo sistema."""

    quantidade: int
    fornecedores: list[FornecedorRead]
