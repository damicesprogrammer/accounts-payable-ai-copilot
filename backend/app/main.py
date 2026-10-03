from fastapi import FastAPI

from app.api.routes import fornecedores
from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import RequestIdMiddleware, configure_logging

configure_logging(get_settings().log_level)

app = FastAPI(
    title="AP Copilot",
    description="Módulo simplificado de Títulos a Pagar",
    version="0.1.0",
)
app.add_middleware(RequestIdMiddleware)
register_error_handlers(app)

app.include_router(fornecedores.router)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
