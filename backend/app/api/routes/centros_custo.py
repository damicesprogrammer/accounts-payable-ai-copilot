from fastapi import APIRouter, status

from app.api.deps import ERROS_404, ERROS_409, DbSession, PaginacaoParams
from app.schemas.centro_custo import CentroCustoCreate, CentroCustoRead, CentroCustoUpdate
from app.services.centro_custo_service import CentroCustoService

router = APIRouter(prefix="/centros-custo", tags=["centros de custo"])


@router.get("", response_model=list[CentroCustoRead])
def listar_centros_custo(db: DbSession, paginacao: PaginacaoParams, ativo: bool | None = None):
    return CentroCustoService(db).listar(
        ativo=ativo, limit=paginacao.limit, offset=paginacao.offset
    )


@router.get("/{centro_custo_id}", response_model=CentroCustoRead, responses=ERROS_404)
def obter_centro_custo(centro_custo_id: int, db: DbSession):
    return CentroCustoService(db).obter(centro_custo_id)


@router.post(
    "", response_model=CentroCustoRead, status_code=status.HTTP_201_CREATED, responses=ERROS_409
)
def criar_centro_custo(dados: CentroCustoCreate, db: DbSession):
    return CentroCustoService(db).criar(dados)


@router.put("/{centro_custo_id}", response_model=CentroCustoRead, responses=ERROS_404)
def atualizar_centro_custo(centro_custo_id: int, dados: CentroCustoUpdate, db: DbSession):
    return CentroCustoService(db).atualizar(centro_custo_id, dados)
