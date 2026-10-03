from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Dimensão fixa da coluna. O provider OpenAI pede vetores com esta dimensão
# (parâmetro `dimensions`), então trocar o modelo text-embedding-3-* não quebra o schema.
EMBEDDING_DIM = 1536


class ChunkDocumentacao(Base):
    """Trecho de um documento da base de conhecimento, com seu embedding.

    Sem tabela de documentos nem versionamento: a indexação apaga e recria tudo.
    """

    __tablename__ = "chunks_documentacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(200))  # nome do arquivo Markdown
    section: Mapped[str] = mapped_column(String(200))  # heading da seção
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
