from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import StatusLog, StatusTitulo, TipoLog
from app.repositories.log_repository import LogRepository
from app.schemas.titulo import TituloCreate, TituloUpdate
from app.services.titulo_service import TituloService
from tests.factories import criar_fornecedor, criar_titulo, criar_titulo_aprovado, pagar

HOJE = date(2026, 10, 3)


def _dados_titulo(fornecedor_id: int, **overrides) -> dict:
    dados = {
        "numero": "NF-100",
        "fornecedor_id": fornecedor_id,
        "descricao": "Serviço de manutenção",
        "data_emissao": HOJE,
        "data_vencimento": HOJE + timedelta(days=30),
        "valor_total": Decimal("1500.00"),
    }
    return {**dados, **overrides}


def _tipos_log(db, titulo_id: int) -> list[TipoLog]:
    return [log.tipo for log in LogRepository(db).list_by_titulo(titulo_id)]


# ---------------------------------------------------------------- criação


def test_titulo_criado_como_pendente_e_gera_log(db):
    fornecedor = criar_fornecedor(db)

    titulo = TituloService(db).criar(TituloCreate(**_dados_titulo(fornecedor.id)))

    assert titulo.status == StatusTitulo.PENDENTE
    assert _tipos_log(db, titulo.id) == [TipoLog.CRIACAO]


def test_regra3_fornecedor_inativo_nao_recebe_titulo(db):
    fornecedor = criar_fornecedor(db, ativo=False)

    with pytest.raises(BusinessRuleError) as exc:
        TituloService(db).criar(TituloCreate(**_dados_titulo(fornecedor.id)))

    assert exc.value.code == "FORNECEDOR_INATIVO"


def test_fornecedor_inexistente(db):
    with pytest.raises(NotFoundError):
        TituloService(db).criar(TituloCreate(**_dados_titulo(999_999)))


def test_numero_duplicado_para_o_mesmo_fornecedor(db):
    fornecedor = criar_fornecedor(db)
    criar_titulo(db, fornecedor=fornecedor, numero="NF-1")

    with pytest.raises(ConflictError):
        criar_titulo(db, fornecedor=fornecedor, numero="NF-1")


def test_mesmo_numero_em_fornecedores_diferentes_e_permitido(db):
    criar_titulo(db, numero="NF-1")
    criar_titulo(db, numero="NF-1")


@pytest.mark.parametrize("valor", ["0", "-10.00"])
def test_regra6_valor_total_nao_pode_ser_zero_ou_negativo(valor):
    with pytest.raises(ValidationError):
        TituloCreate(**_dados_titulo(1, valor_total=Decimal(valor)))


def test_regra6_banco_tambem_rejeita_valor_negativo(db):
    """Defesa em profundidade: mesmo contornando a aplicação, o CHECK do banco barra."""
    titulo = criar_titulo(db)

    with pytest.raises(IntegrityError):
        db.execute(
            text("UPDATE titulos_pagar SET valor_total = -1 WHERE id = :id"), {"id": titulo.id}
        )


def test_vencimento_anterior_a_emissao_e_rejeitado():
    with pytest.raises(ValidationError):
        TituloCreate(**_dados_titulo(1, data_vencimento=HOJE - timedelta(days=1)))


# ---------------------------------------------------------------- atualização


def test_atualizar_titulo_pendente_registra_campos_alterados(db):
    titulo = criar_titulo(db, valor="100.00")
    dados = TituloUpdate(
        numero=titulo.numero,
        descricao=titulo.descricao,
        data_emissao=titulo.data_emissao,
        data_vencimento=titulo.data_vencimento,
        valor_total=Decimal("150.00"),
    )

    atualizado = TituloService(db).atualizar(titulo.id, dados)

    assert atualizado.valor_total == Decimal("150.00")
    ultimo_log = LogRepository(db).list_by_titulo(titulo.id)[-1]
    assert ultimo_log.tipo == TipoLog.ATUALIZACAO
    assert "valor_total: 100.00 -> 150.00" in ultimo_log.mensagem


def test_titulo_cancelado_nao_pode_ser_editado(db):
    titulo = criar_titulo(db)
    service = TituloService(db)
    service.cancelar(titulo.id, "Lançado em duplicidade")

    with pytest.raises(BusinessRuleError) as exc:
        service.atualizar(
            titulo.id,
            TituloUpdate(
                numero=titulo.numero,
                descricao="nova",
                data_emissao=titulo.data_emissao,
                data_vencimento=titulo.data_vencimento,
                valor_total=titulo.valor_total,
            ),
        )

    assert exc.value.code == "TITULO_NAO_EDITAVEL"


# ---------------------------------------------------------------- status


def test_cancelar_titulo_gera_log_com_motivo(db):
    titulo = criar_titulo(db)

    cancelado = TituloService(db).cancelar(titulo.id, "Lançado em duplicidade")

    assert cancelado.status == StatusTitulo.CANCELADO
    ultimo_log = LogRepository(db).list_by_titulo(titulo.id)[-1]
    assert ultimo_log.tipo == TipoLog.MUDANCA_STATUS
    assert "Lançado em duplicidade" in ultimo_log.mensagem


def test_cancelado_e_estado_final(db):
    titulo = criar_titulo(db)
    service = TituloService(db)
    service.cancelar(titulo.id, "motivo")

    with pytest.raises(BusinessRuleError) as exc:
        service.cancelar(titulo.id, "de novo")

    assert exc.value.code == "TRANSICAO_STATUS_INVALIDA"


def test_erro_de_integracao_e_reprocessamento(db):
    titulo = criar_titulo(db)
    service = TituloService(db)

    service.registrar_erro_integracao(titulo.id, "Centro de custo 1001 inexistente no ERP")
    assert titulo.status == StatusTitulo.ERRO
    log_integracao = LogRepository(db).list_by_titulo(titulo.id)[-1]
    assert log_integracao.tipo == TipoLog.INTEGRACAO
    assert log_integracao.status == StatusLog.ERRO

    service.reprocessar(titulo.id)
    assert titulo.status == StatusTitulo.PENDENTE


def test_reprocessar_so_e_permitido_a_partir_de_erro(db):
    titulo = criar_titulo(db)

    with pytest.raises(BusinessRuleError):
        TituloService(db).reprocessar(titulo.id)


# ---------------------------------------------------------------- consultas


def test_listar_vencidos_considera_apenas_titulos_em_aberto(db):
    passado = HOJE - timedelta(days=40)
    vencido = criar_titulo(db, emissao=passado, vencimento=HOJE - timedelta(days=1))
    cancelado = criar_titulo(db, emissao=passado, vencimento=HOJE - timedelta(days=1))
    TituloService(db).cancelar(cancelado.id, "motivo")
    criar_titulo(db, emissao=HOJE, vencimento=HOJE)  # vence hoje: ainda não vencido

    vencidos = TituloService(db).listar(vencidos=True, hoje=HOJE)

    assert [t.id for t in vencidos] == [vencido.id]


# ---------------------------------------------------------------- detalhe financeiro


def test_detalhe_consolida_rateio_pagamentos_e_vencimento(db):
    titulo = criar_titulo_aprovado(
        db,
        valor="1000.00",
        emissao=HOJE - timedelta(days=60),
        vencimento=HOJE - timedelta(days=5),
    )
    pagar(db, titulo, "300.00")

    detalhe = TituloService(db).obter_detalhe(titulo.id, hoje=HOJE)

    assert detalhe.valor_rateado == Decimal("1000.00")
    assert detalhe.valor_pago == Decimal("300.00")
    assert detalhe.saldo_pendente == Decimal("700.00")
    assert detalhe.vencido is True


def test_titulo_pago_nao_e_considerado_vencido(db):
    titulo = criar_titulo_aprovado(
        db, valor="100.00", emissao=HOJE - timedelta(days=60), vencimento=HOJE - timedelta(days=5)
    )
    pagar(db, titulo, "100.00")

    detalhe = TituloService(db).obter_detalhe(titulo.id, hoje=HOJE)

    assert detalhe.vencido is False
    assert detalhe.saldo_pendente == Decimal("0.00")
