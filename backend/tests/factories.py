"""Construtores de dados de teste.

Criam entidades através dos services (e não inserindo direto no banco), para que
os dados de teste respeitem as mesmas regras de negócio da aplicação.
"""

from itertools import count

from sqlalchemy.orm import Session

from app.core import cnpj
from app.models import Fornecedor
from app.schemas.fornecedor import FornecedorCreate, FornecedorUpdate
from app.services.fornecedor_service import FornecedorService

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
