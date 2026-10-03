from fastapi import FastAPI

app = FastAPI(
    title="AP Copilot",
    description="Módulo simplificado de Títulos a Pagar",
    version="0.1.0",
)


@app.get("/health", tags=["infra"])
def health() -> dict[str, str]:
    return {"status": "ok"}
