from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (ou de um arquivo .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://ap_copilot:ap_copilot@localhost:5432/ap_copilot"
    test_database_url: str = (
        "postgresql+psycopg://ap_copilot:ap_copilot@localhost:5432/ap_copilot_test"
    )
    log_level: str = "INFO"
    # Origens do frontend autorizadas a chamar a API pelo navegador (lista JSON no .env).
    cors_origins: list[str] = ["http://localhost:5173"]

    # IA — opcionais: a API financeira funciona sem eles. A falta só gera erro
    # quando algo que usa o LLM é chamado (ver app.ai.providers.get_llm_provider).
    llm_provider: str = "openai"
    openai_api_key: SecretStr | None = None  # SecretStr: nunca aparece em repr/logs
    openai_model: str | None = None
    openai_reasoning_effort: str | None = None  # ex.: "none"; vazio = não enviar
    openai_embedding_model: str = "text-embedding-3-small"
    llm_timeout_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
