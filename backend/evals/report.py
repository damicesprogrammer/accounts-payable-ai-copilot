"""Relatório dos evals: resumo no terminal e JSON opcional.

Não inclui API key, system prompt, resultados de tools nem conteúdo dos chunks.
"""

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

CATEGORIAS = ("agent", "finance", "safety", "rag")

NOTA_TOOL_INEXISTENTE = (
    "Tool inexistente pedida pelo modelo (ex.: executar_sql) → TOOL_NAO_PERMITIDA, nada executa: "
    "garantia determinística, coberta pelo pytest (tests/agent/test_seguranca_agente.py)."
)


@dataclass(frozen=True)
class Precos:
    """USD por 1M de tokens. Opcional: sem os dois preços, o custo não é estimado."""

    input_por_milhao: float | None = None
    output_por_milhao: float | None = None

    def custo(self, input_tokens: int, output_tokens: int) -> float | None:
        if self.input_por_milhao is None or self.output_por_milhao is None:
            return None
        return (
            input_tokens * self.input_por_milhao + output_tokens * self.output_por_milhao
        ) / 1_000_000


def moeda_br(valor: Decimal) -> str:
    """1234567.8 → "1.234.567,80" (formato da resposta em português)."""
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def totais(resultados: list[dict[str, Any]], precos: Precos) -> dict[str, Any]:
    soma = {
        campo: sum(r[campo] for r in resultados)
        for campo in (
            "llm_calls",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "embedding_tokens",
        )
    }
    return {
        "passed": sum(r["passed"] for r in resultados),
        "total": len(resultados),
        "duration_s": round(sum(r["duration_s"] for r in resultados), 2),
        **soma,
        "estimated_cost_usd": precos.custo(soma["input_tokens"], soma["output_tokens"]),
    }


def resumo(resultados: list[dict[str, Any]], precos: Precos) -> str:
    t = totais(resultados, precos)
    linhas = ["AP Copilot Evals", ""]
    for categoria in CATEGORIAS:
        doc = [r for r in resultados if r["category"] == categoria]
        if doc:
            linhas.append(f"{categoria.capitalize() + ':':<10}{_placar(doc)}")
    linhas += [
        "",
        f"{'Total:':<10}{t['passed']}/{t['total']} passed",
        f"{'Duration:':<10}{t['duration_s']}s",
        f"LLM calls: {t['llm_calls']}",
        f"Tokens:    input {t['input_tokens']} · output {t['output_tokens']} · "
        f"total {t['total_tokens']} · embeddings {t['embedding_tokens']}",
    ]
    if t["estimated_cost_usd"] is None:
        linhas.append("Estimated cost: not estimated (use --input-price and --output-price)")
    else:
        linhas.append(
            f"Estimated cost: ${t['estimated_cost_usd']:.4f} "
            "(chat tokens × configured prices; embeddings not included)"
        )

    rag = [r for r in resultados if r.get("top_chunks")]
    if rag:
        linhas += ["", "RAG retrieval (top 1):"]
        for r in rag:
            top = r["top_chunks"][0]
            linhas.append(f"  {r['id']:<30} {top['score']:.4f}  {top['source']} › {top['section']}")

    falhas = [r for r in resultados if not r["passed"]]
    if falhas:
        linhas += ["", "Failures:"]
        for r in falhas:
            linhas.append(f"  {r['id']} [{r['category']}]")
            linhas += [f"    - {motivo}" for motivo in r["failures"]]
            linhas.append(f"    tools: {', '.join(r['tools']) or '(nenhuma)'}")

    linhas += ["", NOTA_TOOL_INEXISTENTE]
    return "\n".join(linhas)


def salvar_json(caminho: Path, resultados: list[dict[str, Any]], precos: Precos) -> None:
    dados = {"summary": totais(resultados, precos), "cases": resultados}
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _placar(resultados: list[dict[str, Any]]) -> str:
    return f"{sum(r['passed'] for r in resultados)}/{len(resultados)} passed"
