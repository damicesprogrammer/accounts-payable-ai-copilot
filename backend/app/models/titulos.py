from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.cadastros import CentroCusto, Fornecedor
from app.models.enums import StatusLog, StatusPagamento, StatusTitulo, TipoLog
from app.models.types import Money, enum_column


class TituloPagar(Base):
    __tablename__ = "titulos_pagar"
    __table_args__ = (
        UniqueConstraint("fornecedor_id", "numero", name="uq_titulos_pagar_fornecedor_numero"),
        CheckConstraint("valor_total > 0", name="valor_total_positivo"),
        CheckConstraint("data_vencimento >= data_emissao", name="vencimento_apos_emissao"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(50))
    fornecedor_id: Mapped[int] = mapped_column(ForeignKey("fornecedores.id"), index=True)
    descricao: Mapped[str] = mapped_column(String(500))
    data_emissao: Mapped[date] = mapped_column(Date)
    data_vencimento: Mapped[date] = mapped_column(Date, index=True)
    valor_total: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[StatusTitulo] = mapped_column(
        enum_column(StatusTitulo, "status_titulo"),
        default=StatusTitulo.PENDENTE,
        server_default=StatusTitulo.PENDENTE.value,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fornecedor: Mapped[Fornecedor] = relationship(lazy="joined")


class RateioTitulo(Base):
    __tablename__ = "rateios_titulo"
    __table_args__ = (
        UniqueConstraint("titulo_id", "centro_custo_id", name="uq_rateios_titulo_titulo_centro"),
        CheckConstraint("valor > 0", name="valor_positivo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo_id: Mapped[int] = mapped_column(
        ForeignKey("titulos_pagar.id", ondelete="CASCADE"), index=True
    )
    centro_custo_id: Mapped[int] = mapped_column(ForeignKey("centros_custo.id"))
    valor: Mapped[Decimal] = mapped_column(Money)

    centro_custo: Mapped[CentroCusto] = relationship(lazy="joined")


class Pagamento(Base):
    __tablename__ = "pagamentos"
    __table_args__ = (CheckConstraint("valor > 0", name="valor_positivo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo_id: Mapped[int] = mapped_column(
        ForeignKey("titulos_pagar.id", ondelete="CASCADE"), index=True
    )
    data_pagamento: Mapped[date] = mapped_column(Date)
    valor: Mapped[Decimal] = mapped_column(Money)
    status: Mapped[StatusPagamento] = mapped_column(
        enum_column(StatusPagamento, "status_pagamento"),
        default=StatusPagamento.CONFIRMADO,
        server_default=StatusPagamento.CONFIRMADO.value,
    )


class LogIntegracao(Base):
    """Trilha de auditoria de negócio. titulo_id é nulo para eventos de cadastro."""

    __tablename__ = "logs_integracao"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo_id: Mapped[int | None] = mapped_column(
        ForeignKey("titulos_pagar.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[TipoLog] = mapped_column(enum_column(TipoLog, "tipo_log"))
    status: Mapped[StatusLog] = mapped_column(enum_column(StatusLog, "status_log"))
    mensagem: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
