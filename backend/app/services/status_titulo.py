"""Máquina de estados do título a pagar.

    PENDENTE ──aprovar──► APROVADO ──(pagamentos = valor_total)──► PAGO
       │  ▲                  │
       │  └──reprocessar── ERRO ◄── falha de integração
       └──────cancelar───────┴──► CANCELADO

PAGO e CANCELADO são estados finais.
"""

from app.core.exceptions import BusinessRuleError
from app.models import StatusTitulo

TRANSICOES: dict[StatusTitulo, frozenset[StatusTitulo]] = {
    StatusTitulo.PENDENTE: frozenset(
        {StatusTitulo.APROVADO, StatusTitulo.CANCELADO, StatusTitulo.ERRO}
    ),
    StatusTitulo.APROVADO: frozenset(
        {StatusTitulo.PAGO, StatusTitulo.CANCELADO, StatusTitulo.ERRO}
    ),
    StatusTitulo.ERRO: frozenset({StatusTitulo.PENDENTE, StatusTitulo.CANCELADO}),
    StatusTitulo.PAGO: frozenset(),
    StatusTitulo.CANCELADO: frozenset(),
}

# Títulos cujos dados (valor, datas, rateios) ainda podem ser alterados.
# Depois de aprovado, o título está "congelado" para pagamento.
EDITAVEIS = frozenset({StatusTitulo.PENDENTE, StatusTitulo.ERRO})

# Títulos que ainda representam uma obrigação a pagar (usados para "vencidos").
EM_ABERTO = frozenset({StatusTitulo.PENDENTE, StatusTitulo.APROVADO, StatusTitulo.ERRO})


def validar_transicao(titulo_id: int, atual: StatusTitulo, novo: StatusTitulo) -> None:
    if novo not in TRANSICOES[atual]:
        raise BusinessRuleError(
            f"Título {titulo_id} não pode passar de {atual} para {novo}.",
            code="TRANSICAO_STATUS_INVALIDA",
            titulo_id=titulo_id,
            status_atual=atual,
            status_destino=novo,
        )


def validar_editavel(titulo_id: int, atual: StatusTitulo) -> None:
    if atual not in EDITAVEIS:
        raise BusinessRuleError(
            f"Título {titulo_id} está {atual} e não pode ser alterado "
            f"(permitido apenas em {', '.join(sorted(EDITAVEIS))}).",
            code="TITULO_NAO_EDITAVEL",
            titulo_id=titulo_id,
            status_atual=atual,
        )
