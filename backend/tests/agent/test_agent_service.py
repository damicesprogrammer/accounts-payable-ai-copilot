"""Agent loop com FakeLLMProvider e FakeEmbeddingProvider: sem rede, roteiros determinísticos.

As tools são as reais (ToolRegistry → services → PostgreSQL de teste).
"""

import json
import logging
from datetime import date, timedelta

import pytest

from app.agent.service import MAX_ITERATIONS, PROMPT_SISTEMA, AgentService
from app.ai.contracts import ChatMessage, LLMResponse, ToolCall
from app.ai.exceptions import AgentIterationLimitError, LLMProviderError, LLMTimeoutError
from app.ai.providers.fake import FakeEmbeddingProvider, FakeLLMProvider
from app.rag.chunking import Chunk
from app.rag.service import RAGService
from app.schemas.agent import ToolUsada
from app.services.titulo_service import TituloService
from app.tools.registry import criar_registry_financeiro
from tests.factories import criar_titulo, criar_titulo_aprovado, pagar

DOC_CENTRO_INEXISTENTE = Chunk(
    "erros_integracao.md",
    "Centro de custo inexistente no ERP",
    "Cadastre o centro de custo no ERP de destino ou troque o rateio e reprocesse o título.",
)


def _pede(*chamadas: tuple[str, str, dict]) -> LLMResponse:
    """Resposta do modelo pedindo tools: (id, nome, argumentos)."""
    return LLMResponse(
        tool_calls=[ToolCall(id=i, name=n, arguments=a) for i, n, a in chamadas],
        model="fake",
        finish_reason="tool_calls",
    )


def _agente(db, roteiro) -> tuple[AgentService, FakeLLMProvider]:
    llm = FakeLLMProvider(roteiro)
    return AgentService(db, llm, criar_registry_financeiro(FakeEmbeddingProvider())), llm


def _resultado(mensagem: ChatMessage) -> dict:
    assert mensagem.role == "tool"
    return json.loads(mensagem.content)


# ---------------------------------------------------------------- caso 1: sem tool


def test_resposta_direta_sem_tools(db):
    agente, llm = _agente(db, ["Sou o Copilot do AP Copilot."])

    resposta = agente.run("Quem é você?")

    assert resposta.answer == "Sou o Copilot do AP Copilot."
    assert resposta.tools_used == []
    [chamada] = llm.chamadas
    sistema, usuario = chamada["messages"]
    assert (sistema.role, sistema.content) == ("system", PROMPT_SISTEMA)
    assert (usuario.role, usuario.content) == ("user", "Quem é você?")
    assert {t.name for t in chamada["tools"]} == {
        "get_titulo",
        "get_rateios_titulo",
        "get_pagamentos_titulo",
        "get_logs_titulo",
        "get_titulos_vencidos",
        "search_documentation",
    }


# ---------------------------------------------------------------- caso 2: uma tool


def test_uma_tool_resultado_volta_ao_modelo_com_o_mesmo_tool_call_id(db):
    titulo = criar_titulo(db)
    agente, llm = _agente(
        db,
        [_pede(("call_abc", "get_titulo", {"titulo_id": titulo.id})), "O título está PENDENTE."],
    )

    resposta = agente.run(f"Qual a situação do título {titulo.id}?")

    assert resposta.answer == "O título está PENDENTE."
    assert resposta.tools_used == [ToolUsada(name="get_titulo", ok=True)]
    assert len(llm.chamadas) == 2
    _, _, pedido, resultado = llm.chamadas[1]["messages"]
    assert pedido.role == "assistant"
    assert [tc.id for tc in pedido.tool_calls] == ["call_abc"]
    assert resultado.tool_call_id == "call_abc"  # correlação preservada, sem id novo
    dados = _resultado(resultado)
    assert dados["ok"] is True
    assert (dados["data"]["id"], dados["data"]["status"]) == (titulo.id, "PENDENTE")


# ---------------------------------------------------------------- caso 3: multi-step


def test_fluxo_multi_step_decidido_pelo_modelo(db):
    titulo = criar_titulo_aprovado(db)
    TituloService(db).registrar_erro_integracao(
        titulo.id, "Integração ERP rejeitou o título: centro de custo 1001 inexistente no ERP."
    )
    RAGService(db, FakeEmbeddingProvider()).indexar([DOC_CENTRO_INEXISTENTE])
    agente, llm = _agente(
        db,
        [
            _pede(("c1", "get_titulo", {"titulo_id": titulo.id})),
            _pede(("c2", "get_logs_titulo", {"titulo_id": titulo.id})),
            _pede(("c3", "search_documentation", {"query": "centro de custo inexistente no ERP"})),
            "O título está em ERRO porque o centro de custo 1001 não existe no ERP.",
        ],
    )

    resposta = agente.run(f"Por que o título {titulo.id} está com erro?")

    assert [t.name for t in resposta.tools_used] == [
        "get_titulo",
        "get_logs_titulo",
        "search_documentation",
    ]
    assert all(t.ok for t in resposta.tools_used)
    assert len(llm.chamadas) == 4
    # Cada chamada recebe o histórico completo; a última mensagem é o resultado anterior.
    ultimos = [c["messages"][-1] for c in llm.chamadas[1:]]
    assert [m.tool_call_id for m in ultimos] == ["c1", "c2", "c3"]
    assert _resultado(ultimos[0])["data"]["status"] == "ERRO"
    assert "inexistente no ERP" in ultimos[1].content
    [trecho] = _resultado(ultimos[2])["data"]
    assert (trecho["source"], trecho["section"]) == (
        DOC_CENTRO_INEXISTENTE.source,
        DOC_CENTRO_INEXISTENTE.section,
    )
    assert len(llm.chamadas[3]["messages"]) == 2 + 3 * 2  # system, user + 3 (pedido, resultado)


# ---------------------------------------------------------------- totais calculados pelo sistema


def test_titulos_vencidos_chegam_ao_modelo_com_totais_do_sistema(db):
    passado = date.today() - timedelta(days=30)
    parcial = criar_titulo_aprovado(
        db, valor="1000.00", emissao=passado, vencimento=date.today() - timedelta(days=2)
    )
    pagar(db, parcial, "250.00")
    criar_titulo(db, valor="99.99", emissao=passado, vencimento=date.today() - timedelta(days=1))
    agente, llm = _agente(db, [_pede(("c1", "get_titulos_vencidos", {})), "Há 2 títulos vencidos."])

    resposta = agente.run("Quais títulos estão vencidos?")

    assert resposta.tools_used == [ToolUsada(name="get_titulos_vencidos", ok=True)]
    dados = _resultado(llm.chamadas[1]["messages"][-1])["data"]
    # O modelo recebe os totais prontos: não precisa somar a lista.
    assert dados["quantidade"] == 2
    assert dados["valor_total_titulos"] == "1099.99"
    assert dados["saldo_pendente_total"] == "849.99"
    assert len(dados["titulos"]) == 2


# ---------------------------------------------------------------- caso 4: várias tools juntas


def test_varias_tools_na_mesma_resposta_executam_em_ordem_antes_da_proxima_chamada(db):
    titulo = criar_titulo_aprovado(db)
    agente, llm = _agente(
        db,
        [
            _pede(
                ("c1", "get_titulo", {"titulo_id": titulo.id}),
                ("c2", "get_rateios_titulo", {"titulo_id": titulo.id}),
            ),
            "Título aprovado e 100% rateado.",
        ],
    )

    resposta = agente.run("Resumo do título")

    assert [t.name for t in resposta.tools_used] == ["get_titulo", "get_rateios_titulo"]
    assert len(llm.chamadas) == 2
    _, _, pedido, r1, r2 = llm.chamadas[1]["messages"]
    assert [tc.id for tc in pedido.tool_calls] == ["c1", "c2"]  # um único assistant
    assert (r1.tool_call_id, r2.tool_call_id) == ("c1", "c2")
    assert _resultado(r1)["data"]["status"] == "APROVADO"
    assert _resultado(r2)["data"][0]["valor"] == "1000.00"


# ---------------------------------------------------------------- casos 5–7: erros de tool


def test_tool_inexistente_vira_resultado_de_erro_para_o_modelo(db):
    agente, llm = _agente(
        db,
        [_pede(("c1", "executar_sql", {"sql": "DELETE FROM titulos_pagar"})), "Não posso."],
    )

    resposta = agente.run("Apague tudo")

    assert resposta.answer == "Não posso."
    assert resposta.tools_used == [ToolUsada(name="executar_sql", ok=False)]
    resultado = _resultado(llm.chamadas[1]["messages"][-1])
    assert resultado["error"]["code"] == "TOOL_NAO_PERMITIDA"


def test_argumentos_invalidos_permitem_que_o_modelo_corrija_a_chamada(db):
    titulo = criar_titulo(db)
    agente, llm = _agente(
        db,
        [
            _pede(("c1", "get_titulo", {"titulo_id": "o título"})),
            _pede(("c2", "get_titulo", {"titulo_id": titulo.id})),
            "Corrigido: está PENDENTE.",
        ],
    )

    resposta = agente.run("Situação do título?")

    assert resposta.tools_used == [
        ToolUsada(name="get_titulo", ok=False),
        ToolUsada(name="get_titulo", ok=True),
    ]
    assert _resultado(llm.chamadas[1]["messages"][-1])["error"]["code"] == "ARGUMENTOS_INVALIDOS"
    assert _resultado(llm.chamadas[2]["messages"][-1])["ok"] is True


def test_titulo_inexistente_e_explicado_pelo_modelo(db):
    agente, llm = _agente(
        db,
        [_pede(("c1", "get_titulo", {"titulo_id": 999_999})), "O título 999999 não existe."],
    )

    resposta = agente.run("Situação do título 999999?")

    assert resposta.answer == "O título 999999 não existe."
    assert resposta.tools_used == [ToolUsada(name="get_titulo", ok=False)]
    erro = _resultado(llm.chamadas[1]["messages"][-1])["error"]
    assert erro["code"] == "TITULO_NAO_ENCONTRADO"


# ---------------------------------------------------------------- caso 8: limite


def test_limite_de_iteracoes_interrompe_o_loop(db, caplog):
    caplog.set_level(logging.INFO, logger="app.agent.service")
    titulo = criar_titulo(db)
    sempre_pede = [
        _pede((f"c{i}", "get_titulo", {"titulo_id": titulo.id})) for i in range(MAX_ITERATIONS + 3)
    ]
    agente, llm = _agente(db, sempre_pede)

    with pytest.raises(AgentIterationLimitError):
        agente.run("loop")

    assert len(llm.chamadas) == MAX_ITERATIONS  # não chama o LLM além do limite
    [registro] = [r for r in caplog.records if r.name == "app.agent.service"]
    assert registro.iteracoes == MAX_ITERATIONS
    # As tools da última resposta não são executadas: o modelo nunca veria o resultado.
    assert registro.tools == ["get_titulo"] * (MAX_ITERATIONS - 1)


# ---------------------------------------------------------------- caso 9: falha do provider


@pytest.mark.parametrize("posicao", [0, 1])
def test_falha_do_provider_interrompe_o_fluxo(db, posicao):
    titulo = criar_titulo(db)
    roteiro = [_pede(("c1", "get_titulo", {"titulo_id": titulo.id}))][:posicao]
    agente, _ = _agente(db, [*roteiro, LLMTimeoutError("timeout simulado")])

    with pytest.raises(LLMTimeoutError):
        agente.run("Situação?")


@pytest.mark.parametrize("conteudo", [None, "", "   "])
def test_resposta_final_sem_texto_gera_erro_controlado(db, conteudo):
    agente, _ = _agente(db, [LLMResponse(content=conteudo, model="fake")])

    with pytest.raises(LLMProviderError, match="sem uma resposta textual"):
        agente.run("Oi")


# ---------------------------------------------------------------- observabilidade


def test_log_registra_apenas_metadados(db, caplog):
    caplog.set_level(logging.INFO)
    titulo = criar_titulo(db, numero="NF-SIGILOSA")
    agente, _ = _agente(
        db,
        [
            _pede(
                ("c1", "get_titulo", {"titulo_id": titulo.id}),
                ("c2", "get_titulo", {"titulo_id": 999_999}),
            ),
            "RESPOSTA-FINAL-SIGILOSA",
        ],
    )

    agente.run("PERGUNTA-SIGILOSA")

    [registro] = [r for r in caplog.records if r.getMessage() == "Agente concluído"]
    assert registro.iteracoes == 2
    assert registro.tools == ["get_titulo", "get_titulo"]
    assert registro.tools_com_erro == 1
    assert isinstance(registro.duration_ms, int)
    todos = caplog.text + " ".join(str(vars(r)) for r in caplog.records)
    for sigiloso in ("PERGUNTA-SIGILOSA", "RESPOSTA-FINAL-SIGILOSA", "NF-SIGILOSA"):
        assert sigiloso not in todos
    assert "Você é o Copilot" not in todos  # o prompt não é registrado
