from datetime import timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import StatusPagamento, StatusTitulo, TipoLog
from app.repositories.log_repository import LogRepository
from app.services.pagamento_service import PagamentoService
from app.services.titulo_service import TituloService
from tests.factories import criar_titulo, criar_titulo_aprovado, pagar, ratear

# ---------------------------------------------------------------- regra 2


def test_pagamento_parcial_mantem_titulo_aprovado(db):
    titulo = criar_titulo_aprovado(db, valor="1000.00")

    pagar(db, titulo, "400.00")

    assert titulo.status == StatusTitulo.APROVADO


def test_regra2_quitacao_exata_marca_titulo_como_pago_automaticamente(db):
    titulo = criar_titulo_aprovado(db, valor="1000.00")

    pagar(db, titulo, "400.00")
    pagar(db, titulo, "600.00")

    assert titulo.status == StatusTitulo.PAGO
    ultimos = LogRepository(db).list_by_titulo(titulo.id)[-2:]
    assert [log.tipo for log in ultimos] == [TipoLog.PAGAMENTO, TipoLog.MUDANCA_STATUS]
    assert "APROVADO para PAGO" in ultimos[-1].mensagem


def test_regra2_nao_e_possivel_marcar_pago_sem_quitacao(db):
    """Mesmo chamando a transição diretamente, a guarda central impede PAGO sem quitação."""
    titulo = criar_titulo_aprovado(db, valor="1000.00")
    pagar(db, titulo, "999.99")

    with pytest.raises(BusinessRuleError) as exc:
        TituloService(db).mudar_status(titulo, StatusTitulo.PAGO, "tentativa manual")

    assert exc.value.code == "PAGAMENTOS_NAO_QUITAM_TITULO"


def test_pagamento_acima_do_saldo_e_rejeitado(db):
    titulo = criar_titulo_aprovado(db, valor="1000.00")
    pagar(db, titulo, "900.00")

    with pytest.raises(BusinessRuleError) as exc:
        pagar(db, titulo, "100.01")

    assert exc.value.code == "PAGAMENTO_EXCEDE_SALDO"
    assert exc.value.details["saldo_pendente"] == "100.00"


def test_pagamento_estornado_nao_conta_para_quitacao(db):
    titulo = criar_titulo_aprovado(db, valor="1000.00")
    pagamento = pagar(db, titulo, "600.00")

    estornado = PagamentoService(db).estornar(titulo.id, pagamento.id)
    assert estornado.status == StatusPagamento.ESTORNADO

    pagar(db, titulo, "1000.00")  # o saldo voltou a ser o valor total
    assert titulo.status == StatusTitulo.PAGO


# ---------------------------------------------------------------- regra 5 e status


def test_regra5_titulo_cancelado_nao_recebe_pagamento(db):
    titulo = criar_titulo(db)
    TituloService(db).cancelar(titulo.id, "Cancelado pelo fornecedor")

    with pytest.raises(BusinessRuleError) as exc:
        pagar(db, titulo, "10.00")

    assert exc.value.code == "TITULO_CANCELADO"


@pytest.mark.parametrize("com_rateio_parcial", [False, True])
def test_pagamento_exige_titulo_aprovado(db, com_rateio_parcial):
    titulo = criar_titulo(db, valor="1000.00")
    if com_rateio_parcial:
        ratear(db, titulo, "500.00")

    with pytest.raises(BusinessRuleError) as exc:
        pagar(db, titulo, "10.00")

    assert exc.value.code == "TITULO_NAO_APROVADO"
    assert exc.value.details["status_atual"] == StatusTitulo.PENDENTE


def test_titulo_em_erro_nao_recebe_pagamento(db):
    titulo = criar_titulo_aprovado(db)
    TituloService(db).registrar_erro_integracao(titulo.id, "Timeout no ERP")

    with pytest.raises(BusinessRuleError) as exc:
        pagar(db, titulo, "10.00")

    assert exc.value.code == "TITULO_NAO_APROVADO"


def test_titulo_pago_nao_recebe_novo_pagamento(db):
    titulo = criar_titulo_aprovado(db, valor="100.00")
    pagar(db, titulo, "100.00")

    with pytest.raises(BusinessRuleError) as exc:
        pagar(db, titulo, "0.01")

    assert exc.value.code == "TITULO_JA_PAGO"


def test_titulo_com_pagamento_nao_pode_ser_cancelado(db):
    titulo = criar_titulo_aprovado(db, valor="1000.00")
    pagar(db, titulo, "100.00")

    with pytest.raises(BusinessRuleError) as exc:
        TituloService(db).cancelar(titulo.id, "motivo")

    assert exc.value.code == "TITULO_COM_PAGAMENTOS"


def test_data_pagamento_anterior_a_emissao(db):
    titulo = criar_titulo_aprovado(db)

    with pytest.raises(BusinessRuleError) as exc:
        pagar(db, titulo, "10.00", data=titulo.data_emissao - timedelta(days=1))

    assert exc.value.code == "DATA_PAGAMENTO_INVALIDA"


# ---------------------------------------------------------------- estorno


def test_nao_estorna_pagamento_de_titulo_pago(db):
    titulo = criar_titulo_aprovado(db, valor="100.00")
    pagamento = pagar(db, titulo, "100.00")

    with pytest.raises(BusinessRuleError) as exc:
        PagamentoService(db).estornar(titulo.id, pagamento.id)

    assert exc.value.code == "ESTORNO_NAO_PERMITIDO"


def test_nao_estorna_duas_vezes(db):
    titulo = criar_titulo_aprovado(db)
    pagamento = pagar(db, titulo, "10.00")
    service = PagamentoService(db)
    service.estornar(titulo.id, pagamento.id)

    with pytest.raises(BusinessRuleError) as exc:
        service.estornar(titulo.id, pagamento.id)

    assert exc.value.code == "PAGAMENTO_JA_ESTORNADO"


def test_estornar_pagamento_de_outro_titulo(db):
    pagamento = pagar(db, criar_titulo_aprovado(db), "10.00")
    outro = criar_titulo_aprovado(db)

    with pytest.raises(NotFoundError):
        PagamentoService(db).estornar(outro.id, pagamento.id)


def test_listar_pagamentos(db):
    titulo = criar_titulo_aprovado(db, valor="300.00")
    pagar(db, titulo, "100.00")
    pagar(db, titulo, "200.00")

    valores = [p.valor for p in PagamentoService(db).listar(titulo.id)]

    assert valores == [Decimal("100.00"), Decimal("200.00")]
