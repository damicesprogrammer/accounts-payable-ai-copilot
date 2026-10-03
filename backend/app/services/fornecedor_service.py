from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Fornecedor, TipoLog
from app.repositories.fornecedor_repository import FornecedorRepository
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.services.audit_service import AuditService


class FornecedorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = FornecedorRepository(db)
        self.audit = AuditService(db)

    def listar(
        self, *, ativo: bool | None = None, limit: int = 50, offset: int = 0
    ) -> Sequence[Fornecedor]:
        return self.repo.list(ativo=ativo, limit=limit, offset=offset)

    def obter(self, fornecedor_id: int) -> Fornecedor:
        fornecedor = self.repo.get(fornecedor_id)
        if fornecedor is None:
            raise NotFoundError(
                f"Fornecedor {fornecedor_id} não encontrado.",
                code="FORNECEDOR_NAO_ENCONTRADO",
                fornecedor_id=fornecedor_id,
            )
        return fornecedor

    def criar(self, dados: FornecedorCreate) -> Fornecedor:
        if self.repo.get_by_cnpj(dados.cnpj):
            raise ConflictError(
                f"Já existe fornecedor com o CNPJ {dados.cnpj}.",
                code="CNPJ_DUPLICADO",
                cnpj=dados.cnpj,
            )
        fornecedor = self.repo.add(Fornecedor(nome=dados.nome, cnpj=dados.cnpj, ativo=True))
        self.audit.registrar(
            TipoLog.CADASTRO, f"Fornecedor {fornecedor.id} ({fornecedor.nome}) cadastrado."
        )
        self.db.commit()
        return fornecedor

    def atualizar(self, fornecedor_id: int, dados: FornecedorUpdate) -> Fornecedor:
        fornecedor = self.obter(fornecedor_id)
        alterou_situacao = fornecedor.ativo != dados.ativo

        fornecedor.nome = dados.nome
        fornecedor.ativo = dados.ativo

        mensagem = f"Fornecedor {fornecedor.id} atualizado."
        if alterou_situacao:
            mensagem = f"Fornecedor {fornecedor.id} {'ativado' if dados.ativo else 'inativado'}."
        self.audit.registrar(TipoLog.CADASTRO, mensagem)
        self.db.commit()
        return fornecedor
