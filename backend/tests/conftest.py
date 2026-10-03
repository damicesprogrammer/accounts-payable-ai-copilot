"""Fixtures de teste.

Estratégia:
- Os testes usam um PostgreSQL real (banco ap_copilot_test), não SQLite, para que
  CHECKs, UNIQUEs e locks se comportem como em produção.
- O schema é criado pelas próprias migrations do Alembic: os testes também
  validam que as migrations funcionam.
- Cada teste roda dentro de uma transação externa que sofre rollback no final.
  Os commits feitos pelos services viram SAVEPOINTs (join_transaction_mode),
  então cada teste começa com o banco limpo sem precisar truncar tabelas.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = get_settings().test_database_url
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.attributes["database_url"] = url
    cfg.attributes["configure_logger"] = False
    command.upgrade(cfg, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
