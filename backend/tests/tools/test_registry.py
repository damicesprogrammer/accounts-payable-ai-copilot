import pytest
from pydantic import BaseModel, ConfigDict

from app.ai.contracts import ToolCall
from app.core.exceptions import BusinessRuleError
from app.tools.contracts import Tool
from app.tools.registry import ToolRegistry


class NumeroInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numero: int


def _dobro(db, args: NumeroInput):
    return {"resultado": args.numero * 2}


def _regra(db, args: NumeroInput):
    raise BusinessRuleError("Título 1 está CANCELADO.", code="TITULO_CANCELADO")


def _quebra(db, args: NumeroInput):
    raise RuntimeError("detalhe interno: senha=123 em /app/segredo.py")


DOBRO = Tool("dobro", "Dobra um número.", NumeroInput, _dobro)


def _registry(*tools: Tool) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


def _call(name: str, **arguments) -> ToolCall:
    return ToolCall(id="call_1", name=name, arguments=arguments)


def test_registra_e_expoe_definicoes():
    registry = _registry(DOBRO)

    [definicao] = registry.definitions()

    assert registry.names == ["dobro"]
    assert definicao.name == "dobro"
    assert definicao.input_schema["properties"]["numero"]["type"] == "integer"


def test_nao_permite_registrar_o_mesmo_nome_duas_vezes():
    registry = _registry(DOBRO)

    with pytest.raises(ValueError):
        registry.register(DOBRO)


def test_executa_tool_registrada(db):
    resultado = _registry(DOBRO).execute(_call("dobro", numero=21), db)

    assert resultado.ok is True
    assert resultado.data == {"resultado": 42}


def test_recusa_tool_inexistente(db):
    resultado = _registry(DOBRO).execute(_call("executar_sql", sql="DROP TABLE x"), db)

    assert resultado.ok is False
    assert resultado.error.code == "TOOL_NAO_PERMITIDA"


@pytest.mark.parametrize(
    "arguments",
    [
        {},  # faltando
        {"numero": "vinte e um"},  # tipo errado
        {"numero": 1, "extra": "x"},  # campo não declarado
    ],
)
def test_valida_argumentos(db, arguments):
    resultado = _registry(DOBRO).execute(ToolCall(id="c", name="dobro", arguments=arguments), db)

    assert resultado.ok is False
    assert resultado.error.code == "ARGUMENTOS_INVALIDOS"


def test_converte_domain_error_preservando_o_codigo(db):
    registry = _registry(Tool("regra", "x", NumeroInput, _regra))

    resultado = registry.execute(_call("regra", numero=1), db)

    assert resultado.ok is False
    assert resultado.error.code == "TITULO_CANCELADO"
    assert resultado.error.message == "Título 1 está CANCELADO."


def test_erro_interno_nao_vaza_detalhes(db):
    registry = _registry(Tool("quebra", "x", NumeroInput, _quebra))

    resultado = registry.execute(_call("quebra", numero=1), db)

    assert resultado.error.code == "ERRO_INTERNO"
    serializado = resultado.model_dump_json()
    assert "senha" not in serializado
    assert "Traceback" not in serializado
    assert "segredo.py" not in serializado


def test_resultado_tem_formato_padrao(db):
    resultado = _registry(DOBRO).execute(_call("inexistente"), db)

    assert resultado.model_dump(mode="json") == {
        "ok": False,
        "data": None,
        "error": {
            "code": "TOOL_NAO_PERMITIDA",
            "message": "A tool 'inexistente' não está disponível.",
        },
    }
