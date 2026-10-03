from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.common import InputSchema


class PerguntaInput(InputSchema):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]


class TrechoRecuperado(BaseModel):
    """Chunk devolvido pela busca semântica. `score` = similaridade de cosseno."""

    source: str
    section: str
    content: str
    score: float


class FonteResposta(BaseModel):
    source: str = Field(description="Nome do arquivo, exatamente como aparece no contexto.")
    section: str = Field(description="Seção, exatamente como aparece no contexto.")


class RespostaRAG(BaseModel):
    """Structured output pedido ao LLM e também a resposta de POST /ai/ask."""

    answer: str = Field(description="Resposta baseada somente no contexto recuperado.")
    sources: list[FonteResposta] = Field(
        description="Trechos do contexto usados na resposta. Vazio se não houver informação."
    )
