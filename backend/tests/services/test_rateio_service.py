from decimal import Decimal

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import StatusTitulo, TipoLog
from app.repositories.log_repository import LogRepository
from app.schemas.rateio import RateioCreate
from app.schemas.titulo import TituloUpdate
from app.services.rateio_service import RateioService
from app.services.titulo_service import TituloService
from tests.factories import (
    criar_centro_custo,
    criar_titulo,
    criar_titulo_aprovado,
    ratear,
)

# ---------------------------------------------------------------- regra 1


def test_rateio_parcial_e_permitido(db):
    titulo = criar_titulo(db, valor="1000.00")

    ratear(db, titulo, "400.00")
    ratear(db, titulo, "600.00")

    assert len(RateioService(db).listar(titulo.id)) == 2


def test_regra1_rateio_nao_pode_ultrapassar_valor_do_titulo(db):
    titulo = criar_titulo(db, valor="1000.00")
    ratear(db, titulo, "700.00")

    with pytest.raises(BusinessRuleError) as exc:
        ratear(db, titulo, "300.01")

    assert exc.value.code == "RATEIO_EXCEDE_VALOR_TITULO"
    assert exc.value.details["valor_disponivel"] == "300.00"


def test_regra1_reduzir_valor_abaixo_do_rateado_e_bloqueado(db):
    titulo = criar_titulo(db, valor="1000.00")
    ratear(db, titulo, "800.00")

    with pytest.raises(BusinessRuleError) as exc:
        TituloService(db).atualizar(
            titulo.id,
            TituloUpdate(
                numero=titulo.numero,
                descricao=titulo.descricao,
                data_emissao=titulo.data_emissao,
                data_vencimento=titulo.data_vencimento,
                valor_total=Decimal("799.99"),
            ),
        )

    assert exc.value.code == "VALOR_MENOR_QUE_RATEIO"


# ---------------------------------------------------------------- regra 4


def test_regra4_centro_custo_inativo_nao_recebe_rateio(db):
    titulo = criar_titulo(db)
    centro = criar_centro_custo(db, ativo=False)

    with pytest.raises(BusinessRuleError) as exc:
        ratear(db, titulo, "100.00", centro=centro)

    assert exc.value.code == "CENTRO_CUSTO_INATIVO"


# ---------------------------------------------------------------- outras validações


def test_centro_custo_repetido_no_mesmo_titulo(db):
    titulo = criar_titulo(db)
    centro = criar_centro_custo(db)
    ratear(db, titulo, "100.00", centro=centro)

    with pytest.raises(ConflictError):
        ratear(db, titulo, "100.00", centro=centro)


def test_rateio_gera_log(db):
    titulo = criar_titulo(db, valor="1000.00")
    ratear(db, titulo, "250.00")

    ultimo = LogRepository(db).list_by_titulo(titulo.id)[-1]
    assert ultimo.tipo == TipoLog.RATEIO
    assert "Total rateado: 250.00 de 1000.00" in ultimo.mensagem


def test_titulo_aprovado_nao_aceita_novo_rateio(db):
    titulo = criar_titulo_aprovado(db)
    centro = criar_centro_custo(db)

    with pytest.raises(BusinessRuleError) as exc:
        RateioService(db).adicionar(
            titulo.id, RateioCreate(centro_custo_id=centro.id, valor=Decimal("1.00"))
        )

    assert exc.value.code == "TITULO_NAO_EDITAVEL"


def test_remover_rateio(db):
    titulo = criar_titulo(db)
    rateio = ratear(db, titulo, "100.00")

    RateioService(db).remover(titulo.id, rateio.id)

    assert RateioService(db).listar(titulo.id) == []


def test_remover_rateio_de_outro_titulo_retorna_nao_encontrado(db):
    rateio = ratear(db, criar_titulo(db), "100.00")
    outro = criar_titulo(db)

    with pytest.raises(NotFoundError):
        RateioService(db).remover(outro.id, rateio.id)


# ---------------------------------------------------------------- aprovação


def test_aprovacao_exige_rateio_de_100_por_cento(db):
    titulo = criar_titulo(db, valor="1000.00")
    ratear(db, titulo, "999.99")

    with pytest.raises(BusinessRuleError) as exc:
        TituloService(db).aprovar(titulo.id)

    assert exc.value.code == "RATEIO_INCOMPLETO"
    assert exc.value.details["valor_faltante"] == "0.01"


def test_titulo_sem_rateio_nao_pode_ser_aprovado(db):
    titulo = criar_titulo(db)

    with pytest.raises(BusinessRuleError) as exc:
        TituloService(db).aprovar(titulo.id)

    assert exc.value.code == "RATEIO_INCOMPLETO"


def test_aprovar_com_rateio_completo(db):
    titulo = criar_titulo(db, valor="1000.00")
    ratear(db, titulo, "300.00")
    ratear(db, titulo, "700.00")

    aprovado = TituloService(db).aprovar(titulo.id)

    assert aprovado.status == StatusTitulo.APROVADO
