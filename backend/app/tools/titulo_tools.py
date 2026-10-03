"""Tools de consulta financeira (somente leitura).

Cada tool apenas chama métodos de leitura dos services e devolve dados
serializáveis. Nenhuma faz commit, altera dados ou acessa repositories/SQL.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.schemas.log import LogRead
from app.schemas.pagamento import PagamentoRead
from app.schemas.rateio import RateioRead
from app.services.pagamento_service import PagamentoService
from app.services.rateio_service import RateioService
from app.services.titulo_service import TituloService
from app.tools.contracts import Tool

# Campos técnicos que não ajudam o modelo a raciocinar sobre o título.
_CAMPOS_TECNICOS = {"fornecedor_id", "created_at", "updated_at"}

# Totais calculados pelo sistema + o essencial de cada título vencido.
_CAMPOS_VENCIDOS = {
    "quantidade": True,
    "valor_total_titulos": True,
    "saldo_pendente_total": True,
    "titulos": {
        "__all__": {
            "id",
            "numero",
            "fornecedor",
            "status",
            "data_vencimento",
            "valor_total",
            "valor_pago",
            "saldo_pendente",
        }
    },
}


class TituloIdInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    titulo_id: int = Field(gt=0, description="ID numérico do título a pagar.")


class SemArgumentos(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _get_titulo(db: Session, args: TituloIdInput) -> dict[str, Any]:
    detalhe = TituloService(db).obter_detalhe(args.titulo_id)
    return detalhe.model_dump(mode="json", exclude=_CAMPOS_TECNICOS)


def _get_rateios_titulo(db: Session, args: TituloIdInput) -> list[dict[str, Any]]:
    rateios = RateioService(db).listar(args.titulo_id)
    return [RateioRead.model_validate(r).model_dump(mode="json") for r in rateios]


def _get_pagamentos_titulo(db: Session, args: TituloIdInput) -> list[dict[str, Any]]:
    pagamentos = PagamentoService(db).listar(args.titulo_id)
    return [PagamentoRead.model_validate(p).model_dump(mode="json") for p in pagamentos]


def _get_logs_titulo(db: Session, args: TituloIdInput) -> list[dict[str, Any]]:
    logs = TituloService(db).listar_logs(args.titulo_id)
    return [LogRead.model_validate(log).model_dump(mode="json") for log in logs]


def _get_titulos_vencidos(db: Session, args: SemArgumentos) -> dict[str, Any]:
    resumo = TituloService(db).resumo_vencidos()
    return resumo.model_dump(mode="json", include=_CAMPOS_VENCIDOS)


get_titulo = Tool(
    name="get_titulo",
    description=(
        "Consulta um título a pagar: status, fornecedor, datas, valor total, valor "
        "rateado, valor pago, saldo pendente e se está vencido."
    ),
    input_model=TituloIdInput,
    handler=_get_titulo,
)

get_rateios_titulo = Tool(
    name="get_rateios_titulo",
    description="Lista os rateios do título por centro de custo (código, situação e valor).",
    input_model=TituloIdInput,
    handler=_get_rateios_titulo,
)

get_pagamentos_titulo = Tool(
    name="get_pagamentos_titulo",
    description="Lista os pagamentos do título (data, valor e status CONFIRMADO/ESTORNADO).",
    input_model=TituloIdInput,
    handler=_get_pagamentos_titulo,
)

get_logs_titulo = Tool(
    name="get_logs_titulo",
    description=(
        "Lista a trilha de auditoria do título em ordem cronológica, incluindo mudanças "
        "de status e erros de integração."
    ),
    input_model=TituloIdInput,
    handler=_get_logs_titulo,
)

get_titulos_vencidos = Tool(
    name="get_titulos_vencidos",
    description=(
        "Lista os títulos em aberto (PENDENTE, APROVADO ou ERRO) com vencimento anterior a "
        "hoje, com quantidade, valor_total_titulos (soma dos valores originais) e "
        "saldo_pendente_total (soma do que falta pagar) já calculados pelo sistema."
    ),
    input_model=SemArgumentos,
    handler=_get_titulos_vencidos,
)
