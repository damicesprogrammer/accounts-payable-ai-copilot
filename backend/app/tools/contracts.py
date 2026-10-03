from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.contracts import ToolDefinition

# Dados devolvidos por uma tool: já serializáveis em JSON (Decimal vira string).
JsonData = dict[str, Any] | list[dict[str, Any]]


@dataclass(frozen=True)
class Tool:
    """Uma função que o LLM pode solicitar.

    `input_model` valida os argumentos enviados pelo modelo antes de qualquer
    execução; `handler` recebe a sessão e os argumentos já validados e chama
    services — nunca repositories ou SQL.
    """

    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[Session, Any], JsonData]

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            input_schema=self.input_model.model_json_schema(),
        )


class ToolError(BaseModel):
    code: str
    message: str


class ToolResult(BaseModel):
    ok: bool
    data: JsonData | None = None
    error: ToolError | None = None

    @classmethod
    def sucesso(cls, data: JsonData) -> "ToolResult":
        return cls(ok=True, data=data)

    @classmethod
    def falha(cls, code: str, message: str) -> "ToolResult":
        return cls(ok=False, error=ToolError(code=code, message=message))
