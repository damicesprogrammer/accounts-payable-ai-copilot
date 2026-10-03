import pytest

from app.agent.service import MAX_ITERATIONS, prompt_sistema
from app.ai.contracts import LLMResponse, ToolCall
from app.ai.exceptions import LLMTimeoutError
from app.ai.providers import get_embedding_provider, get_llm_provider
from app.ai.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from app.api.routes.ai import embedding_provider, llm_provider
from app.core.config import Settings
from app.main import app
from tests.factories import criar_titulo


def _usar(llm) -> None:
    app.dependency_overrides[embedding_provider] = lambda: FakeEmbeddingProvider()
    app.dependency_overrides[llm_provider] = lambda: llm


def _pede(id_: str, nome: str, **argumentos) -> LLMResponse:
    return LLMResponse(tool_calls=[ToolCall(id=id_, name=nome, arguments=argumentos)], model="f")


def test_copilot_responde_com_as_tools_executadas(client, db):
    titulo = criar_titulo(db)
    _usar(
        FakeLLMProvider(
            [
                _pede("c1", "get_titulo", titulo_id=titulo.id),
                _pede("c2", "search_documentation", query="aprovação"),
                "O título está PENDENTE e precisa de rateio de 100% para ser aprovado.",
            ]
        )
    )

    resposta = client.post("/ai/copilot", json={"question": f"Situação do título {titulo.id}?"})

    assert resposta.status_code == 200
    assert resposta.json() == {
        "answer": "O título está PENDENTE e precisa de rateio de 100% para ser aprovado.",
        "tools_used": [
            {"name": "get_titulo", "ok": True},
            {"name": "search_documentation", "ok": True},
        ],
    }


def test_copilot_nao_expoe_prompt_nem_historico(client, db):
    titulo = criar_titulo(db, numero="NF-INTERNO")
    _usar(FakeLLMProvider([_pede("c1", "get_titulo", titulo_id=titulo.id), "Resposta."]))

    resposta = client.post("/ai/copilot", json={"question": "Situação?"})

    assert set(resposta.json()) == {"answer", "tools_used"}
    for interno in ("Você é o Copilot", "NF-INTERNO", "tool_call_id", "c1"):
        assert interno not in resposta.text


def test_copilot_sem_configuracao_retorna_erro_tratado(client):
    sem_chave = Settings(_env_file=None, openai_api_key="", openai_model="")
    app.dependency_overrides[embedding_provider] = lambda: get_embedding_provider(sem_chave)
    app.dependency_overrides[llm_provider] = lambda: get_llm_provider(sem_chave)

    resposta = client.post("/ai/copilot", json={"question": "Situação do título 1?"})

    assert resposta.status_code == 503
    assert resposta.json()["error"]["code"] == "IA_NAO_CONFIGURADA"
    assert "Traceback" not in resposta.text


def test_copilot_limite_de_iteracoes_retorna_502(client, db):
    titulo = criar_titulo(db)
    _usar(
        FakeLLMProvider(
            [_pede(f"c{i}", "get_titulo", titulo_id=titulo.id) for i in range(MAX_ITERATIONS)]
        )
    )

    resposta = client.post("/ai/copilot", json={"question": "loop"})

    assert resposta.status_code == 502
    assert resposta.json()["error"]["code"] == "IA_LIMITE_ITERACOES"


def test_copilot_timeout_do_provider_retorna_504(client):
    _usar(FakeLLMProvider([LLMTimeoutError("A OpenAI não respondeu.")]))

    resposta = client.post("/ai/copilot", json={"question": "Situação?"})

    assert resposta.status_code == 504
    assert resposta.json()["error"]["code"] == "IA_TIMEOUT"


@pytest.mark.parametrize(
    "payload",
    [{}, {"question": ""}, {"question": "x" * 1001}, {"question": "ok", "conversation_id": "1"}],
)
def test_copilot_valida_a_pergunta(client, payload):
    _usar(FakeLLMProvider([]))

    assert client.post("/ai/copilot", json=payload).status_code == 422


def test_cada_requisicao_e_independente(client):
    """Sem memória: a segunda requisição não recebe o histórico da primeira."""
    llm = FakeLLMProvider(["Primeira.", "Segunda."])
    _usar(llm)

    client.post("/ai/copilot", json={"question": "PERGUNTA-UM"})
    client.post("/ai/copilot", json={"question": "PERGUNTA-DOIS"})

    segunda = llm.chamadas[1]["messages"]
    assert [m.role for m in segunda] == ["system", "user"]
    assert "PERGUNTA-UM" not in " ".join(m.content or "" for m in segunda)


@pytest.mark.parametrize(
    ("corpo", "idioma"),
    [({}, "pt-BR"), ({"language": "pt-BR"}, "pt-BR"), ({"language": "en-US"}, "en-US")],
)
def test_copilot_responde_no_idioma_escolhido(client, corpo, idioma):
    llm = FakeLLMProvider(["ok"])
    _usar(llm)

    resposta = client.post("/ai/copilot", json={"question": "Situação?", **corpo})

    assert resposta.status_code == 200
    # Sem `language`, o padrão é português (o mesmo prompt usado pelos evals).
    assert llm.chamadas[0]["messages"][0].content == prompt_sistema(idioma)


@pytest.mark.parametrize("language", ["es-ES", "en", "", None])
def test_copilot_recusa_idioma_nao_suportado(client, language):
    _usar(FakeLLMProvider(["ok"]))

    resposta = client.post("/ai/copilot", json={"question": "Situação?", "language": language})

    assert resposta.status_code == 422
