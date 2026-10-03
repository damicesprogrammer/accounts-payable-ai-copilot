"""Construtores de dados de teste.

Criam entidades através dos services (e não inserindo direto no banco), para que
os dados de teste respeitem as mesmas regras de negócio da aplicação.
"""

from datetime import date, timedelta
from decimal import Decimal
from itertools import count

from sqlalchemy.orm import Session

from app.core import cnpj
from app.models import CentroCusto, Fornecedor, Pagamento, RateioTitulo, TituloPagar
from app.schemas.centro_custo import CentroCustoCreate, CentroCustoUpdate
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.schemas.pagamento import PagamentoCreate
from app.schemas.rateio import RateioCreate
from app.schemas.titulo import TituloCreate
from app.services.centro_custo_service import CentroCustoService
from app.services.fornecedor_service import FornecedorService
from app.services.pagamento_service import PagamentoService
from app.services.rateio_service import RateioService
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


def ratear(
    db: Session, titulo: TituloPagar, valor: str, centro: CentroCusto | None = None
) -> RateioTitulo:
    centro = centro or criar_centro_custo(db)
    return RateioService(db).adicionar(
        titulo.id, RateioCreate(centro_custo_id=centro.id, valor=Decimal(valor))
    )


def criar_titulo_aprovado(db: Session, *, valor: str = "1000.00", **kwargs) -> TituloPagar:
    """Título com rateio de 100% em um centro de custo, já aprovado."""
    titulo = criar_titulo(db, valor=valor, **kwargs)
    ratear(db, titulo, valor)
    return TituloService(db).aprovar(titulo.id)


def pagar(db: Session, titulo: TituloPagar, valor: str, data: date | None = None) -> Pagamento:
    return PagamentoService(db).registrar(
        titulo.id,
        PagamentoCreate(data_pagamento=data or titulo.data_emissao, valor=Decimal(valor)),
    )
