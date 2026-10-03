from pydantic import BaseModel


class ToolUsada(BaseModel):
    """Tool executada pelo agente. Montado pela aplicação, não pelo modelo."""

    name: str
    ok: bool


class CopilotResponse(BaseModel):
    answer: str
    tools_used: list[ToolUsada]
