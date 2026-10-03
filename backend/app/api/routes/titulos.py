from fastapi import APIRouter, status

from app.api.deps import ERROS_404, ERROS_409, ERROS_422, DbSession, PaginacaoParams
from app.models import StatusTitulo
from app.schemas.log import LogRead
from app.schemas.pagamento import PagamentoCreate, PagamentoRead
from app.schemas.rateio import RateioCreate, RateioRead
from app.schemas.titulo import (
    CancelamentoInput,
    TituloCreate,
    TituloDetalhe,
    TituloRead,
    TituloUpdate,
)
from app.services.pagamento_service import PagamentoService
from app.services.rateio_service import RateioService
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


@router.get("/{titulo_id}", response_model=TituloDetalhe, responses=ERROS_404)
def obter_titulo(titulo_id: int, db: DbSession):
    return TituloService(db).obter_detalhe(titulo_id)


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


@router.post(
    "/{titulo_id}/aprovar", response_model=TituloRead, responses={**ERROS_404, **ERROS_422}
)
def aprovar_titulo(titulo_id: int, db: DbSession):
    """Exige rateio cobrindo 100% do valor do título."""
    return TituloService(db).aprovar(titulo_id)


# ---------------------------------------------------------------- rateios


@router.get("/{titulo_id}/rateios", response_model=list[RateioRead], responses=ERROS_404)
def listar_rateios(titulo_id: int, db: DbSession):
    return RateioService(db).listar(titulo_id)


@router.post(
    "/{titulo_id}/rateios",
    response_model=RateioRead,
    status_code=status.HTTP_201_CREATED,
    responses={**ERROS_404, **ERROS_409, **ERROS_422},
)
def adicionar_rateio(titulo_id: int, dados: RateioCreate, db: DbSession):
    return RateioService(db).adicionar(titulo_id, dados)


@router.delete(
    "/{titulo_id}/rateios/{rateio_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**ERROS_404, **ERROS_422},
)
def remover_rateio(titulo_id: int, rateio_id: int, db: DbSession) -> None:
    RateioService(db).remover(titulo_id, rateio_id)


# ---------------------------------------------------------------- pagamentos


@router.get("/{titulo_id}/pagamentos", response_model=list[PagamentoRead], responses=ERROS_404)
def listar_pagamentos(titulo_id: int, db: DbSession):
    return PagamentoService(db).listar(titulo_id)


@router.post(
    "/{titulo_id}/pagamentos",
    response_model=PagamentoRead,
    status_code=status.HTTP_201_CREATED,
    responses={**ERROS_404, **ERROS_422},
)
def registrar_pagamento(titulo_id: int, dados: PagamentoCreate, db: DbSession):
    """Quando a soma dos pagamentos confirmados atinge o valor total, o título
    passa automaticamente para PAGO."""
    return PagamentoService(db).registrar(titulo_id, dados)


@router.post(
    "/{titulo_id}/pagamentos/{pagamento_id}/estornar",
    response_model=PagamentoRead,
    responses={**ERROS_404, **ERROS_422},
)
def estornar_pagamento(titulo_id: int, pagamento_id: int, db: DbSession):
    return PagamentoService(db).estornar(titulo_id, pagamento_id)


# ---------------------------------------------------------------- auditoria


@router.get("/{titulo_id}/logs", response_model=list[LogRead], responses=ERROS_404)
def listar_logs(titulo_id: int, db: DbSession):
    """Trilha de auditoria do título, em ordem cronológica."""
    return TituloService(db).listar_logs(titulo_id)
