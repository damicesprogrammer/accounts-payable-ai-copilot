"""Provider OpenAI (Chat Completions).

Único módulo que conhece a SDK da OpenAI: converte nossos contratos para o
formato da SDK e normaliza a resposta de volta para LLMResponse / ToolCall.
"""

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import openai
from pydantic import BaseModel, SecretStr, ValidationError

from app.ai.contracts import ChatMessage, LLMResponse, TokenUsage, ToolCall, ToolDefinition
from app.ai.exceptions import LLMProviderError, LLMStructuredOutputError, LLMTimeoutError

logger = logging.getLogger(__name__)


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        *,
        timeout: float = 30.0,
        reasoning_effort: str | None = None,
        client: openai.OpenAI | None = None,  # injetável nos testes (sem rede)
    ) -> None:
        self.model = model
        # Repassado só quando configurado: modelos sem raciocínio recusam o parâmetro.
        # Ex.: alguns modelos de raciocínio só aceitam tools neste endpoint com "none".
        self._opcoes: dict[str, Any] = (
            {"reasoning_effort": reasoning_effort} if reasoning_effort else {}
        )
        self._client = client or openai.OpenAI(
            api_key=api_key.get_secret_value(), timeout=timeout, max_retries=1
        )

    def generate(
        self, messages: list[ChatMessage], *, tools: list[ToolDefinition] | None = None
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": _mensagens(messages),
            **self._opcoes,
        }
        if tools:
            kwargs["tools"] = [_tool_openai(t) for t in tools]

        completion, duracao_ms = self._chamar(self._client.chat.completions.create, **kwargs)
        choice = completion.choices[0]
        resposta = LLMResponse(
            content=choice.message.content,
            tool_calls=[_tool_call(tc) for tc in choice.message.tool_calls or []],
            model=completion.model,
            finish_reason=choice.finish_reason,
            usage=_usage(completion),
        )
        self._log_sucesso(resposta, duracao_ms)
        return resposta

    def generate_structured[T: BaseModel](
        self, messages: list[ChatMessage], response_model: type[T]
    ) -> T:
        # `parse` gera o JSON Schema estrito a partir do modelo Pydantic e valida a resposta.
        completion, duracao_ms = self._chamar(
            self._client.chat.completions.parse,
            model=self.model,
            messages=_mensagens(messages),
            response_format=response_model,
            **self._opcoes,
        )
        choice = completion.choices[0]
        # Recusa ou ausência de objeto não é sucesso: verifica antes de registrar.
        if choice.message.refusal or choice.message.parsed is None:
            erro = LLMStructuredOutputError(
                f"O modelo não retornou um {response_model.__name__} válido."
            )
            self._log_falha(erro, duracao_ms)
            raise erro
        metadados = LLMResponse(
            model=completion.model, finish_reason=choice.finish_reason, usage=_usage(completion)
        )
        self._log_sucesso(metadados, duracao_ms)
        return choice.message.parsed

    # ------------------------------------------------------------------ apoio

    def _chamar(self, metodo: Callable[..., Any], **kwargs: Any) -> tuple[Any, int]:
        """Executa a chamada e devolve (resultado, duração em ms), traduzindo as
        exceções da SDK para as da camada de IA.

        As mensagens de erro não reaproveitam o texto do fornecedor: ele pode
        ecoar parte da API key ou do conteúdo enviado.
        """
        inicio = time.perf_counter()
        try:
            return metodo(**kwargs), _ms_desde(inicio)
        except openai.APITimeoutError as exc:
            self._log_falha(exc, _ms_desde(inicio))
            raise LLMTimeoutError("A OpenAI não respondeu dentro do tempo limite.") from None
        except openai.APIStatusError as exc:
            self._log_falha(exc, _ms_desde(inicio))
            raise LLMProviderError(
                f"A OpenAI recusou a chamada (HTTP {exc.status_code})."
            ) from None
        except (
            ValidationError,
            openai.LengthFinishReasonError,
            openai.ContentFilterFinishReasonError,
        ) as exc:
            self._log_falha(exc, _ms_desde(inicio))
            raise LLMStructuredOutputError(
                "A resposta da OpenAI não é compatível com o schema solicitado."
            ) from None
        except openai.OpenAIError as exc:
            self._log_falha(exc, _ms_desde(inicio))
            raise LLMProviderError(f"Falha na chamada à OpenAI ({type(exc).__name__}).") from None

    def _log_sucesso(self, resposta: LLMResponse, duracao_ms: int) -> None:
        # Prompts e respostas não são registrados: apenas metadados da chamada.
        logger.info(
            "Chamada LLM concluída",
            extra={
                "provider": self.name,
                "model": resposta.model,
                "duration_ms": duracao_ms,
                "input_tokens": resposta.usage.input_tokens if resposta.usage else None,
                "output_tokens": resposta.usage.output_tokens if resposta.usage else None,
                "finish_reason": resposta.finish_reason,
                "tool_calls": len(resposta.tool_calls),
            },
        )

    def _log_falha(self, exc: Exception, duracao_ms: int) -> None:
        logger.warning(
            "Chamada LLM falhou",
            extra={
                "provider": self.name,
                "model": self.model,
                "duration_ms": duracao_ms,
                "error_type": type(exc).__name__,
            },
        )


# ---------------------------------------------------------------------- conversões


def _ms_desde(inicio: float) -> int:
    return round((time.perf_counter() - inicio) * 1000)


def _mensagens(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    return [_mensagem(m) for m in messages]


def _mensagem(m: ChatMessage) -> dict[str, Any]:
    if m.role == "tool":
        return {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content or ""}
    mensagem: dict[str, Any] = {"role": m.role, "content": m.content}
    if m.tool_calls:
        mensagem["tool_calls"] = [
            {
                "id": tc.id,  # o mesmo id gerado pelo modelo: correlaciona pedido e resultado
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                },
            }
            for tc in m.tool_calls
        ]
    return mensagem


def _tool_openai(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.input_schema,
        },
    }


def _tool_call(tool_call: Any) -> ToolCall:
    if tool_call.type != "function":
        raise LLMProviderError(f"Tipo de tool call não suportado: {tool_call.type}.")
    try:
        argumentos = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        raise LLMProviderError(
            f"O modelo enviou argumentos que não são JSON para '{tool_call.function.name}'."
        ) from None
    if not isinstance(argumentos, dict):
        raise LLMProviderError(
            f"Os argumentos de '{tool_call.function.name}' não são um objeto JSON."
        )
    return ToolCall(id=tool_call.id, name=tool_call.function.name, arguments=argumentos)


def _usage(completion: Any) -> TokenUsage | None:
    if completion.usage is None:
        return None
    return TokenUsage(
        input_tokens=completion.usage.prompt_tokens,
        output_tokens=completion.usage.completion_tokens,
    )
