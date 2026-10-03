from enum import StrEnum


class StatusTitulo(StrEnum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    PAGO = "PAGO"
    CANCELADO = "CANCELADO"
    ERRO = "ERRO"


class StatusPagamento(StrEnum):
    CONFIRMADO = "CONFIRMADO"
    ESTORNADO = "ESTORNADO"


class TipoLog(StrEnum):
    CRIACAO = "CRIACAO"
    ATUALIZACAO = "ATUALIZACAO"
    MUDANCA_STATUS = "MUDANCA_STATUS"
    RATEIO = "RATEIO"
    PAGAMENTO = "PAGAMENTO"
    INTEGRACAO = "INTEGRACAO"
    CADASTRO = "CADASTRO"


class StatusLog(StrEnum):
    SUCESSO = "SUCESSO"
    ERRO = "ERRO"
    INFO = "INFO"
