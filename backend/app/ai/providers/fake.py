import re
import zlib

from pydantic import BaseModel, ValidationError

from app.ai.contracts import ChatMessage, LLMResponse, ToolDefinition
from app.ai.exceptions import LLMStructuredOutputError
from app.models import EMBEDDING_DIM

Roteiro = LLMResponse | str | Exception


class FakeLLMProvider:
    """Provider para testes: sem rede, sem tokens, sem API key.

    Recebe um roteiro de respostas, devolvidas na ordem:
    - str          → resposta textual (ou JSON bruto, em generate_structured)
    - LLMResponse  → resposta completa, ex.: com tool calls
    - Exception    → é lançada (simula erro ou timeout do provider)

    Registra o que recebeu em `chamadas`, para os testes inspecionarem.
    """

    name = "fake"

    def __init__(self, roteiro: list[Roteiro]) -> None:
        self._roteiro = list(roteiro)
        self.chamadas: list[dict] = []

    def generate(
        self, messages: list[ChatMessage], *, tools: list[ToolDefinition] | None = None
    ) -> LLMResponse:
        self.chamadas.append({"messages": messages, "tools": tools})
        resposta = self._proxima()
        if isinstance(resposta, str):
            return LLMResponse(content=resposta, model="fake", finish_reason="stop")
        return resposta

    def generate_structured[T: BaseModel](
        self, messages: list[ChatMessage], response_model: type[T]
    ) -> T:
        self.chamadas.append({"messages": messages, "response_model": response_model})
        resposta = self._proxima()
        bruto = resposta if isinstance(resposta, str) else (resposta.content or "")
        try:
            return response_model.model_validate_json(bruto)
        except ValidationError as exc:
            raise LLMStructuredOutputError(
                f"Resposta incompatível com {response_model.__name__} "
                f"({exc.error_count()} erro(s) de validação)."
            ) from exc

    def _proxima(self) -> LLMResponse | str:
        if not self._roteiro:
            raise AssertionError("FakeLLMProvider: roteiro de respostas esgotado.")
        resposta = self._roteiro.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


class FakeEmbeddingProvider:
    """Embeddings determinísticos para testes: sem rede, sem tokens, sem API key.

    Não simula semântica. Cada palavra incrementa uma posição fixa do vetor
    (crc32 da palavra), então textos que compartilham palavras ficam próximos
    na distância de cosseno — o suficiente para testes previsíveis de busca.

    `erro`: se informado, é lançado em toda chamada (simula falha do provider).
    """

    name = "fake"

    def __init__(self, *, erro: Exception | None = None) -> None:
        self._erro = erro
        self.chamadas: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.chamadas.append(list(texts))
        if self._erro:
            raise self._erro
        return [_vetor_bag_of_words(texto) for texto in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]


def _vetor_bag_of_words(texto: str) -> list[float]:
    vetor = [0.0] * EMBEDDING_DIM
    for palavra in re.findall(r"\w+", texto.lower()):
        vetor[zlib.crc32(palavra.encode()) % EMBEDDING_DIM] += 1.0
    if not any(vetor):
        vetor[0] = 1.0  # vetor nulo não tem distância de cosseno definida
    return vetor
