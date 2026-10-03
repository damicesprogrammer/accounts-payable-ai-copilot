from collections.abc import Sequence
from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import LogIntegracao, StatusLog, StatusTitulo, TipoLog, TituloPagar
from app.repositories.log_repository import LogRepository
from app.repositories.pagamento_repository import PagamentoRepository
from app.repositories.rateio_repository import RateioRepository
from app.repositories.titulo_repository import TituloRepository
from app.schemas.titulo import TituloCreate, TituloUpdate
from app.services import status_titulo
from app.services.audit_service import AuditService
from app.services.fornecedor_service import FornecedorService


class TituloService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = TituloRepository(db)
        self.audit = AuditService(db)

    # ------------------------------------------------------------------ consultas

    def listar(
        self,
        *,
        status: StatusTitulo | None = None,
        fornecedor_id: int | None = None,
        vencidos: bool = False,
        hoje: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[TituloPagar]:
        """`vencidos=True`: títulos em aberto com vencimento anterior a `hoje`."""
        filtros_vencidos = {}
        if vencidos:
            filtros_vencidos = {
                "vencimento_antes_de": hoje or date.today(),
                "status_in": status_titulo.EM_ABERTO,
            }
        return self.repo.list(
            status=status,
            fornecedor_id=fornecedor_id,
            limit=limit,
            offset=offset,
            **filtros_vencidos,
        )

    def obter(self, titulo_id: int) -> TituloPagar:
        titulo = self.repo.get(titulo_id)
        if titulo is None:
            raise self._nao_encontrado(titulo_id)
        return titulo

    def listar_logs(self, titulo_id: int) -> Sequence[LogIntegracao]:
        self.obter(titulo_id)  # 404 se o título não existir
        return LogRepository(self.db).list_by_titulo(titulo_id)

    def obter_para_alteracao(self, titulo_id: int) -> TituloPagar:
        """Obtém o título com lock de linha. Usado por toda operação de escrita
        que depende do estado atual do título (status, totais)."""
        titulo = self.repo.get_for_update(titulo_id)
        if titulo is None:
            raise self._nao_encontrado(titulo_id)
        return titulo

    # ------------------------------------------------------------------ escrita

    def criar(self, dados: TituloCreate) -> TituloPagar:
        fornecedor = FornecedorService(self.db).obter(dados.fornecedor_id)
        # Regra 3: fornecedor inativo não pode receber novos títulos.
        if not fornecedor.ativo:
            raise BusinessRuleError(
                f"Fornecedor {fornecedor.id} ({fornecedor.nome}) está inativo e não pode "
                "receber novos títulos.",
                code="FORNECEDOR_INATIVO",
                fornecedor_id=fornecedor.id,
            )
        self._garantir_numero_unico(dados.fornecedor_id, dados.numero)

        titulo = self.repo.add(
            TituloPagar(
                numero=dados.numero,
                fornecedor_id=dados.fornecedor_id,
                descricao=dados.descricao,
                data_emissao=dados.data_emissao,
                data_vencimento=dados.data_vencimento,
                valor_total=dados.valor_total,
                status=StatusTitulo.PENDENTE,
            )
        )
        self.audit.registrar(
            TipoLog.CRIACAO,
            f"Título {titulo.numero} criado com valor {titulo.valor_total} "
            f"e vencimento em {titulo.data_vencimento.isoformat()}.",
            titulo_id=titulo.id,
        )
        self.db.commit()
        return titulo

    def atualizar(self, titulo_id: int, dados: TituloUpdate) -> TituloPagar:
        titulo = self.obter_para_alteracao(titulo_id)
        status_titulo.validar_editavel(titulo.id, titulo.status)
        if dados.numero != titulo.numero:
            self._garantir_numero_unico(titulo.fornecedor_id, dados.numero)

        # Regra 1 (lado inverso): reduzir o valor não pode deixar o rateio maior que o título.
        valor_rateado = RateioRepository(self.db).soma_por_titulo(titulo.id)
        if dados.valor_total < valor_rateado:
            raise BusinessRuleError(
                f"O valor total {dados.valor_total} é menor que o já rateado ({valor_rateado}). "
                "Ajuste os rateios antes de reduzir o valor do título.",
                code="VALOR_MENOR_QUE_RATEIO",
                titulo_id=titulo.id,
                valor_rateado=str(valor_rateado),
            )

        alteracoes = [
            f"{campo}: {getattr(titulo, campo)} -> {novo}"
            for campo, novo in dados.model_dump().items()
            if getattr(titulo, campo) != novo
        ]
        for campo, valor in dados.model_dump().items():
            setattr(titulo, campo, valor)

        self.audit.registrar(
            TipoLog.ATUALIZACAO,
            "Título atualizado. " + ("; ".join(alteracoes) or "Nenhum campo alterado."),
            titulo_id=titulo.id,
        )
        self.db.commit()
        return titulo

    def aprovar(self, titulo_id: int) -> TituloPagar:
        """Aprova o título para pagamento.

        Regra: só é possível aprovar quando o rateio cobre exatamente 100% do valor.
        """
        titulo = self.obter_para_alteracao(titulo_id)
        status_titulo.validar_transicao(titulo.id, titulo.status, StatusTitulo.APROVADO)

        valor_rateado = RateioRepository(self.db).soma_por_titulo(titulo.id)
        if valor_rateado != titulo.valor_total:
            faltante = titulo.valor_total - valor_rateado
            raise BusinessRuleError(
                f"Título {titulo.id} não pode ser aprovado: rateio cobre {valor_rateado} "
                f"de {titulo.valor_total} (faltam {faltante}).",
                code="RATEIO_INCOMPLETO",
                titulo_id=titulo.id,
                valor_total=str(titulo.valor_total),
                valor_rateado=str(valor_rateado),
                valor_faltante=str(faltante),
            )

        self.mudar_status(titulo, StatusTitulo.APROVADO, "Rateio conferido (100% do valor)")
        self.db.commit()
        return titulo

    def cancelar(self, titulo_id: int, motivo: str) -> TituloPagar:
        titulo = self.obter_para_alteracao(titulo_id)
        valor_pago = PagamentoRepository(self.db).soma_confirmados(titulo.id)
        if valor_pago > 0:
            raise BusinessRuleError(
                f"Título {titulo.id} possui {valor_pago} em pagamentos confirmados. "
                "Estorne os pagamentos antes de cancelar.",
                code="TITULO_COM_PAGAMENTOS",
                titulo_id=titulo.id,
                valor_pago=str(valor_pago),
            )
        self.mudar_status(titulo, StatusTitulo.CANCELADO, motivo)
        self.db.commit()
        return titulo

    def reprocessar(self, titulo_id: int) -> TituloPagar:
        """Devolve um título em ERRO para PENDENTE, após a causa ser corrigida."""
        titulo = self.obter_para_alteracao(titulo_id)
        self.mudar_status(titulo, StatusTitulo.PENDENTE, "Reprocessamento solicitado")
        self.db.commit()
        return titulo

    def registrar_erro_integracao(self, titulo_id: int, mensagem: str) -> TituloPagar:
        """Marca o título como ERRO após falha na integração com o ERP.

        Nesta fase a integração é simulada (usada pelo seed); o ponto de entrada
        já existe para que uma integração real possa chamá-lo.
        """
        titulo = self.obter_para_alteracao(titulo_id)
        self.mudar_status(titulo, StatusTitulo.ERRO, "Falha na integração")
        self.audit.registrar(
            TipoLog.INTEGRACAO, mensagem, titulo_id=titulo.id, status=StatusLog.ERRO
        )
        self.db.commit()
        return titulo

    # ------------------------------------------------------------------ apoio

    def mudar_status(self, titulo: TituloPagar, novo: StatusTitulo, motivo: str) -> None:
        """Aplica uma transição validada e registra o log. Não faz commit: compõe
        operações maiores (ex.: quitação automática ao registrar pagamento)."""
        anterior = titulo.status
        status_titulo.validar_transicao(titulo.id, anterior, novo)
        if novo == StatusTitulo.PAGO:
            self._garantir_quitado(titulo)
        titulo.status = novo
        self.audit.registrar(
            TipoLog.MUDANCA_STATUS,
            f"Status alterado de {anterior} para {novo}. Motivo: {motivo}",
            titulo_id=titulo.id,
        )

    def _garantir_quitado(self, titulo: TituloPagar) -> None:
        """Regra 2: só é PAGO quando os pagamentos confirmados somam exatamente o valor.

        Fica no único ponto por onde qualquer mudança de status passa, então
        nenhum fluxo — atual ou futuro — consegue marcar PAGO sem quitação.
        """
        valor_pago = PagamentoRepository(self.db).soma_confirmados(titulo.id)
        if valor_pago != titulo.valor_total:
            raise BusinessRuleError(
                f"Título {titulo.id} não pode ser marcado como PAGO: pagamentos confirmados "
                f"somam {valor_pago} de {titulo.valor_total}.",
                code="PAGAMENTOS_NAO_QUITAM_TITULO",
                titulo_id=titulo.id,
                valor_total=str(titulo.valor_total),
                valor_pago=str(valor_pago),
            )

    def _garantir_numero_unico(self, fornecedor_id: int, numero: str) -> None:
        if self.repo.get_by_numero(fornecedor_id, numero):
            raise ConflictError(
                f"Já existe título {numero} para o fornecedor {fornecedor_id}.",
                code="TITULO_DUPLICADO",
                fornecedor_id=fornecedor_id,
                numero=numero,
            )

    @staticmethod
    def _nao_encontrado(titulo_id: int) -> NotFoundError:
        return NotFoundError(
            f"Título {titulo_id} não encontrado.",
            code="TITULO_NAO_ENCONTRADO",
            titulo_id=titulo_id,
        )
