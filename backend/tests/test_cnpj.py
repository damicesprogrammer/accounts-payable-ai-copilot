import pytest

from app.core import cnpj


@pytest.mark.parametrize("valor", ["11.222.333/0001-81", "11222333000181"])
def test_cnpj_valido(valor):
    assert cnpj.is_valido(valor)


@pytest.mark.parametrize(
    "valor",
    ["11.222.333/0001-82", "11111111111111", "123", "", "abcdefghijklmn"],
)
def test_cnpj_invalido(valor):
    assert not cnpj.is_valido(valor)


def test_cnpj_gerado_e_valido():
    assert all(cnpj.is_valido(cnpj.gerar(n)) for n in range(1, 100))
