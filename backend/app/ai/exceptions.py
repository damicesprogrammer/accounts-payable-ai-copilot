"""Erros da camada de IA.

As mensagens nunca incluem API keys nem o conteúdo bruto de respostas de erro
do fornecedor (que podem conter dados sensíveis).
"""


class LLMError(Exception):
    """Base de todos os erros da camada de IA."""


class LLMConfigurationError(LLMError):
    """Provider desconhecido, API key ou modelo não configurados."""


class LLMTimeoutError(LLMError):
    """O provider não respondeu dentro do tempo limite."""


class LLMProviderError(LLMError):
    """Falha na chamada ao provider ou resposta em formato inesperado."""


class LLMStructuredOutputError(LLMError):
    """A resposta não é compatível com o schema solicitado."""
