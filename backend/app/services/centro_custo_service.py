from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import CentroCusto, TipoLog
from app.repositories.centro_custo_repository import CentroCustoRepository
from app.schemas.centro_custo import CentroCustoCreate, CentroCustoUpdate
from app.services.audit_service import AuditService


class CentroCustoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CentroCustoRepository(db)
        self.audit = AuditService(db)

    def listar(
        self, *, ativo: bool | None = None, limit: int = 50, offset: int = 0
    ) -> Sequence[CentroCusto]:
        return self.repo.list(ativo=ativo, limit=limit, offset=offset)

    def obter(self, centro_custo_id: int) -> CentroCusto:
        centro = self.repo.get(centro_custo_id)
        if centro is None:
            raise NotFoundError(
                f"Centro de custo {centro_custo_id} não encontrado.",
                code="CENTRO_CUSTO_NAO_ENCONTRADO",
                centro_custo_id=centro_custo_id,
            )
        return centro

    def criar(self, dados: CentroCustoCreate) -> CentroCusto:
        if self.repo.get_by_codigo(dados.codigo):
            raise ConflictError(
                f"Já existe centro de custo com o código {dados.codigo}.",
                code="CODIGO_CENTRO_CUSTO_DUPLICADO",
                codigo=dados.codigo,
            )
        centro = self.repo.add(
            CentroCusto(codigo=dados.codigo, descricao=dados.descricao, ativo=True)
        )
        self.audit.registrar(
            TipoLog.CADASTRO, f"Centro de custo {centro.codigo} ({centro.descricao}) cadastrado."
        )
        self.db.commit()
        return centro

    def atualizar(self, centro_custo_id: int, dados: CentroCustoUpdate) -> CentroCusto:
        centro = self.obter(centro_custo_id)
        alterou_situacao = centro.ativo != dados.ativo

        centro.descricao = dados.descricao
        centro.ativo = dados.ativo

        mensagem = f"Centro de custo {centro.codigo} atualizado."
        if alterou_situacao:
            situacao = "ativado" if dados.ativo else "inativado"
            mensagem = f"Centro de custo {centro.codigo} {situacao}."
        self.audit.registrar(TipoLog.CADASTRO, mensagem)
        self.db.commit()
        return centro
