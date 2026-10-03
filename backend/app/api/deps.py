"""Dependências compartilhadas pelas rotas."""

from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.common import ErrorResponse

DbSession = Annotated[Session, Depends(get_db)]


class Paginacao(BaseModel):
    limit: int
    offset: int


def paginacao(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Paginacao:
    return Paginacao(limit=limit, offset=offset)


PaginacaoParams = Annotated[Paginacao, Depends(paginacao)]

# Documenta no OpenAPI o formato padronizado de erro de domínio.
ERROS_404 = {404: {"model": ErrorResponse}}
ERROS_409 = {409: {"model": ErrorResponse}}
ERROS_422 = {422: {"model": ErrorResponse}}
