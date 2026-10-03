from collections.abc import Sequence

from sqlalchemy import select

from app.models import CentroCusto
from app.repositories.base import BaseRepository


class CentroCustoRepository(BaseRepository[CentroCusto]):
    model = CentroCusto

    def get_by_codigo(self, codigo: str) -> CentroCusto | None:
        return self.db.scalar(select(CentroCusto).where(CentroCusto.codigo == codigo))

    def list(
        self, *, ativo: bool | None = None, limit: int = 50, offset: int = 0
    ) -> Sequence[CentroCusto]:
        stmt = select(CentroCusto).order_by(CentroCusto.codigo).limit(limit).offset(offset)
        if ativo is not None:
            stmt = stmt.where(CentroCusto.ativo == ativo)
        return self.db.scalars(stmt).all()
