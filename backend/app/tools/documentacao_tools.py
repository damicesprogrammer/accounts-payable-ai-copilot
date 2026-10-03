"""Tool de busca na documentação (somente leitura).

Faz apenas o retrieval (pergunta → embedding → pgvector → chunks). Não chama o
LLM: quem decide como responder com os trechos é o modelo que pediu a tool.
"""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.orm import Session

from app.ai.contracts import EmbeddingProvider
from app.ai.providers import get_embedding_provider
from app.rag.service import RAGService
from app.tools.contracts import Tool


class BuscaDocumentacaoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ] = Field(description="Pergunta ou termos a buscar na documentação do AP Copilot.")


def search_documentation(embeddings: EmbeddingProvider | None = None) -> Tool:
    """Cria a tool. Sem `embeddings`, o provider configurado é criado só quando a
    tool é executada — a aplicação continua subindo sem API key."""

    def _handler(db: Session, args: BuscaDocumentacaoInput) -> list[dict[str, Any]]:
        provider = embeddings or get_embedding_provider()
        trechos = RAGService(db, provider).search(args.query)
        return [t.model_dump(mode="json") for t in trechos]

    return Tool(
        name="search_documentation",
        description=(
            "Busca trechos da documentação de regras do AP Copilot (títulos, rateios, "
            "pagamentos, estornos, erros de integração). Devolve source, section, content "
            "e score de cada trecho encontrado."
        ),
        input_model=BuscaDocumentacaoInput,
        handler=_handler,
    )
