"""schema inicial: cadastros, títulos, rateios, pagamentos e logs

Revision ID: 0001
Revises:
Create Date: 2026-10-03

Escrita à mão (e conferida com `alembic check`) para que as constraints de
negócio fiquem explícitas e revisáveis.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUS_TITULO = ("PENDENTE", "APROVADO", "PAGO", "CANCELADO", "ERRO")
STATUS_PAGAMENTO = ("CONFIRMADO", "ESTORNADO")
TIPO_LOG = (
    "CRIACAO",
    "ATUALIZACAO",
    "MUDANCA_STATUS",
    "RATEIO",
    "PAGAMENTO",
    "INTEGRACAO",
    "CADASTRO",
)
STATUS_LOG = ("SUCESSO", "ERRO", "INFO")


def _enum(values: tuple[str, ...], name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=20)


def upgrade() -> None:
    op.create_table(
        "fornecedores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("cnpj", sa.String(14), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("cnpj", name="uq_fornecedores_cnpj"),
    )

    op.create_table(
        "centros_custo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(20), nullable=False),
        sa.Column("descricao", sa.String(200), nullable=False),
        sa.Column("ativo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("codigo", name="uq_centros_custo_codigo"),
    )

    op.create_table(
        "titulos_pagar",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("numero", sa.String(50), nullable=False),
        sa.Column(
            "fornecedor_id",
            sa.Integer(),
            sa.ForeignKey("fornecedores.id", name="fk_titulos_pagar_fornecedor_id_fornecedores"),
            nullable=False,
        ),
        sa.Column("descricao", sa.String(500), nullable=False),
        sa.Column("data_emissao", sa.Date(), nullable=False),
        sa.Column("data_vencimento", sa.Date(), nullable=False),
        sa.Column("valor_total", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "status",
            _enum(STATUS_TITULO, "status_titulo"),
            server_default="PENDENTE",
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("fornecedor_id", "numero", name="uq_titulos_pagar_fornecedor_numero"),
        sa.CheckConstraint("valor_total > 0", name="valor_total_positivo"),
        sa.CheckConstraint("data_vencimento >= data_emissao", name="vencimento_apos_emissao"),
    )
    op.create_index("ix_titulos_pagar_fornecedor_id", "titulos_pagar", ["fornecedor_id"])
    op.create_index("ix_titulos_pagar_data_vencimento", "titulos_pagar", ["data_vencimento"])
    op.create_index("ix_titulos_pagar_status", "titulos_pagar", ["status"])

    op.create_table(
        "rateios_titulo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "titulo_id",
            sa.Integer(),
            sa.ForeignKey(
                "titulos_pagar.id",
                name="fk_rateios_titulo_titulo_id_titulos_pagar",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "centro_custo_id",
            sa.Integer(),
            sa.ForeignKey(
                "centros_custo.id", name="fk_rateios_titulo_centro_custo_id_centros_custo"
            ),
            nullable=False,
        ),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.UniqueConstraint("titulo_id", "centro_custo_id", name="uq_rateios_titulo_titulo_centro"),
        sa.CheckConstraint("valor > 0", name="valor_positivo"),
    )
    op.create_index("ix_rateios_titulo_titulo_id", "rateios_titulo", ["titulo_id"])

    op.create_table(
        "pagamentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "titulo_id",
            sa.Integer(),
            sa.ForeignKey(
                "titulos_pagar.id", name="fk_pagamentos_titulo_id_titulos_pagar", ondelete="CASCADE"
            ),
            nullable=False,
        ),
        sa.Column("data_pagamento", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(14, 2), nullable=False),
        sa.Column(
            "status",
            _enum(STATUS_PAGAMENTO, "status_pagamento"),
            server_default="CONFIRMADO",
            nullable=False,
        ),
        sa.CheckConstraint("valor > 0", name="valor_positivo"),
    )
    op.create_index("ix_pagamentos_titulo_id", "pagamentos", ["titulo_id"])

    op.create_table(
        "logs_integracao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "titulo_id",
            sa.Integer(),
            sa.ForeignKey(
                "titulos_pagar.id",
                name="fk_logs_integracao_titulo_id_titulos_pagar",
                ondelete="CASCADE",
            ),
            nullable=True,
        ),
        sa.Column("tipo", _enum(TIPO_LOG, "tipo_log"), nullable=False),
        sa.Column("status", _enum(STATUS_LOG, "status_log"), nullable=False),
        sa.Column("mensagem", sa.String(1000), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_logs_integracao_titulo_id", "logs_integracao", ["titulo_id"])


def downgrade() -> None:
    op.drop_table("logs_integracao")
    op.drop_table("pagamentos")
    op.drop_table("rateios_titulo")
    op.drop_table("titulos_pagar")
    op.drop_table("centros_custo")
    op.drop_table("fornecedores")
