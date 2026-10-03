import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.ai.exceptions import (
    LLMConfigurationError,
    LLMError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from app.core.exceptions import BusinessRuleError, ConflictError, DomainError, NotFoundError

logger = logging.getLogger(__name__)

_STATUS_BY_ERROR: dict[type[DomainError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    BusinessRuleError: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    http_status = next(
        (s for cls, s in _STATUS_BY_ERROR.items() if isinstance(exc, cls)),
        status.HTTP_400_BAD_REQUEST,
    )
    logger.info(
        "Operação recusada pelo domínio",
        extra={"error_code": exc.code, "path": request.url.path},
    )
    return JSONResponse(
        status_code=http_status,
        content=_error_body(exc.code, exc.message, exc.details),
    )


# Erros da camada de IA: (status HTTP, código). A ordem importa — o primeiro
# isinstance vence, e LLMError é o fallback.
_STATUS_BY_LLM_ERROR: list[tuple[type[LLMError], int, str]] = [
    (LLMConfigurationError, status.HTTP_503_SERVICE_UNAVAILABLE, "IA_NAO_CONFIGURADA"),
    (LLMTimeoutError, status.HTTP_504_GATEWAY_TIMEOUT, "IA_TIMEOUT"),
    (LLMStructuredOutputError, status.HTTP_502_BAD_GATEWAY, "IA_RESPOSTA_INVALIDA"),
    (LLMError, status.HTTP_502_BAD_GATEWAY, "IA_INDISPONIVEL"),
]


async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    http_status, code = next((s, c) for cls, s, c in _STATUS_BY_LLM_ERROR if isinstance(exc, cls))
    # As mensagens da camada de IA não contêm segredos nem texto bruto do fornecedor.
    logger.warning("Falha na camada de IA", extra={"error_code": code, "path": request.url.path})
    return JSONResponse(status_code=http_status, content=_error_body(code, str(exc)))


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Detalhes internos vão para o log, nunca para a resposta.
    logger.exception("Erro inesperado", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("ERRO_INTERNO", "Erro interno inesperado."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(LLMError, llm_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
