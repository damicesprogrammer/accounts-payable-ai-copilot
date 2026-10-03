"""Registry de tools: a allowlist do que o LLM pode executar.

O nome vindo do modelo é usado apenas como chave de um dicionário de tools
registradas explicitamente. Não há eval, exec, import dinâmico nem getattr
baseado em texto do modelo.
"""

import logging
import time

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai.contracts import EmbeddingProvider, ToolCall, ToolDefinition
from app.ai.exceptions import LLMError
from app.core.exceptions import DomainError
from app.tools import documentacao_tools, fornecedor_tools, titulo_tools
from app.tools.contracts import Tool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' já registrada.")
        self._tools[tool.name] = tool

    @property
    def names(self) -> list[str]:
        return list(self._tools)

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]

    def execute(self, call: ToolCall, db: Session) -> ToolResult:
        inicio = time.perf_counter()
        resultado = self._execute(call, db)
        logger.info(
            "Tool executada",
            extra={
                "tool": call.name[:100],
                "ok": resultado.ok,
                "error_code": resultado.error.code if resultado.error else None,
                "duration_ms": round((time.perf_counter() - inicio) * 1000),
            },
        )
        return resultado

    def _execute(self, call: ToolCall, db: Session) -> ToolResult:
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolResult.falha(
                "TOOL_NAO_PERMITIDA", f"A tool '{call.name[:100]}' não está disponível."
            )

        try:
            argumentos = tool.input_model.model_validate(call.arguments)
        except ValidationError as exc:
            return ToolResult.falha("ARGUMENTOS_INVALIDOS", _resumo_validacao(exc))

        try:
            return ToolResult.sucesso(tool.handler(db, argumentos))
        except DomainError as exc:
            # Erros de negócio são informação útil para o modelo: mantém o código do domínio.
            return ToolResult.falha(exc.code, exc.message)
        except LLMError as exc:
            # Ex.: search_documentation sem API key. As mensagens da camada de IA não
            # contêm segredos nem texto bruto do fornecedor.
            return ToolResult.falha("IA_INDISPONIVEL", str(exc))
        except Exception:
            # Detalhes ficam no log do servidor; o modelo recebe apenas uma mensagem genérica.
            logger.exception("Erro inesperado ao executar tool", extra={"tool": tool.name})
            return ToolResult.falha("ERRO_INTERNO", "Erro interno ao executar a tool.")


def _resumo_validacao(exc: ValidationError) -> str:
    erros = [
        f"{'.'.join(str(parte) for parte in erro['loc']) or 'argumentos'}: {erro['msg']}"
        for erro in exc.errors()
    ]
    return "Argumentos inválidos — " + "; ".join(erros)


def criar_registry_financeiro(embeddings: EmbeddingProvider | None = None) -> ToolRegistry:
    """Allowlist explícita das tools disponíveis ao LLM. Todas somente leitura.

    `embeddings` permite injetar o provider da search_documentation (ex.: fake nos testes).
    """
    registry = ToolRegistry()
    registry.register(titulo_tools.get_titulo)
    registry.register(titulo_tools.get_rateios_titulo)
    registry.register(titulo_tools.get_pagamentos_titulo)
    registry.register(titulo_tools.get_logs_titulo)
    registry.register(titulo_tools.get_titulos_vencidos)
    registry.register(titulo_tools.get_titulos_por_status)
    registry.register(fornecedor_tools.get_fornecedores)
    registry.register(documentacao_tools.search_documentation(embeddings))
    return registry
