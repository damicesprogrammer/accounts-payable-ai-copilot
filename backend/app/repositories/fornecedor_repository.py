from collections.abc import Sequence

from sqlalchemy import select

from app.models import Fornecedor
from app.repositories.base import BaseRepository


class FornecedorRepository(BaseRepository[Fornecedor]):
    model = Fornecedor

    def get_by_cnpj(self, cnpj: str) -> Fornecedor | None:
        return self.db.scalar(select(Fornecedor).where(Fornecedor.cnpj == cnpj))

    def list(
        self, *, ativo: bool | None = None, limit: int | None = 50, offset: int = 0
    ) -> Sequence[Fornecedor]:
        stmt = select(Fornecedor).order_by(Fornecedor.nome).limit(limit).offset(offset)
        if ativo is not None:
            stmt = stmt.where(Fornecedor.ativo == ativo)
        return self.db.scalars(stmt).all()
