"""RAGService contra o PostgreSQL real (pgvector), com providers fake: sem rede."""

import json
import logging

import pytest
from sqlalchemy import event, func, select

from app.ai.exceptions import LLMStructuredOutputError, LLMTimeoutError
from app.ai.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from app.models import EMBEDDING_DIM, ChunkDocumentacao
from app.rag.chunking import Chunk
from app.rag.service import PROMPT_SISTEMA, SEM_INFORMACAO, RAGService
from app.schemas.rag import TrechoRecuperado

ESTORNO = Chunk(
    "regras_pagamentos.md",
    "Estorno de título PAGO",
    "O estorno de um pagamento de título PAGO devolve o título para PENDENTE.",
)
RATEIO = Chunk(
    "regras_rateios.md",
    "Rateio de 100%",
    "A aprovação exige rateio entre centros de custo de exatamente 100% do valor.",
)
VENCIDO = Chunk(
    "regras_titulos.md",
    "Título vencido",
    "Vencido é o título em aberto com data de vencimento anterior a hoje.",
)
CHUNKS = [ESTORNO, RATEIO, VENCIDO]


def _indice(db) -> list[tuple[str, str, str]]:
    stmt = select(
        ChunkDocumentacao.source, ChunkDocumentacao.section, ChunkDocumentacao.content
    ).order_by(ChunkDocumentacao.id)
    return [tuple(linha) for linha in db.execute(stmt).all()]


def _service(db, llm=None, embeddings=None) -> RAGService:
    return RAGService(db, embeddings or FakeEmbeddingProvider(), llm)


def _indexado(db, chunks=CHUNKS, llm=None) -> RAGService:
    service = _service(db, llm)
    service.indexar(chunks)
    return service


def _resposta_llm(answer: str, *fontes: Chunk) -> str:
    return json.dumps(
        {"answer": answer, "sources": [{"source": f.source, "section": f.section} for f in fontes]}
    )


# ---------------------------------------------------------------- indexação


def test_indexacao_grava_chunks_com_embedding_da_dimensao_da_coluna(db, caplog):
    caplog.set_level(logging.INFO, logger="app.rag.service")
    embeddings = FakeEmbeddingProvider()

    total = RAGService(db, embeddings).indexar(CHUNKS)

    assert total == 3
    assert _indice(db) == [(c.source, c.section, c.content) for c in CHUNKS]
    dimensoes = db.scalars(select(func.vector_dims(ChunkDocumentacao.embedding)).distinct()).all()
    assert dimensoes == [EMBEDDING_DIM]
    # Um único lote de embeddings; o heading entra no texto vetorizado.
    [lote] = embeddings.chamadas
    assert lote[0] == f"{ESTORNO.section}\n\n{ESTORNO.content}"

    [registro] = [r for r in caplog.records if r.getMessage() == "Documentação indexada"]
    assert (registro.documentos, registro.chunks) == (3, 3)
    assert isinstance(registro.duration_ms, int)
    assert ESTORNO.content not in caplog.text  # conteúdo não é registrado


def test_reindexacao_substitui_o_indice_anterior(db):
    _indexado(db)

    _service(db).indexar([RATEIO])

    assert _indice(db) == [(RATEIO.source, RATEIO.section, RATEIO.content)]


def test_falha_no_provider_de_embeddings_preserva_o_indice_anterior(db):
    _indexado(db)
    antes = _indice(db)
    falha = FakeEmbeddingProvider(erro=LLMTimeoutError("timeout simulado"))

    with pytest.raises(LLMTimeoutError):
        RAGService(db, falha).indexar([RATEIO])

    assert _indice(db) == antes


class _DimensaoErrada:
    """Devolve vetores incompatíveis com a coluna: a gravação falha no banco."""

    name = "dimensao-errada"

    def embed_texts(self, texts):
        return [[1.0, 2.0, 3.0] for _ in texts]

    def embed_query(self, text):
        return [1.0, 2.0, 3.0]


def test_falha_na_gravacao_faz_rollback_sem_indice_parcial(db):
    _indexado(db)
    antes = _indice(db)

    with pytest.raises(Exception, match="dimensions"):
        RAGService(db, _DimensaoErrada()).indexar([RATEIO, VENCIDO])

    assert _indice(db) == antes  # nem apagou o antigo, nem gravou parte do novo


def test_indexacao_sem_chunks_e_recusada_sem_apagar_o_indice(db):
    _indexado(db)

    with pytest.raises(ValueError):
        _service(db).indexar([])

    assert len(_indice(db)) == 3


# ---------------------------------------------------------------- retrieval


def test_query_gera_embedding_e_busca_retorna_o_chunk_mais_proximo(db):
    embeddings = FakeEmbeddingProvider()
    RAGService(db, embeddings).indexar(CHUNKS)

    [primeiro, *_] = RAGService(db, embeddings).search("estorno de título PAGO")

    assert embeddings.chamadas[-1] == ["estorno de título PAGO"]
    assert (primeiro.source, primeiro.section) == (ESTORNO.source, ESTORNO.section)
    assert primeiro.content == ESTORNO.content


def test_resultados_ordenados_por_similaridade_com_score(db):
    service = _indexado(db)

    resultados = service.search(f"{VENCIDO.section}\n\n{VENCIDO.content}")

    assert resultados[0].section == VENCIDO.section
    assert resultados[0].score == pytest.approx(1.0)  # mesmo texto → mesmo vetor
    scores = [r.score for r in resultados]
    assert scores == sorted(scores, reverse=True)
    assert all(-1 <= s <= 1 for s in scores)


def test_limit_e_respeitado(db):
    service = _indexado(db)

    assert len(service.search("título", limit=2)) == 2
    assert len(service.search("título")) == 3  # default 5, mas só há 3 chunks


def test_similaridade_e_calculada_no_postgresql(db):
    service = _indexado(db)
    sqls: list[str] = []

    def capturar(conn, cursor, statement, *args):
        sqls.append(statement)

    conexao = db.connection()
    event.listen(conexao, "before_cursor_execute", capturar)
    try:
        service.search("estorno")
    finally:
        event.remove(conexao, "before_cursor_execute", capturar)

    [sql] = sqls
    assert "<=>" in sql  # operador de distância de cosseno do pgvector
    assert "LIMIT" in sql
    assert "embedding," not in sql.split("FROM")[0]  # vetores não voltam para o Python


def test_busca_em_indice_vazio_retorna_lista_vazia(db, caplog):
    caplog.set_level(logging.INFO, logger="app.rag.service")

    assert _service(db).search("qualquer coisa") == []

    [registro] = caplog.records
    assert registro.resultados == 0
    assert "qualquer coisa" not in caplog.text  # a pergunta não é registrada


# ---------------------------------------------------------------- answer


def test_chunks_recuperados_entram_no_contexto_do_llm(db):
    llm = FakeLLMProvider([_resposta_llm("Volta para PENDENTE.", ESTORNO)])
    service = _indexado(db, llm=llm)

    service.answer("O que acontece no estorno de título PAGO?")

    [chamada] = llm.chamadas
    sistema, usuario = chamada["messages"]
    assert (sistema.role, sistema.content) == ("system", PROMPT_SISTEMA)
    assert usuario.role == "user"
    for chunk in CHUNKS:
        assert f"source: {chunk.source} | section: {chunk.section}" in usuario.content
        assert chunk.content in usuario.content
    assert usuario.content.endswith("Pergunta: O que acontece no estorno de título PAGO?")


def test_prompt_exige_grounding():
    for regra in ("SOMENTE", "não há informação suficiente", "Não invente", "conhecimento externo"):
        assert regra in PROMPT_SISTEMA


def test_resposta_estruturada_com_fontes_validas_e_aceita(db):
    llm = FakeLLMProvider([_resposta_llm("Volta para PENDENTE.", ESTORNO)])

    resposta = _indexado(db, llm=llm).answer("Estorno de título PAGO?")

    assert resposta.answer == "Volta para PENDENTE."
    assert [(f.source, f.section) for f in resposta.sources] == [(ESTORNO.source, ESTORNO.section)]


def test_resposta_sem_fontes_e_aceita(db):
    llm = FakeLLMProvider([_resposta_llm("Não há informação suficiente na documentação.")])

    resposta = _indexado(db, llm=llm).answer("Qual a taxa de juros?")

    assert resposta.sources == []


@pytest.mark.parametrize(
    "fonte",
    [
        Chunk("politica_interna.md", "Juros", ""),  # documento inventado
        Chunk(ESTORNO.source, "Seção inventada", ""),  # arquivo real, seção inventada
        Chunk(RATEIO.source, ESTORNO.section, ""),  # combinação que não foi entregue
    ],
)
def test_fonte_inventada_pelo_llm_e_recusada(db, fonte):
    llm = FakeLLMProvider([_resposta_llm("Resposta.", ESTORNO, fonte)])

    with pytest.raises(LLMStructuredOutputError, match="fora|não estavam"):
        _indexado(db, llm=llm).answer("Estorno?")


def test_fonte_existente_no_indice_mas_nao_recuperada_e_recusada(db, monkeypatch):
    llm = FakeLLMProvider([_resposta_llm("Resposta.", VENCIDO)])
    service = _indexado(db, llm=llm)
    so_estorno = TrechoRecuperado(**vars(ESTORNO), score=0.9)
    monkeypatch.setattr(service, "search", lambda query: [so_estorno])

    with pytest.raises(LLMStructuredOutputError):
        service.answer("estorno")  # VENCIDO está no índice, mas não foi entregue ao modelo


def test_resposta_estruturada_invalida_e_recusada(db):
    llm = FakeLLMProvider(['{"answer": "sem o campo sources"}'])

    with pytest.raises(LLMStructuredOutputError):
        _indexado(db, llm=llm).answer("Estorno?")


def test_sem_documentos_indexados_responde_sem_chamar_o_llm(db):
    llm = FakeLLMProvider([])  # roteiro vazio: qualquer chamada falharia

    resposta = _service(db, llm).answer("O que é rateio?")

    assert resposta.answer == SEM_INFORMACAO
    assert resposta.sources == []
    assert llm.chamadas == []


def test_answer_exige_llm(db):
    with pytest.raises(ValueError):
        _service(db).answer("pergunta")
