"""Smoke test MANUAL da integração real com a OpenAI (não faz parte do pytest).

Requer OPENAI_API_KEY e OPENAI_MODEL configurados. Consome tokens.

    python -m scripts.smoke_openai --titulo-id 4

Prova o fluxo da Fase 2, sem loop de agente:
    LLM real → solicita tool → ToolCall normalizada → ToolRegistry → service → resultado
"""

import argparse
import json

from app.ai.contracts import ChatMessage
from app.ai.exceptions import LLMError
from app.ai.providers import get_llm_provider
from app.core.db import SessionLocal
from app.tools.registry import criar_registry_financeiro


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test manual do OpenAIProvider.")
    parser.add_argument("--titulo-id", type=int, default=1)
    args = parser.parse_args()

    registry = criar_registry_financeiro()
    mensagens = [
        ChatMessage(
            role="system",
            content="Você é um assistente de contas a pagar. Consulte os dados pelas ferramentas.",
        ),
        ChatMessage(role="user", content=f"Qual é a situação do título {args.titulo_id}?"),
    ]

    try:
        resposta = get_llm_provider().generate(mensagens, tools=registry.definitions())
    except LLMError as exc:
        raise SystemExit(f"Falha: {exc}") from None

    print(f"modelo={resposta.model} finish_reason={resposta.finish_reason} usage={resposta.usage}")
    if not resposta.tool_calls:
        print(f"Sem tool calls. Resposta textual: {resposta.content}")
        return

    with SessionLocal() as db:
        for chamada in resposta.tool_calls:
            resultado = registry.execute(chamada, db)
            print(f"\n→ {chamada.name}({chamada.arguments})")
            print(json.dumps(resultado.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
