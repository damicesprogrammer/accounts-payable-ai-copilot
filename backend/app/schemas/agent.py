from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.rag import PerguntaInput

# Idiomas da interface; o agente responde no idioma escolhido.
Idioma = Literal["pt-BR", "en-US"]


class CopilotInput(PerguntaInput):
    language: Idioma = Field(default="pt-BR", description="Idioma da resposta.")


class ToolUsada(BaseModel):
    """Tool executada pelo agente. Montado pela aplicação, não pelo modelo."""

    name: str
    ok: bool


class CopilotResponse(BaseModel):
    answer: str
    tools_used: list[ToolUsada]
