from app.ai.contracts import LLMProvider
from app.ai.exceptions import LLMConfigurationError
from app.ai.providers.openai import OpenAIProvider
from app.core.config import Settings, get_settings


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Cria o provider configurado em LLM_PROVIDER.

    Chamado apenas por quem realmente usa o LLM: a aplicação sobe sem API key.
    """
    settings = settings or get_settings()

    if settings.llm_provider != "openai":
        raise LLMConfigurationError(f"LLM_PROVIDER não suportado: '{settings.llm_provider}'.")
    if settings.openai_api_key is None or not settings.openai_api_key.get_secret_value():
        raise LLMConfigurationError("OPENAI_API_KEY não configurada.")
    if not settings.openai_model:
        raise LLMConfigurationError("OPENAI_MODEL não configurado.")

    return OpenAIProvider(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        timeout=settings.llm_timeout_seconds,
    )
