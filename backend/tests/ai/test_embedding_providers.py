"""Providers de embedding sem rede: o cliente da SDK é substituído por um stub."""

import logging
from types import SimpleNamespace

import httpx
import openai
import pytest
from openai.types import CreateEmbeddingResponse
from pydantic import SecretStr

from app.ai.exceptions import LLMConfigurationError, LLMProviderError, LLMTimeoutError
from app.ai.providers import get_embedding_provider
from app.ai.providers.fake import FakeEmbeddingProvider
from app.ai.providers.openai_embeddings import OpenAIEmbeddingProvider
from app.core.config import Settings
from app.models import EMBEDDING_DIM

API_KEY = "sk-test-SEGREDO-NAO-PODE-VAZAR"
REQUEST = httpx.Request("POST", "https://api.openai.com/v1/embeddings")


class StubEmbeddings:
    def __init__(self, resultado):
        self.resultado = resultado
        self.kwargs: dict = {}

    def create(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


def _provider(resultado) -> tuple[OpenAIEmbeddingProvider, StubEmbeddings]:
    stub = StubEmbeddings(resultado)
    client = SimpleNamespace(embeddings=stub)
    return OpenAIEmbeddingProvider(SecretStr(API_KEY), "emb-teste", client=client), stub


def _resposta(*vetores: list[float]) -> CreateEmbeddingResponse:
    # Fora de ordem de propósito: o provider deve respeitar `index`.
    data = [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vetores)][
        ::-1
    ]
    return CreateEmbeddingResponse.model_validate(
        {
            "object": "list",
            "model": "emb-teste",
            "data": data,
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }
    )


# ---------------------------------------------------------------- OpenAI


def test_openai_pede_dimensao_fixa_e_preserva_a_ordem(caplog):
    caplog.set_level(logging.INFO, logger="app.ai.providers.openai_embeddings")
    provider, stub = _provider(_resposta([1.0, 0.0], [0.0, 1.0]))

    vetores = provider.embed_texts(["primeiro texto", "segundo texto"])

    assert vetores == [[1.0, 0.0], [0.0, 1.0]]
    assert stub.kwargs == {
        "model": "emb-teste",
        "input": ["primeiro texto", "segundo texto"],
        "dimensions": EMBEDDING_DIM,
    }
    [registro] = caplog.records
    assert (registro.textos, registro.input_tokens) == (2, 5)
    assert "primeiro texto" not in caplog.text  # textos não são registrados


def test_openai_embed_query_devolve_um_vetor():
    provider, stub = _provider(_resposta([0.5, 0.5]))

    assert provider.embed_query("pergunta") == [0.5, 0.5]
    assert stub.kwargs["input"] == ["pergunta"]


def test_openai_timeout_vira_llm_timeout_error():
    provider, _ = _provider(openai.APITimeoutError(request=REQUEST))

    with pytest.raises(LLMTimeoutError):
        provider.embed_texts(["x"])


def test_openai_erro_http_nao_ecoa_a_mensagem_do_fornecedor():
    erro = openai.AuthenticationError(
        f"Incorrect API key provided: {API_KEY}",
        response=httpx.Response(401, request=REQUEST),
        body=None,
    )
    provider, _ = _provider(erro)

    with pytest.raises(LLMProviderError) as exc:
        provider.embed_texts(["x"])

    assert "401" in str(exc.value)
    assert API_KEY not in str(exc.value)


# ---------------------------------------------------------------- configuração


def test_sem_api_key_o_provider_de_embeddings_nao_e_criado():
    settings = Settings(_env_file=None, openai_api_key="")

    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
        get_embedding_provider(settings)


def test_sem_modelo_de_embedding_o_provider_nao_e_criado():
    settings = Settings(_env_file=None, openai_api_key=API_KEY, openai_embedding_model="")

    with pytest.raises(LLMConfigurationError, match="OPENAI_EMBEDDING_MODEL"):
        get_embedding_provider(settings)


def test_provider_de_embeddings_configurado_e_criado_sem_chamar_a_api():
    settings = Settings(
        _env_file=None, openai_api_key=API_KEY, openai_embedding_model="text-embedding-3-small"
    )

    provider = get_embedding_provider(settings)

    assert isinstance(provider, OpenAIEmbeddingProvider)
    assert provider.model == "text-embedding-3-small"


# ---------------------------------------------------------------- fake


def test_fake_e_deterministico_e_tem_a_dimensao_da_coluna():
    fake = FakeEmbeddingProvider()

    [a, b] = fake.embed_texts(["Estorno de pagamento", "Estorno de pagamento"])

    assert a == b
    assert len(a) == EMBEDDING_DIM
    assert fake.embed_query("") != [0.0] * EMBEDDING_DIM  # nunca devolve vetor nulo
    assert fake.chamadas == [["Estorno de pagamento", "Estorno de pagamento"], [""]]


def test_fake_pode_simular_falha():
    fake = FakeEmbeddingProvider(erro=LLMTimeoutError("timeout simulado"))

    with pytest.raises(LLMTimeoutError):
        fake.embed_query("x")
