from pathlib import Path

import pytest

from app.ai.contracts import ToolCall
from app.ai.providers import get_embedding_provider
from app.ai.providers.fake import FakeEmbeddingProvider
from app.core.config import Settings
from app.rag.chunking import Chunk
from app.rag.service import RAGService
from app.tools import documentacao_tools
from app.tools.registry import criar_registry_financeiro

APP_DIR = Path(__file__).resolve().parents[2] / "app"

CHUNKS = [
    Chunk("regras_pagamentos.md", "Estorno de título PAGO", "Estorno de PAGO volta a PENDENTE."),
    Chunk("regras_rateios.md", "Rateio", "Rateio de 100% para aprovar."),
]


@pytest.fixture
def embeddings():
    return FakeEmbeddingProvider()


@pytest.fixture
def registry(embeddings):
    return criar_registry_financeiro(embeddings)


def _buscar(registry, db, query: str):
    return registry.execute(
        ToolCall(id="call_1", name="search_documentation", arguments={"query": query}), db
    )


def test_retorna_somente_trechos_de_documentacao(registry, embeddings, db):
    RAGService(db, embeddings).indexar(CHUNKS)

    resultado = _buscar(registry, db, "estorno de título PAGO")

    assert resultado.ok is True
    assert embeddings.chamadas[-1] == ["estorno de título PAGO"]
    primeiro = resultado.data[0]
    assert set(primeiro) == {"source", "section", "content", "score"}
    assert (primeiro["source"], primeiro["section"]) == (
        "regras_pagamentos.md",
        "Estorno de título PAGO",
    )
    assert isinstance(primeiro["score"], float)
    assert len(resultado.data) == 2


def test_indice_vazio_retorna_lista_vazia(registry, db):
    resultado = _buscar(registry, db, "estorno")

    assert (resultado.ok, resultado.data) == (True, [])


def test_definicao_exposta_ao_llm(registry):
    [definicao] = [d for d in registry.definitions() if d.name == "search_documentation"]

    assert definicao.input_schema["required"] == ["query"]
    assert definicao.input_schema["additionalProperties"] is False


def test_nao_chama_o_llm():
    """Só retrieval: quem gera a resposta é o modelo que pediu a tool."""
    fonte = (APP_DIR / "tools" / "documentacao_tools.py").read_text(encoding="utf-8")
    for proibido in ("get_llm_provider", "LLMProvider", ".answer(", "generate"):
        assert proibido not in fonte


def test_sem_api_key_retorna_erro_claro_sem_derrubar_a_aplicacao(db, monkeypatch):
    sem_chave = Settings(_env_file=None, openai_api_key="")
    monkeypatch.setattr(
        documentacao_tools, "get_embedding_provider", lambda: get_embedding_provider(sem_chave)
    )
    registry = criar_registry_financeiro()  # sem provider injetado: usa o configurado

    resultado = _buscar(registry, db, "estorno")

    assert resultado.ok is False
    assert resultado.error.code == "IA_INDISPONIVEL"
    assert "OPENAI_API_KEY" in resultado.error.message
