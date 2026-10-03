import pytest
from sqlalchemy import select

from app.core import cnpj
from app.core.exceptions import ConflictError, NotFoundError
from app.models import LogAuditoria, TipoLog
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.services.fornecedor_service import FornecedorService
from tests.factories import criar_fornecedor


def test_criar_fornecedor_ativo_por_padrao(db):
    fornecedor = FornecedorService(db).criar(
        FornecedorCreate(nome="ACME Ltda", cnpj="11.222.333/0001-81")
    )

    assert fornecedor.id is not None
    assert fornecedor.ativo is True
    assert fornecedor.cnpj == "11222333000181"  # armazenado sem pontuação


def test_nao_permite_cnpj_duplicado(db):
    existente = criar_fornecedor(db)

    with pytest.raises(ConflictError) as exc:
        FornecedorService(db).criar(FornecedorCreate(nome="Outro", cnpj=existente.cnpj))

    assert exc.value.code == "CNPJ_DUPLICADO"


def test_inativar_fornecedor_gera_log(db):
    fornecedor = criar_fornecedor(db)

    FornecedorService(db).atualizar(fornecedor.id, FornecedorUpdate(nome="X", ativo=False))

    mensagens = db.scalars(
        select(LogAuditoria.mensagem).where(LogAuditoria.tipo == TipoLog.CADASTRO)
    ).all()
    assert f"Fornecedor {fornecedor.id} inativado." in mensagens


def test_obter_fornecedor_inexistente(db):
    with pytest.raises(NotFoundError):
        FornecedorService(db).obter(999_999)


def test_schema_rejeita_cnpj_invalido():
    with pytest.raises(ValueError, match="CNPJ inválido"):
        FornecedorCreate(nome="X", cnpj=cnpj.gerar(1)[:-1] + "0")
