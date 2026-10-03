from decimal import Decimal

import pytest
from pydantic import BaseModel

from app.ai.contracts import ChatMessage, LLMResponse, ToolCall
from app.ai.exceptions import LLMProviderError, LLMStructuredOutputError, LLMTimeoutError
from app.ai.providers.fake import FakeLLMProvider

PERGUNTA = [ChatMessage(role="user", content="Qual o saldo do título 1?")]


class Diagnostico(BaseModel):
    titulo_id: int
    problema: str
    saldo_pendente: Decimal


def test_resposta_textual():
    provider = FakeLLMProvider(["O saldo é 700,00."])

    resposta = provider.generate(PERGUNTA)

    assert resposta.content == "O saldo é 700,00."
    assert resposta.tool_calls == []


def test_tool_call():
    chamada = ToolCall(id="call_1", name="get_titulo", arguments={"titulo_id": 1})
    provider = FakeLLMProvider([LLMResponse(model="fake", tool_calls=[chamada])])

    resposta = provider.generate(PERGUNTA)

    assert resposta.tool_calls == [chamada]


def test_multiplas_tool_calls():
    chamadas = [
        ToolCall(id="call_1", name="get_titulo", arguments={"titulo_id": 1}),
        ToolCall(id="call_2", name="get_logs_titulo", arguments={"titulo_id": 1}),
    ]
    provider = FakeLLMProvider([LLMResponse(model="fake", tool_calls=chamadas)])

    resposta = provider.generate(PERGUNTA)

    assert [c.name for c in resposta.tool_calls] == ["get_titulo", "get_logs_titulo"]


def test_structured_output_valido():
    provider = FakeLLMProvider(
        ['{"titulo_id": 1, "problema": "rateio incompleto", "saldo_pendente": "700.00"}']
    )

    resultado = provider.generate_structured(PERGUNTA, Diagnostico)

    assert resultado == Diagnostico(
        titulo_id=1, problema="rateio incompleto", saldo_pendente=Decimal("700.00")
    )


@pytest.mark.parametrize(
    "bruto",
    [
        '{"titulo_id": "um", "problema": "x", "saldo_pendente": "1"}',  # tipo errado
        '{"titulo_id": 1}',  # campos faltando
        "não é JSON",
    ],
)
def test_structured_output_invalido_gera_erro_especifico(bruto):
    provider = FakeLLMProvider([bruto])

    with pytest.raises(LLMStructuredOutputError):
        provider.generate_structured(PERGUNTA, Diagnostico)


def test_erro_do_provider():
    provider = FakeLLMProvider([LLMProviderError("falha simulada")])

    with pytest.raises(LLMProviderError):
        provider.generate(PERGUNTA)


def test_timeout():
    provider = FakeLLMProvider([LLMTimeoutError("timeout simulado")])

    with pytest.raises(LLMTimeoutError):
        provider.generate(PERGUNTA)


def test_registra_o_que_recebeu():
    provider = FakeLLMProvider(["ok"])

    provider.generate(PERGUNTA, tools=[])

    assert provider.chamadas == [{"messages": PERGUNTA, "tools": []}]
