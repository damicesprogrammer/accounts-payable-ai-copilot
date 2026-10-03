"""Construtores de dados de teste.

Criam entidades através dos services (e não inserindo direto no banco), para que
os dados de teste respeitem as mesmas regras de negócio da aplicação.
"""

from datetime import date, timedelta
from decimal import Decimal
from itertools import count

from sqlalchemy.orm import Session

from app.core import cnpj
from app.models import CentroCusto, Fornecedor, TituloPagar
from app.schemas.centro_custo import CentroCustoCreate, CentroCustoUpdate
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.schemas.titulo import TituloCreate
from app.services.centro_custo_service import CentroCustoService
from app.services.fornecedor_service import FornecedorService
from app.services.titulo_service import TituloService

_seq = count(1)


def criar_fornecedor(db: Session, *, nome: str | None = None, ativo: bool = True) -> Fornecedor:
    n = next(_seq)
    service = FornecedorService(db)
    fornecedor = service.criar(FornecedorCreate(nome=nome or f"Fornecedor {n}", cnpj=cnpj.gerar(n)))
    if not ativo:
        fornecedor = service.atualizar(
            fornecedor.id, FornecedorUpdate(nome=fornecedor.nome, ativo=False)
        )
    return fornecedor


def criar_centro_custo(
    db: Session, *, codigo: str | None = None, ativo: bool = True
) -> CentroCusto:
    n = next(_seq)
    service = CentroCustoService(db)
    centro = service.criar(
        CentroCustoCreate(codigo=codigo or f"CC{n:04d}", descricao=f"Centro de custo {n}")
    )
    if not ativo:
        centro = service.atualizar(
            centro.id, CentroCustoUpdate(descricao=centro.descricao, ativo=False)
        )
    return centro


def criar_titulo(
    db: Session,
    *,
    fornecedor: Fornecedor | None = None,
    valor: str = "1000.00",
    emissao: date | None = None,
    vencimento: date | None = None,
    numero: str | None = None,
) -> TituloPagar:
    fornecedor = fornecedor or criar_fornecedor(db)
    emissao = emissao or date.today()
    return TituloService(db).criar(
        TituloCreate(
            numero=numero or f"NF-{next(_seq)}",
            fornecedor_id=fornecedor.id,
            descricao="Título de teste",
            data_emissao=emissao,
            data_vencimento=vencimento or emissao + timedelta(days=30),
            valor_total=Decimal(valor),
        )
    )
