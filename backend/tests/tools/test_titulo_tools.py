from datetime import date, timedelta

import pytest

from app.ai.contracts import ChatMessage, LLMResponse, ToolCall
from app.ai.providers.fake import FakeLLMProvider
from app.tools.registry import criar_registry_financeiro
from tests.factories import criar_centro_custo, criar_titulo, criar_titulo_aprovado, pagar, ratear

HOJE = date.today()


@pytest.fixture
def registry():
    return criar_registry_financeiro()


def _executar(registry, db, name: str, **arguments):
    return registry.execute(ToolCall(id="call_1", name=name, arguments=arguments), db)


def test_get_titulo_expoe_resumo_financeiro_serializavel(registry, db):
    titulo = criar_titulo_aprovado(db, valor="1000.00")
    pagar(db, titulo, "250.00")

    resultado = _executar(registry, db, "get_titulo", titulo_id=titulo.id)

    assert resultado.ok is True
    data = resultado.data
    assert data["id"] == titulo.id
    assert data["numero"] == titulo.numero
    assert data["fornecedor"]["nome"] == titulo.fornecedor.nome
    assert data["status"] == "APROVADO"
    # Valores monetários: strings com 2 casas, sem perda de precisão.
    assert (data["valor_total"], data["valor_rateado"]) == ("1000.00", "1000.00")
    assert (data["valor_pago"], data["saldo_pendente"]) == ("250.00", "750.00")
    assert data["vencido"] is False
    assert data["data_vencimento"] == titulo.data_vencimento.isoformat()
    assert {"created_at", "updated_at", "fornecedor_id"}.isdisjoint(data)


def test_get_titulo_inexistente_preserva_codigo_do_dominio(registry, db):
    resultado = _executar(registry, db, "get_titulo", titulo_id=999_999)

    assert resultado.ok is False
    assert resultado.error.code == "TITULO_NAO_ENCONTRADO"
    assert resultado.error.message == "Título 999999 não encontrado."


def test_get_rateios_titulo(registry, db):
    titulo = criar_titulo(db, valor="1000.00")
    ratear(db, titulo, "600.00", centro=criar_centro_custo(db, codigo="1001"))

    resultado = _executar(registry, db, "get_rateios_titulo", titulo_id=titulo.id)

    [rateio] = resultado.data
    assert rateio["valor"] == "600.00"
    assert rateio["centro_custo"]["codigo"] == "1001"


def test_get_pagamentos_titulo(registry, db):
    titulo = criar_titulo_aprovado(db, valor="100.00")
    pagar(db, titulo, "40.00")

    resultado = _executar(registry, db, "get_pagamentos_titulo", titulo_id=titulo.id)

    [pagamento] = resultado.data
    assert (pagamento["valor"], pagamento["status"]) == ("40.00", "CONFIRMADO")


def test_get_logs_titulo(registry, db):
    titulo = criar_titulo(db)

    resultado = _executar(registry, db, "get_logs_titulo", titulo_id=titulo.id)

    assert [log["tipo"] for log in resultado.data] == ["CRIACAO"]


def test_get_titulos_vencidos_devolve_totais_calculados_pelo_sistema(registry, db):
    passado = HOJE - timedelta(days=30)
    parcial = criar_titulo_aprovado(
        db, valor="1000.00", emissao=passado, vencimento=HOJE - timedelta(days=2)
    )
    pagar(db, parcial, "300.00")
    aberto = criar_titulo(db, valor="0.10", emissao=passado, vencimento=HOJE - timedelta(days=1))
    criar_titulo(db, emissao=HOJE, vencimento=HOJE + timedelta(days=10))

    resultado = _executar(registry, db, "get_titulos_vencidos")

    data = resultado.data
    assert data["quantidade"] == 2
    # Strings com 2 casas (Decimal serializado), nunca float.
    assert data["valor_total_titulos"] == "1000.10"
    assert data["saldo_pendente_total"] == "700.10"  # 700.00 pendente + 0.10
    assert [t["id"] for t in data["titulos"]] == [parcial.id, aberto.id]
    primeiro = data["titulos"][0]
    assert set(primeiro) == {
        "id",
        "numero",
        "fornecedor",
        "status",
        "data_vencimento",
        "valor_total",
        "valor_pago",
        "saldo_pendente",
    }
    assert (primeiro["valor_total"], primeiro["valor_pago"], primeiro["saldo_pendente"]) == (
        "1000.00",
        "300.00",
        "700.00",
    )
    assert primeiro["fornecedor"]["nome"] == parcial.fornecedor.nome


def test_fluxo_llm_tool_call_ate_o_service(registry, db):
    """LLM (fake) solicita get_titulo → ToolCall normalizada → registry → service."""

    titulo = criar_titulo(db, valor="300.00")
    provider = FakeLLMProvider(
        [
            LLMResponse(
                model="fake",
                finish_reason="tool_calls",
                tool_calls=[
                    ToolCall(id="call_1", name="get_titulo", arguments={"titulo_id": titulo.id})
                ],
            )
        ]
    )

    resposta = provider.generate(
        [ChatMessage(role="user", content=f"Qual o saldo do título {titulo.id}?")],
        tools=registry.definitions(),
    )
    [chamada] = resposta.tool_calls
    resultado = registry.execute(chamada, db)

    assert [t.name for t in provider.chamadas[0]["tools"]] == registry.names
    assert resultado.ok is True
    assert resultado.data["saldo_pendente"] == "300.00"
