from fastapi import APIRouter, status

from app.api.deps import ERROS_404, ERROS_409, DbSession, PaginacaoParams
from app.schemas.fornecedor import FornecedorCreate, FornecedorRead, FornecedorUpdate
from app.services.fornecedor_service import FornecedorService

router = APIRouter(prefix="/fornecedores", tags=["fornecedores"])


@router.get("", response_model=list[FornecedorRead])
def listar_fornecedores(db: DbSession, paginacao: PaginacaoParams, ativo: bool | None = None):
    return FornecedorService(db).listar(ativo=ativo, limit=paginacao.limit, offset=paginacao.offset)


@router.get("/{fornecedor_id}", response_model=FornecedorRead, responses=ERROS_404)
def obter_fornecedor(fornecedor_id: int, db: DbSession):
    return FornecedorService(db).obter(fornecedor_id)


@router.post(
    "", response_model=FornecedorRead, status_code=status.HTTP_201_CREATED, responses=ERROS_409
)
def criar_fornecedor(dados: FornecedorCreate, db: DbSession):
    return FornecedorService(db).criar(dados)


@router.put("/{fornecedor_id}", response_model=FornecedorRead, responses=ERROS_404)
def atualizar_fornecedor(fornecedor_id: int, dados: FornecedorUpdate, db: DbSession):
    return FornecedorService(db).atualizar(fornecedor_id, dados)
