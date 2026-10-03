import json

import pytest

from app.ai.exceptions import LLMTimeoutError
from app.ai.providers import get_embedding_provider, get_llm_provider
from app.ai.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from app.api.routes.ai import embedding_provider, llm_provider
from app.core.config import Settings
from app.main import app
from app.rag.chunking import Chunk
from app.rag.service import SEM_INFORMACAO, RAGService

PERGUNTA = "O que acontece quando um pagamento de um título pago é estornado?"
ESTORNO = Chunk(
    "regras_pagamentos.md",
    "Estorno de título PAGO",
    "Quando um pagamento de um título PAGO é estornado, o título volta para PENDENTE.",
)


def _usar(embeddings, llm) -> None:
    app.dependency_overrides[embedding_provider] = lambda: embeddings
    app.dependency_overrides[llm_provider] = lambda: llm


def _resposta(answer: str, *fontes: tuple[str, str]) -> str:
    return json.dumps(
        {"answer": answer, "sources": [{"source": s, "section": sec} for s, sec in fontes]}
    )


@pytest.fixture
def indexado(db):
    RAGService(db, FakeEmbeddingProvider()).indexar([ESTORNO])


def test_ask_responde_com_fontes(client, indexado):
    llm = FakeLLMProvider(
        [_resposta("O título volta para PENDENTE.", (ESTORNO.source, ESTORNO.section))]
    )
    _usar(FakeEmbeddingProvider(), llm)

    resposta = client.post("/ai/ask", json={"question": PERGUNTA})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "answer": "O título volta para PENDENTE.",
        "sources": [{"source": "regras_pagamentos.md", "section": "Estorno de título PAGO"}],
    }
    assert ESTORNO.content in llm.chamadas[0]["messages"][1].content


def test_ask_sem_documentos_indexados(client):
    _usar(FakeEmbeddingProvider(), FakeLLMProvider([]))

    resposta = client.post("/ai/ask", json={"question": PERGUNTA})

    assert resposta.status_code == 200
    assert resposta.json() == {"answer": SEM_INFORMACAO, "sources": []}


def test_ask_sem_configuracao_retorna_erro_tratado(client):
    sem_chave = Settings(_env_file=None, openai_api_key="", openai_model="")
    app.dependency_overrides[embedding_provider] = lambda: get_embedding_provider(sem_chave)
    app.dependency_overrides[llm_provider] = lambda: get_llm_provider(sem_chave)

    resposta = client.post("/ai/ask", json={"question": PERGUNTA})

    assert resposta.status_code == 503
    erro = resposta.json()["error"]
    assert erro["code"] == "IA_NAO_CONFIGURADA"
    assert "OPENAI_API_KEY" in erro["message"]
    assert "Traceback" not in resposta.text


def test_ask_com_fonte_inventada_retorna_502(client, indexado):
    llm = FakeLLMProvider([_resposta("Há juros de 2%.", ("politica_juros.md", "Juros"))])
    _usar(FakeEmbeddingProvider(), llm)

    resposta = client.post("/ai/ask", json={"question": "Qual a multa por atraso?"})

    assert resposta.status_code == 502
    assert resposta.json()["error"]["code"] == "IA_RESPOSTA_INVALIDA"
    assert "juros" not in resposta.text.lower()  # a resposta recusada não vaza


def test_ask_timeout_do_provider_retorna_504(client, indexado):
    _usar(FakeEmbeddingProvider(), FakeLLMProvider([LLMTimeoutError("A OpenAI não respondeu.")]))

    resposta = client.post("/ai/ask", json={"question": PERGUNTA})

    assert resposta.status_code == 504
    assert resposta.json()["error"]["code"] == "IA_TIMEOUT"


@pytest.mark.parametrize(
    "payload",
    [{}, {"question": "   "}, {"question": "x" * 1001}, {"question": "ok", "sql": "DROP"}],
)
def test_ask_valida_a_pergunta(client, payload):
    _usar(FakeEmbeddingProvider(), FakeLLMProvider([]))

    assert client.post("/ai/ask", json=payload).status_code == 422


def test_api_financeira_continua_sem_api_key(client):
    assert client.get("/titulos").status_code == 200
