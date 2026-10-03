import pytest

from app.ai.contracts import ToolCall
from app.tools.registry import criar_registry_financeiro
from tests.factories import criar_fornecedor


@pytest.fixture
def registry():
    return criar_registry_financeiro()


def _executar(registry, db, **arguments):
    return registry.execute(ToolCall(id="c", name="get_fornecedores", arguments=arguments), db)


@pytest.fixture
def fornecedores(db):
    ativos = [criar_fornecedor(db), criar_fornecedor(db)]
    inativos = [criar_fornecedor(db, ativo=False)]
    return ativos, inativos


@pytest.mark.parametrize(
    ("arguments", "esperados"),
    [
        ({}, lambda ativos, inativos: ativos + inativos),
        ({"ativo": True}, lambda ativos, inativos: ativos),
        ({"ativo": False}, lambda ativos, inativos: inativos),
    ],
    ids=["todos", "ativos", "inativos"],
)
def test_get_fornecedores_filtra_e_conta_no_backend(
    registry, db, fornecedores, arguments, esperados
):
    ids_esperados = sorted(f.id for f in esperados(*fornecedores))

    resultado = _executar(registry, db, **arguments)

    data = resultado.data
    assert data["quantidade"] == len(ids_esperados)  # calculada pelo sistema, não pelo LLM
    assert sorted(f["id"] for f in data["fornecedores"]) == ids_esperados
    if "ativo" in arguments:
        assert {f["ativo"] for f in data["fornecedores"]} == {arguments["ativo"]}
    assert set(data["fornecedores"][0]) == {"id", "nome", "cnpj", "ativo"}


def test_get_fornecedores_quantidade_nao_e_truncada_pela_paginacao(registry, db):
    acima_do_limite_padrao = 51  # listar() pagina em 50 por padrão
    for _ in range(acima_do_limite_padrao):
        criar_fornecedor(db)

    resultado = _executar(registry, db)

    assert resultado.data["quantidade"] == acima_do_limite_padrao
    assert len(resultado.data["fornecedores"]) == acima_do_limite_padrao


@pytest.mark.parametrize("arguments", [{"ativo": "talvez"}, {"ativo": None, "cnpj": "1"}])
def test_get_fornecedores_recusa_argumentos_invalidos(registry, db, arguments):
    resultado = _executar(registry, db, **arguments)

    assert resultado.ok is False
    assert resultado.error.code == "ARGUMENTOS_INVALIDOS"
