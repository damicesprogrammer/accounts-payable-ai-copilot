from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import RateioTitulo, TipoLog
from app.repositories.rateio_repository import RateioRepository
from app.schemas.rateio import RateioCreate
from app.services import status_titulo
from app.services.audit_service import AuditService
from app.services.centro_custo_service import CentroCustoService
from app.services.titulo_service import TituloService


class RateioService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = RateioRepository(db)
        self.titulos = TituloService(db)
        self.audit = AuditService(db)

    def listar(self, titulo_id: int) -> Sequence[RateioTitulo]:
        self.titulos.obter(titulo_id)  # 404 se o título não existir
        return self.repo.list_by_titulo(titulo_id)

    def adicionar(self, titulo_id: int, dados: RateioCreate) -> RateioTitulo:
        titulo = self.titulos.obter_para_alteracao(titulo_id)
        # Rateio só muda antes da aprovação: a aprovação conferiu os 100%.
        status_titulo.validar_editavel(titulo.id, titulo.status)

        centro = CentroCustoService(self.db).obter(dados.centro_custo_id)
        # Regra 4: centro de custo inativo não pode receber novos rateios.
        if not centro.ativo:
            raise BusinessRuleError(
                f"Centro de custo {centro.codigo} está inativo e não pode receber rateios.",
                code="CENTRO_CUSTO_INATIVO",
                centro_custo_id=centro.id,
                codigo=centro.codigo,
            )
        if self.repo.get_by_titulo_e_centro(titulo.id, centro.id):
            raise ConflictError(
                f"O título {titulo.id} já possui rateio para o centro de custo {centro.codigo}.",
                code="RATEIO_DUPLICADO",
                titulo_id=titulo.id,
                centro_custo_id=centro.id,
            )

        # Regra 1: a soma dos rateios não pode ultrapassar o valor do título.
        ja_rateado = self.repo.soma_por_titulo(titulo.id)
        disponivel = titulo.valor_total - ja_rateado
        if dados.valor > disponivel:
            raise BusinessRuleError(
                f"Rateio de {dados.valor} excede o valor disponível do título {titulo.id}: "
                f"valor total {titulo.valor_total}, já rateado {ja_rateado}, "
                f"disponível {disponivel}.",
                code="RATEIO_EXCEDE_VALOR_TITULO",
                titulo_id=titulo.id,
                valor_total=str(titulo.valor_total),
                valor_rateado=str(ja_rateado),
                valor_disponivel=str(disponivel),
            )

        rateio = self.repo.add(
            RateioTitulo(titulo_id=titulo.id, centro_custo_id=centro.id, valor=dados.valor)
        )
        self.audit.registrar(
            TipoLog.RATEIO,
            f"Rateio de {rateio.valor} adicionado ao centro de custo {centro.codigo}. "
            f"Total rateado: {ja_rateado + rateio.valor} de {titulo.valor_total}.",
            titulo_id=titulo.id,
        )
        self.db.commit()
        return rateio

    def remover(self, titulo_id: int, rateio_id: int) -> None:
        titulo = self.titulos.obter_para_alteracao(titulo_id)
        status_titulo.validar_editavel(titulo.id, titulo.status)

        rateio = self.repo.get(rateio_id)
        if rateio is None or rateio.titulo_id != titulo.id:
            raise NotFoundError(
                f"Rateio {rateio_id} não encontrado no título {titulo_id}.",
                code="RATEIO_NAO_ENCONTRADO",
                titulo_id=titulo_id,
                rateio_id=rateio_id,
            )
        codigo_centro = rateio.centro_custo.codigo
        valor = rateio.valor
        self.repo.delete(rateio)
        self.audit.registrar(
            TipoLog.RATEIO,
            f"Rateio de {valor} removido do centro de custo {codigo_centro}.",
            titulo_id=titulo.id,
        )
        self.db.commit()
