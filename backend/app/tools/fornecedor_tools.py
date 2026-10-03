"""Tool de consulta de fornecedores (somente leitura).

Chama apenas métodos de leitura do FornecedorService; nenhuma faz commit,
altera dados ou acessa repositories/SQL.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.services.fornecedor_service import FornecedorService
from app.tools.contracts import Tool

# Quantidade calculada pelo sistema + o básico de cada fornecedor.
_CAMPOS_FORNECEDORES = {
    "quantidade": True,
    "fornecedores": {"__all__": {"id", "nome", "cnpj", "ativo"}},
}


class FornecedoresInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ativo: bool | None = Field(
        default=None,
        description="true: só ativos; false: só inativos; omitido: todos.",
    )


def _get_fornecedores(db: Session, args: FornecedoresInput) -> dict[str, Any]:
    resumo = FornecedorService(db).resumo(ativo=args.ativo)
    return resumo.model_dump(mode="json", include=_CAMPOS_FORNECEDORES)


get_fornecedores = Tool(
    name="get_fornecedores",
    description=(
        "Consulta os fornecedores cadastrados (todos, só ativos ou só inativos), com a "
        "quantidade já calculada pelo sistema."
    ),
    input_model=FornecedoresInput,
    handler=_get_fornecedores,
)
