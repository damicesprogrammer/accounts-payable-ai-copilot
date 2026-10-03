"""Provider de embeddings da OpenAI.

Pede vetores com dimensão fixa (EMBEDDING_DIM), a mesma da coluna pgvector.
"""

import logging
import time

import openai
from pydantic import SecretStr

from app.ai.exceptions import LLMProviderError, LLMTimeoutError
from app.models import EMBEDDING_DIM

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        *,
        timeout: float = 30.0,
        client: openai.OpenAI | None = None,  # injetável nos testes (sem rede)
    ) -> None:
        self.model = model
        self._client = client or openai.OpenAI(
            api_key=api_key.get_secret_value(), timeout=timeout, max_retries=1
        )

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        inicio = time.perf_counter()
        try:
            resposta = self._client.embeddings.create(
                model=self.model, input=texts, dimensions=EMBEDDING_DIM
            )
        except openai.APITimeoutError:
            raise LLMTimeoutError("A OpenAI não respondeu dentro do tempo limite.") from None
        except openai.APIStatusError as exc:
            # Não reaproveita o texto do fornecedor: ele pode ecoar parte da API key.
            raise LLMProviderError(
                f"A OpenAI recusou a chamada de embeddings (HTTP {exc.status_code})."
            ) from None
        except openai.OpenAIError as exc:
            raise LLMProviderError(
                f"Falha na chamada de embeddings à OpenAI ({type(exc).__name__})."
            ) from None

        # A API devolve um item por entrada, com `index`; ordena por garantia.
        vetores = [item.embedding for item in sorted(resposta.data, key=lambda i: i.index)]
        logger.info(
            "Embeddings gerados",
            extra={
                "provider": self.name,
                "model": self.model,
                "textos": len(texts),
                "input_tokens": resposta.usage.prompt_tokens if resposta.usage else None,
                "duration_ms": round((time.perf_counter() - inicio) * 1000),
            },
        )
        return vetores

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
