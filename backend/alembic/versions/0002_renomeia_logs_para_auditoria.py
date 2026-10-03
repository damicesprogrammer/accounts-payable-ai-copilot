"""renomeia logs_integracao para logs_auditoria

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-03

A tabela é a trilha geral de auditoria (criação, status, rateios, pagamentos,
cadastros e integração), não apenas de integração. Renomeia a tabela e também
sequence, constraints e índice, para que os nomes continuem seguindo a
convenção do projeto (verificado com `alembic check`). Não há perda de dados.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINTS = [
    "pk_{t}",
    "fk_{t}_titulo_id_titulos_pagar",
    "ck_{t}_tipo_log",
    "ck_{t}_status_log",
]


def _renomear(origem: str, destino: str) -> None:
    op.rename_table(origem, destino)
    op.execute(f"ALTER SEQUENCE {origem}_id_seq RENAME TO {destino}_id_seq")
    for nome in CONSTRAINTS:
        op.execute(
            f"ALTER TABLE {destino} RENAME CONSTRAINT "
            f"{nome.format(t=origem)} TO {nome.format(t=destino)}"
        )
    op.execute(f"ALTER INDEX ix_{origem}_titulo_id RENAME TO ix_{destino}_titulo_id")


def upgrade() -> None:
    _renomear("logs_integracao", "logs_auditoria")


def downgrade() -> None:
    _renomear("logs_auditoria", "logs_integracao")
