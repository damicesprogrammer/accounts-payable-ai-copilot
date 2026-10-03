from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Numeric

# Dinheiro sempre como NUMERIC(14,2) <-> Decimal. Nunca float.
CENTAVOS = Decimal("0.01")
Money = Numeric(14, 2, asdecimal=True)


def enum_column(enum_cls: type[StrEnum], name: str) -> SAEnum:
    """Enum persistido como VARCHAR + CHECK (não como ENUM nativo do Postgres).

    Enums nativos exigem ALTER TYPE para adicionar valores; VARCHAR com CHECK
    é mais simples de evoluir via migration.
    """
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda cls: [m.value for m in cls],
        validate_strings=True,
    )
