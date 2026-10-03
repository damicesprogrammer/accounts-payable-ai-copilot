from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Pagamento, StatusPagamento
from app.models.types import CENTAVOS
from app.repositories.base import BaseRepository


class PagamentoRepository(BaseRepository[Pagamento]):
    model = Pagamento

    def list_by_titulo(self, titulo_id: int) -> Sequence[Pagamento]:
        stmt = select(Pagamento).where(Pagamento.titulo_id == titulo_id).order_by(Pagamento.id)
        return self.db.scalars(stmt).all()

    def soma_confirmados(self, titulo_id: int) -> Decimal:
        """Somente pagamentos CONFIRMADOS contam para a quitação."""
        stmt = select(func.coalesce(func.sum(Pagamento.valor), 0)).where(
            Pagamento.titulo_id == titulo_id,
            Pagamento.status == StatusPagamento.CONFIRMADO,
        )
        return Decimal(self.db.scalar(stmt)).quantize(CENTAVOS)
