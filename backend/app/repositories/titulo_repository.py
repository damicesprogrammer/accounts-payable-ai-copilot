from collections.abc import Iterable, Sequence
from datetime import date

from sqlalchemy import select

from app.models import StatusTitulo, TituloPagar
from app.repositories.base import BaseRepository


class TituloRepository(BaseRepository[TituloPagar]):
    model = TituloPagar

    def get_for_update(self, titulo_id: int) -> TituloPagar | None:
        """Carrega o título com lock de linha (SELECT ... FOR UPDATE).

        Serializa operações concorrentes sobre o mesmo título — por exemplo, dois
        pagamentos simultâneos que, juntos, ultrapassariam o saldo.
        """
        stmt = (
            select(TituloPagar)
            .where(TituloPagar.id == titulo_id)
            .with_for_update(of=TituloPagar)
            .execution_options(populate_existing=True)
        )
        return self.db.scalar(stmt)

    def get_by_numero(self, fornecedor_id: int, numero: str) -> TituloPagar | None:
        stmt = select(TituloPagar).where(
            TituloPagar.fornecedor_id == fornecedor_id, TituloPagar.numero == numero
        )
        return self.db.scalar(stmt)

    def list(
        self,
        *,
        status: StatusTitulo | None = None,
        fornecedor_id: int | None = None,
        vencimento_antes_de: date | None = None,
        status_in: Iterable[StatusTitulo] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[TituloPagar]:
        stmt = select(TituloPagar).order_by(TituloPagar.data_vencimento, TituloPagar.id)
        if status is not None:
            stmt = stmt.where(TituloPagar.status == status)
        if status_in is not None:
            stmt = stmt.where(TituloPagar.status.in_(list(status_in)))
        if fornecedor_id is not None:
            stmt = stmt.where(TituloPagar.fornecedor_id == fornecedor_id)
        if vencimento_antes_de is not None:
            stmt = stmt.where(TituloPagar.data_vencimento < vencimento_antes_de)
        return self.db.scalars(stmt.limit(limit).offset(offset)).all()
