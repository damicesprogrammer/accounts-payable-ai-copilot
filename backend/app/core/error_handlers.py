import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

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


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # Detalhes internos vão para o log, nunca para a resposta.
    logger.exception("Erro inesperado", extra={"path": request.url.path})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("ERRO_INTERNO", "Erro interno inesperado."),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
