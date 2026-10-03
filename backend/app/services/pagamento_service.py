from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.models import Pagamento, StatusPagamento, StatusTitulo, TipoLog, TituloPagar
from app.repositories.pagamento_repository import PagamentoRepository
from app.schemas.pagamento import PagamentoCreate
from app.services.audit_service import AuditService
from app.services.titulo_service import TituloService


class PagamentoService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PagamentoRepository(db)
        self.titulos = TituloService(db)
        self.audit = AuditService(db)

    def listar(self, titulo_id: int) -> Sequence[Pagamento]:
        self.titulos.obter(titulo_id)  # 404 se o título não existir
        return self.repo.list_by_titulo(titulo_id)

    def registrar(self, titulo_id: int, dados: PagamentoCreate) -> Pagamento:
        # Lock de linha: dois pagamentos simultâneos não podem, juntos, exceder o saldo.
        titulo = self.titulos.obter_para_alteracao(titulo_id)
        self._validar_titulo_aceita_pagamento(titulo)

        if dados.data_pagamento < titulo.data_emissao:
            raise BusinessRuleError(
                f"Data de pagamento {dados.data_pagamento} é anterior à emissão do título "
                f"({titulo.data_emissao}).",
                code="DATA_PAGAMENTO_INVALIDA",
                titulo_id=titulo.id,
            )

        valor_pago = self.repo.soma_confirmados(titulo.id)
        saldo = titulo.valor_total - valor_pago
        if dados.valor > saldo:
            raise BusinessRuleError(
                f"Pagamento de {dados.valor} excede o saldo pendente de {saldo} do título "
                f"{titulo.id} (valor total {titulo.valor_total}, já pago {valor_pago}).",
                code="PAGAMENTO_EXCEDE_SALDO",
                titulo_id=titulo.id,
                valor_total=str(titulo.valor_total),
                valor_pago=str(valor_pago),
                saldo_pendente=str(saldo),
            )

        pagamento = self.repo.add(
            Pagamento(
                titulo_id=titulo.id,
                data_pagamento=dados.data_pagamento,
                valor=dados.valor,
                status=StatusPagamento.CONFIRMADO,
            )
        )
        novo_saldo = saldo - pagamento.valor
        self.audit.registrar(
            TipoLog.PAGAMENTO,
            f"Pagamento de {pagamento.valor} confirmado em {pagamento.data_pagamento}. "
            f"Total pago: {valor_pago + pagamento.valor} de {titulo.valor_total}. "
            f"Saldo pendente: {novo_saldo}.",
            titulo_id=titulo.id,
        )

        # Regra 2: quitação automática quando os pagamentos atingem exatamente o valor.
        if novo_saldo == 0:
            self.titulos.mudar_status(
                titulo, StatusTitulo.PAGO, "Pagamentos confirmados quitaram o valor total"
            )

        self.db.commit()
        return pagamento

    def estornar(self, titulo_id: int, pagamento_id: int) -> Pagamento:
        """Estorna um pagamento de título ainda APROVADO (PAGO é estado final)."""
        titulo = self.titulos.obter_para_alteracao(titulo_id)
        pagamento = self.repo.get(pagamento_id)
        if pagamento is None or pagamento.titulo_id != titulo.id:
            raise NotFoundError(
                f"Pagamento {pagamento_id} não encontrado no título {titulo_id}.",
                code="PAGAMENTO_NAO_ENCONTRADO",
                titulo_id=titulo_id,
                pagamento_id=pagamento_id,
            )
        if titulo.status != StatusTitulo.APROVADO:
            raise BusinessRuleError(
                f"Título {titulo.id} está {titulo.status}; só é possível estornar pagamentos "
                "de títulos APROVADO.",
                code="ESTORNO_NAO_PERMITIDO",
                titulo_id=titulo.id,
                status_atual=titulo.status,
            )
        if pagamento.status == StatusPagamento.ESTORNADO:
            raise BusinessRuleError(
                f"Pagamento {pagamento.id} já está estornado.",
                code="PAGAMENTO_JA_ESTORNADO",
                pagamento_id=pagamento.id,
            )

        pagamento.status = StatusPagamento.ESTORNADO
        self.audit.registrar(
            TipoLog.PAGAMENTO,
            f"Pagamento {pagamento.id} de {pagamento.valor} estornado.",
            titulo_id=titulo.id,
        )
        self.db.commit()
        return pagamento

    def _validar_titulo_aceita_pagamento(self, titulo: TituloPagar) -> None:
        # Regra 5: título cancelado não recebe pagamentos.
        if titulo.status == StatusTitulo.CANCELADO:
            raise BusinessRuleError(
                f"Título {titulo.id} está CANCELADO e não pode receber pagamentos.",
                code="TITULO_CANCELADO",
                titulo_id=titulo.id,
            )
        if titulo.status == StatusTitulo.PAGO:
            raise BusinessRuleError(
                f"Título {titulo.id} já está PAGO.",
                code="TITULO_JA_PAGO",
                titulo_id=titulo.id,
            )
        # Regra adicional: pagamento somente para títulos aprovados.
        if titulo.status != StatusTitulo.APROVADO:
            raise BusinessRuleError(
                f"Título {titulo.id} está {titulo.status}; pagamentos só são aceitos para "
                "títulos APROVADO.",
                code="TITULO_NAO_APROVADO",
                titulo_id=titulo.id,
                status_atual=titulo.status,
            )
