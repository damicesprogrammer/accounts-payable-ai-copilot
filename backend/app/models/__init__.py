"""Importa todos os models para registrá-los no metadata (usado pelo Alembic)."""

from app.models.cadastros import CentroCusto, Fornecedor
from app.models.enums import StatusLog, StatusPagamento, StatusTitulo, TipoLog
from app.models.titulos import LogIntegracao, Pagamento, RateioTitulo, TituloPagar

__all__ = [
    "CentroCusto",
    "Fornecedor",
    "LogIntegracao",
    "Pagamento",
    "RateioTitulo",
    "StatusLog",
    "StatusPagamento",
    "StatusTitulo",
    "TipoLog",
    "TituloPagar",
]
