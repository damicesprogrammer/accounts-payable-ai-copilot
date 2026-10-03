"""Testes do OpenAIProvider sem rede: o cliente da SDK é substituído por um stub
que devolve objetos reais da SDK (ChatCompletion) ou lança exceções da SDK."""

import logging
from types import SimpleNamespace

import httpx
import openai
import pytest
from openai.types.chat import ChatCompletion
from pydantic import BaseModel, SecretStr, ValidationError

from app.ai.contracts import ChatMessage, ToolCall, ToolDefinition
from app.ai.exceptions import (
    LLMConfigurationError,
    LLMProviderError,
    LLMStructuredOutputError,
    LLMTimeoutError,
)
from app.ai.providers import get_llm_provider
from app.ai.providers.openai import OpenAIProvider
from app.core.config import Settings

API_KEY = "sk-test-SEGREDO-NAO-PODE-VAZAR"
PERGUNTA = [ChatMessage(role="user", content="Qual o status do título 7?")]
REQUEST = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
GET_TITULO = ToolDefinition(
    name="get_titulo",
    description="Consulta um título.",
    input_schema={"type": "object", "properties": {"titulo_id": {"type": "integer"}}},
)


class Diagnostico(BaseModel):
    titulo_id: int
    problema: str


class StubCompletions:
    def __init__(self, resultado):
        self.resultado = resultado
        self.kwargs: dict = {}

    def _responder(self, **kwargs):
        self.kwargs = kwargs
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado

    create = _responder
    parse = _responder


def _provider(resultado, **opcoes) -> tuple[OpenAIProvider, StubCompletions]:
    completions = StubCompletions(resultado)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return OpenAIProvider(SecretStr(API_KEY), "gpt-teste", client=client, **opcoes), completions


def _completion(message: dict, finish_reason: str = "stop") -> ChatCompletion:
    return ChatCompletion.model_validate(
        {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-teste-2026",
            "choices": [{"index": 0, "finish_reason": finish_reason, "message": message}],
            "usage": {"prompt_tokens": 42, "completion_tokens": 7, "total_tokens": 49},
        }
    )


def _tool_call_message(arguments: str) -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_abc",
                "type": "function",
                "function": {"name": "get_titulo", "arguments": arguments},
            }
        ],
    }


# ---------------------------------------------------------------- generate


def test_resposta_textual_e_metadados():
    provider, _ = _provider(_completion({"role": "assistant", "content": "Está APROVADO."}))

    resposta = provider.generate(PERGUNTA)

    assert resposta.content == "Está APROVADO."
    assert resposta.tool_calls == []
    assert resposta.model == "gpt-teste-2026"
    assert resposta.finish_reason == "stop"
    assert (resposta.usage.input_tokens, resposta.usage.output_tokens) == (42, 7)


def test_tool_definitions_sao_convertidas_para_o_formato_da_openai():
    provider, completions = _provider(_completion({"role": "assistant", "content": "ok"}))

    provider.generate(PERGUNTA, tools=[GET_TITULO])

    assert completions.kwargs["tools"] == [
        {
            "type": "function",
            "function": {
                "name": "get_titulo",
                "description": "Consulta um título.",
                "parameters": GET_TITULO.input_schema,
            },
        }
    ]
    assert completions.kwargs["messages"] == [
        {"role": "user", "content": "Qual o status do título 7?"}
    ]


def test_historico_com_tool_calls_e_resultados_e_convertido_para_a_openai():
    chamada = ToolCall(id="call_abc", name="get_titulo", arguments={"titulo_id": 7})
    historico = [
        *PERGUNTA,
        ChatMessage(role="assistant", tool_calls=[chamada]),
        ChatMessage(role="tool", tool_call_id="call_abc", content='{"ok": true}'),
    ]
    provider, completions = _provider(_completion({"role": "assistant", "content": "ok"}))

    provider.generate(historico, tools=[GET_TITULO])

    assert completions.kwargs["messages"][1:] == [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_abc",
                    "type": "function",
                    "function": {"name": "get_titulo", "arguments": '{"titulo_id": 7}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_abc", "content": '{"ok": true}'},
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"role": "tool", "content": "x"},  # resultado sem tool_call_id
        {"role": "user", "content": "x", "tool_call_id": "call_1"},
        {"role": "user", "tool_calls": [{"id": "c", "name": "get_titulo", "arguments": {}}]},
    ],
)
def test_mensagem_incoerente_com_o_role_e_recusada(kwargs):
    with pytest.raises(ValidationError):
        ChatMessage(**kwargs)


def test_tool_call_da_openai_e_normalizada_para_nosso_tool_call():
    provider, _ = _provider(
        _completion(_tool_call_message('{"titulo_id": 7}'), finish_reason="tool_calls")
    )

    resposta = provider.generate(PERGUNTA, tools=[GET_TITULO])

    assert resposta.finish_reason == "tool_calls"
    [chamada] = resposta.tool_calls
    assert (chamada.id, chamada.name, chamada.arguments) == (
        "call_abc",
        "get_titulo",
        {"titulo_id": 7},
    )


@pytest.mark.parametrize("arguments", ["{titulo_id: 7", "[7]"])
def test_argumentos_que_nao_sao_objeto_json_geram_erro(arguments):
    provider, _ = _provider(_completion(_tool_call_message(arguments), "tool_calls"))

    with pytest.raises(LLMProviderError):
        provider.generate(PERGUNTA, tools=[GET_TITULO])


def test_timeout_da_sdk_vira_llm_timeout_error():
    provider, _ = _provider(openai.APITimeoutError(request=REQUEST))

    with pytest.raises(LLMTimeoutError):
        provider.generate(PERGUNTA)


def test_erro_http_vira_llm_provider_error_sem_ecoar_a_mensagem_do_fornecedor():
    erro = openai.AuthenticationError(
        f"Incorrect API key provided: {API_KEY}",
        response=httpx.Response(401, request=REQUEST),
        body=None,
    )
    provider, _ = _provider(erro)

    with pytest.raises(LLMProviderError) as exc:
        provider.generate(PERGUNTA)

    assert "401" in str(exc.value)
    assert API_KEY not in str(exc.value)
    assert exc.value.__cause__ is None  # a exceção original (com a mensagem) não é encadeada


# ---------------------------------------------------------------- structured output


def _parsed(parsed, refusal=None):
    message = SimpleNamespace(parsed=parsed, refusal=refusal)
    return SimpleNamespace(
        model="gpt-teste-2026",
        usage=None,
        choices=[SimpleNamespace(message=message, finish_reason="stop")],
    )


def test_structured_output_valido():
    esperado = Diagnostico(titulo_id=7, problema="rateio incompleto")
    provider, completions = _provider(_parsed(esperado))

    assert provider.generate_structured(PERGUNTA, Diagnostico) == esperado
    assert completions.kwargs["response_format"] is Diagnostico


def test_structured_output_recusado_pelo_modelo():
    provider, _ = _provider(_parsed(None, refusal="Não posso ajudar."))

    with pytest.raises(LLMStructuredOutputError):
        provider.generate_structured(PERGUNTA, Diagnostico)


@pytest.mark.parametrize("refusal", ["Não posso ajudar.", None])
def test_structured_output_recusado_ou_vazio_nao_e_registrado_como_sucesso(caplog, refusal):
    caplog.set_level(logging.INFO, logger="app.ai.providers.openai")
    provider, _ = _provider(_parsed(None, refusal=refusal))

    with pytest.raises(LLMStructuredOutputError):
        provider.generate_structured(PERGUNTA, Diagnostico)

    [registro] = caplog.records
    assert registro.getMessage() == "Chamada LLM falhou"
    assert registro.error_type == "LLMStructuredOutputError"


def test_structured_output_invalido_gera_erro_especifico():
    try:
        Diagnostico.model_validate_json('{"titulo_id": "sete"}')
    except ValidationError as exc:
        erro_de_validacao = exc
    provider, _ = _provider(erro_de_validacao)

    with pytest.raises(LLMStructuredOutputError):
        provider.generate_structured(PERGUNTA, Diagnostico)


# ---------------------------------------------------------------- observabilidade e segredos


def test_log_registra_metadados_sem_prompt(caplog):
    caplog.set_level(logging.INFO, logger="app.ai.providers.openai")
    provider, _ = _provider(
        _completion(_tool_call_message('{"titulo_id": 7}'), finish_reason="tool_calls")
    )

    provider.generate(PERGUNTA, tools=[GET_TITULO])

    [registro] = caplog.records
    assert registro.provider == "openai"
    assert registro.model == "gpt-teste-2026"
    assert (registro.input_tokens, registro.output_tokens) == (42, 7)
    assert registro.finish_reason == "tool_calls"
    assert registro.tool_calls == 1
    assert isinstance(registro.duration_ms, int)
    assert "título 7" not in caplog.text  # o prompt não é registrado


def test_api_key_nunca_aparece_em_logs_nem_em_repr(caplog):
    caplog.set_level(logging.DEBUG)
    settings = Settings(_env_file=None, openai_api_key=API_KEY, openai_model="gpt-teste")
    provider, _ = _provider(openai.APITimeoutError(request=REQUEST))

    with pytest.raises(LLMTimeoutError):
        provider.generate(PERGUNTA)

    todos_os_campos = " ".join(str(vars(r)) for r in caplog.records)
    assert API_KEY not in caplog.text
    assert API_KEY not in todos_os_campos
    assert API_KEY not in repr(settings)
    assert API_KEY not in str(settings.model_dump())


# ---------------------------------------------------------------- configuração


def test_sem_api_key_a_criacao_do_provider_falha_com_erro_claro():
    settings = Settings(_env_file=None, openai_api_key="", openai_model="gpt-teste")

    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
        get_llm_provider(settings)


def test_sem_modelo_a_criacao_do_provider_falha():
    settings = Settings(_env_file=None, openai_api_key=API_KEY, openai_model=None)

    with pytest.raises(LLMConfigurationError, match="OPENAI_MODEL"):
        get_llm_provider(settings)


def test_provider_nao_suportado():
    settings = Settings(_env_file=None, llm_provider="gemini")

    with pytest.raises(LLMConfigurationError, match="não suportado"):
        get_llm_provider(settings)


def test_provider_configurado_e_criado_sem_chamar_a_api():
    settings = Settings(_env_file=None, openai_api_key=API_KEY, openai_model="gpt-teste")

    provider = get_llm_provider(settings)

    assert isinstance(provider, OpenAIProvider)
    assert provider.model == "gpt-teste"


def test_api_financeira_funciona_sem_api_key(client):
    assert client.get("/health").status_code == 200
    assert client.get("/titulos").status_code == 200


# ---------------------------------------------------------------- reasoning_effort


def test_reasoning_effort_nao_e_enviado_quando_nao_configurado():
    provider, completions = _provider(_completion({"role": "assistant", "content": "ok"}))

    provider.generate(PERGUNTA, tools=[GET_TITULO])

    assert "reasoning_effort" not in completions.kwargs


def test_reasoning_effort_configurado_e_enviado_no_generate_e_no_structured():
    provider, completions = _provider(
        _completion({"role": "assistant", "content": "ok"}), reasoning_effort="none"
    )
    provider.generate(PERGUNTA, tools=[GET_TITULO])
    assert completions.kwargs["reasoning_effort"] == "none"

    provider, completions = _provider(
        _parsed(Diagnostico(titulo_id=1, problema="x")), reasoning_effort="low"
    )
    provider.generate_structured(PERGUNTA, Diagnostico)
    assert completions.kwargs["reasoning_effort"] == "low"


@pytest.mark.parametrize(("valor", "esperado"), [("none", {"reasoning_effort": "none"}), ("", {})])
def test_reasoning_effort_vem_da_configuracao(valor, esperado):
    settings = Settings(
        _env_file=None,
        openai_api_key=API_KEY,
        openai_model="gpt-teste",
        openai_reasoning_effort=valor,
    )

    assert get_llm_provider(settings)._opcoes == esperado
