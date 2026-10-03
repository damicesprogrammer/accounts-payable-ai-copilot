import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.schemas.centro_custo import CentroCustoCreate, CentroCustoUpdate
from app.services.centro_custo_service import CentroCustoService
from tests.factories import criar_centro_custo


def test_criar_centro_custo_normaliza_codigo(db):
    centro = CentroCustoService(db).criar(CentroCustoCreate(codigo=" adm01 ", descricao="Adm"))

    assert centro.codigo == "ADM01"
    assert centro.ativo is True


def test_nao_permite_codigo_duplicado(db):
    criar_centro_custo(db, codigo="1001")

    with pytest.raises(ConflictError) as exc:
        CentroCustoService(db).criar(CentroCustoCreate(codigo="1001", descricao="Outro"))

    assert exc.value.code == "CODIGO_CENTRO_CUSTO_DUPLICADO"


def test_inativar_centro_custo(db):
    centro = criar_centro_custo(db)

    atualizado = CentroCustoService(db).atualizar(
        centro.id, CentroCustoUpdate(descricao=centro.descricao, ativo=False)
    )

    assert atualizado.ativo is False


def test_obter_centro_inexistente(db):
    with pytest.raises(NotFoundError):
        CentroCustoService(db).obter(999_999)
