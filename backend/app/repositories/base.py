from sqlalchemy.orm import Session

from app.core.db import Base


class BaseRepository[M: Base]:
    """Operações comuns de acesso a dados. Repositories não contêm regra de negócio
    e não fazem commit — a transação pertence ao service."""

    model: type[M]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, id_: int) -> M | None:
        return self.db.get(self.model, id_)

    def add(self, obj: M) -> M:
        self.db.add(obj)
        self.db.flush()  # gera o id sem encerrar a transação
        return obj
