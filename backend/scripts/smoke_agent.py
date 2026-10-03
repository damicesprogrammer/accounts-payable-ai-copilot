"""Smoke test MANUAL do agent loop com a OpenAI real (não faz parte do pytest).

Requer OPENAI_API_KEY e OPENAI_MODEL configurados, o seed aplicado e a
documentação indexada. Consome tokens.

    python -m scripts.seed
    python -m scripts.index_docs
    python -m scripts.smoke_agent
    python -m scripts.smoke_agent --pergunta "Quais títulos do fornecedor 3 estão vencidos?"

Para cada pergunta mostra as tools que o modelo decidiu usar e a resposta final.
"""

import argparse

from app.agent.service import AgentService
from app.ai.exceptions import LLMError
from app.ai.providers import get_embedding_provider, get_llm_provider
from app.core.db import SessionLocal
from app.services.titulo_service import TituloService
from app.tools.registry import criar_registry_financeiro


def _id_por_numero(db, numero: str) -> int:
    for titulo in TituloService(db).listar(limit=200):
        if titulo.numero == numero:
            return titulo.id
    raise SystemExit(f"Título {numero} não encontrado. Rode antes: python -m scripts.seed")


def _perguntas_padrao(db) -> list[str]:
    parcialmente_pago = _id_por_numero(db, "NF-9008")
    com_erro = _id_por_numero(db, "NF-9004")
    return [
        f"Qual é a situação do título {parcialmente_pago}?",
        f"Por que o título {com_erro} está com erro e como posso corrigir?",
        "Quais títulos estão vencidos?",
        "O que acontece quando um pagamento de um título pago é estornado?",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test manual do agente.")
    parser.add_argument("--pergunta", action="append", help="Pode ser repetido.")
    args = parser.parse_args()

    with SessionLocal() as db:
        perguntas = args.pergunta or _perguntas_padrao(db)
        try:
            registry = criar_registry_financeiro(get_embedding_provider())
            agente = AgentService(db, get_llm_provider(), registry)
            for pergunta in perguntas:
                resposta = agente.run(pergunta)
                tools = ", ".join(
                    f"{t.name}{'' if t.ok else ' (erro)'}" for t in resposta.tools_used
                )
                print(f"\n{'=' * 80}\nPergunta: {pergunta}")
                print(f"Tools:    {tools or '(nenhuma)'}")
                print(f"Resposta:\n{resposta.answer}")
        except LLMError as exc:
            raise SystemExit(f"Falha: {exc}") from None


if __name__ == "__main__":
    main()
