"""Contrato mínimo entre a aplicação e um provider de LLM.

Representa apenas o que usamos hoje. Nenhum código fora de `ai/providers/`
precisa conhecer o formato da SDK de um fornecedor.
"""

from typing import Any, Literal, Protocol, Self

from pydantic import BaseModel, Field, model_validator


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


class ChatMessage(BaseModel):
    """Mensagem do histórico.

    - system/user/assistant: texto em `content`.
    - assistant pedindo tools: `tool_calls` (o `content` pode ser vazio).
    - tool: resultado de uma tool em `content`, ligado ao pedido por `tool_call_id`.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None

    @model_validator(mode="after")
    def _coerente_com_o_role(self) -> Self:
        if self.tool_calls and self.role != "assistant":
            raise ValueError("Somente mensagens do assistant podem conter tool_calls.")
        if (self.role == "tool") != (self.tool_call_id is not None):
            raise ValueError("tool_call_id é obrigatório em mensagens tool e só nelas.")
        return self


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


class EmbeddingProvider(Protocol):
    name: str

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Um vetor por texto, na mesma ordem."""
        ...

    def embed_query(self, text: str) -> list[float]: ...
