"""Contrato mínimo entre a aplicação e um provider de LLM.

Representa apenas o que usamos hoje. Nenhum código fora de `ai/providers/`
precisa conhecer o formato da SDK de um fornecedor.
"""

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ToolDefinition(BaseModel):
    """Ferramenta oferecida ao modelo. `input_schema` é um JSON Schema."""

    name: str
    description: str
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    """Pedido do modelo para executar uma ferramenta, já normalizado."""

    id: str
    name: str
    arguments: dict[str, Any]


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int


class LLMResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    model: str
    finish_reason: str | None = None
    usage: TokenUsage | None = None


class LLMProvider(Protocol):
    name: str

    def generate(
        self, messages: list[ChatMessage], *, tools: list[ToolDefinition] | None = None
    ) -> LLMResponse:
        """Gera uma resposta, que pode conter texto e/ou pedidos de tool."""
        ...

    def generate_structured[T: BaseModel](
        self, messages: list[ChatMessage], response_model: type[T]
    ) -> T:
        """Gera uma resposta validada contra `response_model`.

        Lança LLMStructuredOutputError se a resposta não for compatível —
        nunca devolve objeto parcialmente validado.
        """
        ...
