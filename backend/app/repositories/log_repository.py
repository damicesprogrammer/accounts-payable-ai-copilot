from collections.abc import Sequence

from sqlalchemy import select

from app.models import LogAuditoria
from app.repositories.base import BaseRepository


class LogRepository(BaseRepository[LogAuditoria]):
    model = LogAuditoria

    def list_by_titulo(self, titulo_id: int) -> Sequence[LogAuditoria]:
        # Ordena por id: logs da mesma transação compartilham o mesmo now().
        stmt = (
            select(LogAuditoria)
            .where(LogAuditoria.titulo_id == titulo_id)
            .order_by(LogAuditoria.id)
        )
        return self.db.scalars(stmt).all()
