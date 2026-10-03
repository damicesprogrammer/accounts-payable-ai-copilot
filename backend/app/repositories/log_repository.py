from collections.abc import Sequence

from sqlalchemy import select

from app.models import LogIntegracao
from app.repositories.base import BaseRepository


class LogRepository(BaseRepository[LogIntegracao]):
    model = LogIntegracao

    def list_by_titulo(self, titulo_id: int) -> Sequence[LogIntegracao]:
        # Ordena por id: logs da mesma transação compartilham o mesmo now().
        stmt = (
            select(LogIntegracao)
            .where(LogIntegracao.titulo_id == titulo_id)
            .order_by(LogIntegracao.id)
        )
        return self.db.scalars(stmt).all()
