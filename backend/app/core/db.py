from collections.abc import Iterator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Convenção de nomes explícita: constraints com nomes previsíveis facilitam
# migrations e tornam mensagens de erro do Postgres legíveis.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Busca valores gerados pelo banco (created_at, updated_at...) via RETURNING
    # no próprio INSERT/UPDATE, para que os objetos fiquem completos após o commit.
    __mapper_args__ = {"eager_defaults": True}


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependency do FastAPI: uma sessão por requisição.

    A sessão não faz commit aqui: quem define a fronteira da transação são os
    services, que conhecem a operação de negócio completa.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
