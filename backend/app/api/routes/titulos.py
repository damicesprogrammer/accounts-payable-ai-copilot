from fastapi import APIRouter, status

from app.api.deps import ERROS_404, ERROS_409, ERROS_422, DbSession, PaginacaoParams
from app.models import StatusTitulo
from app.schemas.titulo import CancelamentoInput, TituloCreate, TituloRead, TituloUpdate
from app.services.titulo_service import TituloService

router = APIRouter(prefix="/titulos", tags=["títulos"])


@router.get("", response_model=list[TituloRead])
def listar_titulos(
    db: DbSession,
    paginacao: PaginacaoParams,
    status: StatusTitulo | None = None,
    fornecedor_id: int | None = None,
    vencidos: bool = False,
):
    return TituloService(db).listar(
        status=status,
        fornecedor_id=fornecedor_id,
        vencidos=vencidos,
        limit=paginacao.limit,
        offset=paginacao.offset,
    )


@router.get("/{titulo_id}", response_model=TituloRead, responses=ERROS_404)
def obter_titulo(titulo_id: int, db: DbSession):
    return TituloService(db).obter(titulo_id)


@router.post(
    "",
    response_model=TituloRead,
    status_code=status.HTTP_201_CREATED,
    responses={**ERROS_404, **ERROS_409, **ERROS_422},
)
def criar_titulo(dados: TituloCreate, db: DbSession):
    return TituloService(db).criar(dados)


@router.put(
    "/{titulo_id}", response_model=TituloRead, responses={**ERROS_404, **ERROS_409, **ERROS_422}
)
def atualizar_titulo(titulo_id: int, dados: TituloUpdate, db: DbSession):
    return TituloService(db).atualizar(titulo_id, dados)


@router.post(
    "/{titulo_id}/cancelar", response_model=TituloRead, responses={**ERROS_404, **ERROS_422}
)
def cancelar_titulo(titulo_id: int, dados: CancelamentoInput, db: DbSession):
    return TituloService(db).cancelar(titulo_id, dados.motivo)


@router.post(
    "/{titulo_id}/reprocessar", response_model=TituloRead, responses={**ERROS_404, **ERROS_422}
)
def reprocessar_titulo(titulo_id: int, db: DbSession):
    return TituloService(db).reprocessar(titulo_id)
