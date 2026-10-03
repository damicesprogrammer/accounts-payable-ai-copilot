from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select

from app.models import RateioTitulo
from app.repositories.base import BaseRepository


class RateioRepository(BaseRepository[RateioTitulo]):
    model = RateioTitulo

    def list_by_titulo(self, titulo_id: int) -> Sequence[RateioTitulo]:
        stmt = (
            select(RateioTitulo)
            .where(RateioTitulo.titulo_id == titulo_id)
            .order_by(RateioTitulo.id)
        )
        return self.db.scalars(stmt).all()

    def get_by_titulo_e_centro(self, titulo_id: int, centro_custo_id: int) -> RateioTitulo | None:
        stmt = select(RateioTitulo).where(
            RateioTitulo.titulo_id == titulo_id, RateioTitulo.centro_custo_id == centro_custo_id
        )
        return self.db.scalar(stmt)

    def soma_por_titulo(self, titulo_id: int) -> Decimal:
        stmt = select(func.coalesce(func.sum(RateioTitulo.valor), 0)).where(
            RateioTitulo.titulo_id == titulo_id
        )
        return Decimal(self.db.scalar(stmt))

    def delete(self, rateio: RateioTitulo) -> None:
        self.db.delete(rateio)
        self.db.flush()
