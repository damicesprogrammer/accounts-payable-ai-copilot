from collections.abc import Sequence

from sqlalchemy import Row, delete, select

from app.models import ChunkDocumentacao
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[ChunkDocumentacao]):
    model = ChunkDocumentacao

    def substituir_todos(self, chunks: list[ChunkDocumentacao]) -> None:
        """Apaga o índice atual e grava o novo. Sem commit: a transação é do service."""
        self.db.execute(delete(ChunkDocumentacao))
        self.db.add_all(chunks)
        self.db.flush()

    def mais_proximos(
        self, embedding: list[float], limit: int
    ) -> Sequence[Row[tuple[str, str, str, float]]]:
        """Top-N por distância de cosseno (`<=>` do pgvector), calculada no PostgreSQL.

        Só os campos de texto e a distância voltam para o Python — os vetores não.
        """
        distancia = ChunkDocumentacao.embedding.cosine_distance(embedding).label("distancia")
        stmt = (
            select(
                ChunkDocumentacao.source,
                ChunkDocumentacao.section,
                ChunkDocumentacao.content,
                distancia,
            )
            .order_by(distancia, ChunkDocumentacao.id)
            .limit(limit)
        )
        return self.db.execute(stmt).all()
