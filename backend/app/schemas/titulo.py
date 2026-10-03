from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.models import StatusTitulo
from app.schemas.common import InputSchema, ReadSchema, TextoObrigatorio, ValorPositivo


class _DadosTitulo(InputSchema):
    numero: Annotated[TextoObrigatorio, Field(max_length=50)]
    descricao: Annotated[TextoObrigatorio, Field(max_length=500)]
    data_emissao: date
    data_vencimento: date
    valor_total: ValorPositivo

    @model_validator(mode="after")
    def _vencimento_apos_emissao(self) -> Self:
        if self.data_vencimento < self.data_emissao:
            raise ValueError("data_vencimento não pode ser anterior a data_emissao")
        return self


class TituloCreate(_DadosTitulo):
    fornecedor_id: int


class TituloUpdate(_DadosTitulo):
    """Substitui os dados editáveis do título. O fornecedor e o status não mudam
    por aqui: status só muda pelas ações (aprovar, cancelar, reprocessar) e pelos
    pagamentos."""


class CancelamentoInput(InputSchema):
    motivo: Annotated[TextoObrigatorio, Field(max_length=500)]


class FornecedorResumo(ReadSchema):
    id: int
    nome: str


class TituloRead(ReadSchema):
    id: int
    numero: str
    fornecedor_id: int
    fornecedor: FornecedorResumo
    descricao: str
    data_emissao: date
    data_vencimento: date
    valor_total: Decimal
    status: StatusTitulo
    created_at: datetime
    updated_at: datetime


class TituloDetalhe(TituloRead):
    """Título com a situação financeira consolidada (valores calculados, não armazenados)."""

    valor_rateado: Decimal
    valor_pago: Decimal
    saldo_pendente: Decimal
    vencido: bool
