"""Indexa a base de conhecimento (docs/*.md) no pgvector.

Requer OPENAI_API_KEY (e OPENAI_EMBEDDING_MODEL, com default). Consome tokens de embedding.

    python -m scripts.index_docs
    python -m scripts.index_docs --docs-dir outro/diretorio

Apaga e recria todos os chunks em uma única transação: se algo falhar, o índice
anterior é preservado.
"""

import argparse
from pathlib import Path

from app.ai.exceptions import LLMError
from app.ai.providers import get_embedding_provider
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.rag.chunking import carregar_chunks
from app.rag.service import RAGService

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Indexa docs/*.md no pgvector.")
    parser.add_argument("--docs-dir", type=Path, default=DOCS_DIR)
    args = parser.parse_args()
    configure_logging(get_settings().log_level)

    chunks = carregar_chunks(args.docs_dir)
    if not chunks:
        raise SystemExit(f"Nenhum chunk encontrado em {args.docs_dir}.")

    try:
        with SessionLocal() as db:
            total = RAGService(db, get_embedding_provider()).indexar(chunks)
    except LLMError as exc:
        raise SystemExit(f"Falha: {exc}") from None

    documentos = len({c.source for c in chunks})
    print(f"Indexados {total} chunks de {documentos} documentos.")


if __name__ == "__main__":
    main()
