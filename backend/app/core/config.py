from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (ou de um arquivo .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://ap_copilot:ap_copilot@localhost:5432/ap_copilot"
    test_database_url: str = (
        "postgresql+psycopg://ap_copilot:ap_copilot@localhost:5432/ap_copilot_test"
    )
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
