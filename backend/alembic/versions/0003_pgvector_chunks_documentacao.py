"""ativa pgvector e cria chunks_documentacao

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03

Base de conhecimento do RAG: um registro por seção de documento Markdown,
com o embedding em uma coluna `vector`. Sem índice vetorial (HNSW/IVFFlat):
com poucas dezenas de linhas a busca exata por varredura é instantânea.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "chunks_documentacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("section", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chunks_documentacao")),
    )


def downgrade() -> None:
    op.drop_table("chunks_documentacao")
    op.execute("DROP EXTENSION IF EXISTS vector")
