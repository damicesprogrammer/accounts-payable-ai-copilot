"""Smoke test MANUAL do RAG com a OpenAI real (não faz parte do pytest).

Requer OPENAI_API_KEY e OPENAI_MODEL configurados. Consome tokens.

    python -m scripts.smoke_rag
    python -m scripts.smoke_rag --pergunta "Posso cancelar um título pago?"
    python -m scripts.smoke_rag --sem-indexar      # reaproveita o índice atual

Prova o fluxo completo da Fase 3:
    docs → chunks → embeddings → pgvector
    pergunta → embedding → similaridade no PostgreSQL → chunks → LLM → resposta + fontes
"""

import argparse

from app.ai.exceptions import LLMError
from app.ai.providers import get_embedding_provider, get_llm_provider
from app.core.db import SessionLocal
from app.rag.chunking import carregar_chunks
from app.rag.service import RAGService
from scripts.index_docs import DOCS_DIR

PERGUNTA = "O que acontece quando um pagamento de um título pago é estornado?"


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test manual do RAG.")
    parser.add_argument("--pergunta", default=PERGUNTA)
    parser.add_argument("--sem-indexar", action="store_true")
    args = parser.parse_args()

    try:
        with SessionLocal() as db:
            service = RAGService(db, get_embedding_provider(), get_llm_provider())

            if not args.sem_indexar:
                chunks = carregar_chunks(DOCS_DIR)
                print(f"1. Indexados {service.indexar(chunks)} chunks.\n")

            print(f"2. Pergunta: {args.pergunta}\n")
            print("3. Chunks recuperados:")
            for t in service.search(args.pergunta):
                print(f"   {t.score:.4f}  {t.source} › {t.section}")

            resposta = service.answer(args.pergunta)
    except LLMError as exc:
        raise SystemExit(f"Falha: {exc}") from None

    print(f"\n4. Resposta:\n{resposta.answer}\n")
    print("5. Fontes:")
    for fonte in resposta.sources:
        print(f"   - {fonte.source} › {fonte.section}")
    if not resposta.sources:
        print("   (nenhuma)")


if __name__ == "__main__":
    main()
