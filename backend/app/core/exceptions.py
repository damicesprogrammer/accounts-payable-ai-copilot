"""Exceções de domínio.

Os services lançam estas exceções sem saber nada de HTTP. A tradução para status
code acontece em um único lugar (core/error_handlers.py). Cada erro carrega um
`code` estável e legível por máquina — útil para clientes da API e, futuramente,
para o Copilot explicar por que uma operação foi recusada.
"""

from typing import Any


class DomainError(Exception):
    code: str = "ERRO_DOMINIO"

    def __init__(self, message: str, *, code: str | None = None, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class NotFoundError(DomainError):
    code = "NAO_ENCONTRADO"


class ConflictError(DomainError):
    """Violação de unicidade (ex.: CNPJ já cadastrado)."""

    code = "CONFLITO"


class BusinessRuleError(DomainError):
    """Operação válida no formato, mas proibida por uma regra de negócio."""

    code = "REGRA_DE_NEGOCIO"
