"""Garantias de segurança da camada de tools (regras 8, 9 e 10).

- O LLM só executa tools da allowlist explícita.
- Não existe tool de SQL nem tool de escrita nesta fase.
- search_documentation só lê chunks; não chama o LLM nem altera o banco.
- Argumentos são validados antes de qualquer execução.
- Nenhuma tool altera dados.
"""

import ast
from pathlib import Path

import pytest
from sqlalchemy import event, func, select

from app.ai.contracts import ToolCall
from app.ai.providers.fake import FakeEmbeddingProvider
from app.models import (
    CentroCusto,
    ChunkDocumentacao,
    Fornecedor,
    LogAuditoria,
    Pagamento,
    RateioTitulo,
    TituloPagar,
)
from app.rag.chunking import Chunk
from app.rag.service import RAGService
from app.tools.registry import criar_registry_financeiro
from tests.factories import criar_titulo, criar_titulo_aprovado, pagar, ratear

APP_DIR = Path(__file__).resolve().parents[2] / "app"

ALLOWLIST = {
    "get_titulo",
    "get_rateios_titulo",
    "get_pagamentos_titulo",
    "get_logs_titulo",
    "get_titulos_vencidos",
    "search_documentation",
}


@pytest.fixture
def registry():
    return criar_registry_financeiro(FakeEmbeddingProvider())


def _call(name: str, **arguments) -> ToolCall:
    return ToolCall(id="call_1", name=name, arguments=arguments)


def _snapshot(db) -> dict:
    """Contagem de linhas por tabela + estado de cada título."""
    contagens = {
        model.__tablename__: db.scalar(select(func.count()).select_from(model))
        for model in (
            Fornecedor,
            CentroCusto,
            TituloPagar,
            RateioTitulo,
            Pagamento,
            LogAuditoria,
            ChunkDocumentacao,
        )
    }
    titulos = db.execute(
        select(TituloPagar.id, TituloPagar.status, TituloPagar.updated_at).order_by(TituloPagar.id)
    ).all()
    return {"contagens": contagens, "titulos": titulos}


# ---------------------------------------------------------------- allowlist


def test_registry_contem_exatamente_a_allowlist(registry):
    assert set(registry.names) == ALLOWLIST


def test_nao_existe_tool_de_sql_nem_de_escrita(registry):
    proibidos = ("sql", "delete", "update", "create", "insert", "cancel", "aprovar", "estornar")
    for nome in registry.names:
        assert nome.startswith(("get_", "search_"))  # verbos de leitura
        assert not any(p in nome.lower() for p in proibidos)


@pytest.mark.parametrize(
    "nome",
    ["executar_sql", "delete_titulo", "update_titulo", "create_pagamento", "__import__", "eval"],
)
def test_tools_fora_da_allowlist_sao_recusadas(registry, db, nome):
    antes = _snapshot(db)

    resultado = registry.execute(_call(nome, sql="DELETE FROM titulos_pagar"), db)

    assert resultado.error.code == "TOOL_NAO_PERMITIDA"
    assert _snapshot(db) == antes


@pytest.mark.parametrize(
    "arguments",
    [
        {"titulo_id": "1; DROP TABLE titulos_pagar"},
        {"titulo_id": "1 OR 1=1"},
        {"titulo_id": 1, "sql": "DELETE FROM titulos_pagar"},
        {"titulo_id": -1},
    ],
)
def test_argumentos_maliciosos_sao_recusados_antes_da_execucao(registry, db, arguments):
    criar_titulo(db)
    antes = _snapshot(db)

    resultado = registry.execute(ToolCall(id="c", name="get_titulo", arguments=arguments), db)

    assert resultado.error.code == "ARGUMENTOS_INVALIDOS"
    assert _snapshot(db) == antes


# ---------------------------------------------------------------- somente leitura


def test_nenhuma_tool_altera_dados(registry, db):
    titulo = criar_titulo_aprovado(db, valor="500.00")
    pagar(db, titulo, "100.00")
    ratear(db, criar_titulo(db, valor="80.00"), "40.00")
    RAGService(db, FakeEmbeddingProvider()).indexar([Chunk("a.md", "Estorno", "Estorno de PAGO.")])
    antes = _snapshot(db)

    escritas = []

    def registrar_flush(session, flush_context):
        escritas.append(True)

    event.listen(db, "after_flush", registrar_flush)
    try:
        for nome in registry.names:
            args = {
                "get_titulos_vencidos": {},
                "search_documentation": {"query": "estorno"},
            }.get(nome, {"titulo_id": titulo.id})
            assert registry.execute(_call(nome, **args), db).ok is True
    finally:
        event.remove(db, "after_flush", registrar_flush)

    assert escritas == []  # nenhum INSERT/UPDATE/DELETE chegou ao banco
    assert not (db.new or db.dirty or db.deleted)
    assert _snapshot(db) == antes


def test_tools_nao_acessam_repositories_sql_nem_commit():
    """As tools só podem falar com services."""
    for modulo in ("titulo_tools.py", "documentacao_tools.py"):
        fonte = (APP_DIR / "tools" / modulo).read_text(encoding="utf-8")
        for proibido in ("app.repositories", "sqlalchemy import text", ".execute(", ".commit("):
            assert proibido not in fonte, f"{modulo}: {proibido}"


def test_camada_de_ia_nao_usa_eval_exec_nem_import_dinamico():
    proibidos = {"eval", "exec", "__import__", "import_module", "getattr"}
    pastas = ("ai", "tools", "rag", "agent")
    for arquivo in [f for pasta in pastas for f in (APP_DIR / pasta).rglob("*.py")]:
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        chamados = {
            no.func.id if isinstance(no.func, ast.Name) else getattr(no.func, "attr", "")
            for no in ast.walk(arvore)
            if isinstance(no, ast.Call)
        }
        assert not (chamados & proibidos), f"{arquivo.name}: {chamados & proibidos}"


@pytest.mark.parametrize(
    "query",
    ["'; DROP TABLE chunks_documentacao; --", "1 OR 1=1", "SELECT * FROM titulos_pagar"],
)
def test_search_documentation_trata_sql_como_texto_de_busca(registry, db, query):
    """A query só vira embedding: nunca é interpolada em SQL."""
    RAGService(db, FakeEmbeddingProvider()).indexar([Chunk("a.md", "Estorno", "Estorno de PAGO.")])
    antes = _snapshot(db)

    resultado = registry.execute(_call("search_documentation", query=query), db)

    assert resultado.ok is True
    assert [t["source"] for t in resultado.data] == ["a.md"]
    assert _snapshot(db) == antes


@pytest.mark.parametrize(
    "arguments",
    [{}, {"query": ""}, {"query": "x" * 501}, {"query": "estorno", "sql": "DELETE FROM x"}],
)
def test_search_documentation_valida_argumentos(registry, db, arguments):
    resultado = registry.execute(
        ToolCall(id="c", name="search_documentation", arguments=arguments), db
    )

    assert resultado.error.code == "ARGUMENTOS_INVALIDOS"
