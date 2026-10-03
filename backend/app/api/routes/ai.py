from typing import Annotated

from fastapi import APIRouter, Depends

from app.agent.service import AgentService
from app.ai.contracts import EmbeddingProvider, LLMProvider
from app.ai.providers import get_embedding_provider, get_llm_provider
from app.api.deps import DbSession
from app.rag.service import RAGService
from app.schemas.agent import CopilotResponse
from app.schemas.common import ErrorResponse
from app.schemas.rag import PerguntaInput, RespostaRAG
from app.tools.registry import criar_registry_financeiro

router = APIRouter(prefix="/ai", tags=["ia"])


# Wrappers sem parâmetros: o FastAPI não deve tentar ler `settings` da requisição.
# Nos testes, são substituídos por providers fake via dependency_overrides.
def embedding_provider() -> EmbeddingProvider:
    return get_embedding_provider()


def llm_provider() -> LLMProvider:
    return get_llm_provider()


@router.post(
    "/ask",
    response_model=RespostaRAG,
    responses={code: {"model": ErrorResponse} for code in (502, 503, 504)},
)
def perguntar(
    dados: PerguntaInput,
    db: DbSession,
    embeddings: Annotated[EmbeddingProvider, Depends(embedding_provider)],
    llm: Annotated[LLMProvider, Depends(llm_provider)],
):
    """Responde perguntas sobre as regras do AP Copilot usando RAG sobre docs/*.md."""
    return RAGService(db, embeddings, llm).answer(dados.question)


@router.post(
    "/copilot",
    response_model=CopilotResponse,
    responses={code: {"model": ErrorResponse} for code in (502, 503, 504)},
)
def copilot(
    dados: PerguntaInput,
    db: DbSession,
    embeddings: Annotated[EmbeddingProvider, Depends(embedding_provider)],
    llm: Annotated[LLMProvider, Depends(llm_provider)],
):
    """Copilot com tools somente leitura. Cada requisição é independente (sem memória)."""
    return AgentService(db, llm, criar_registry_financeiro(embeddings)).run(dados.question)
