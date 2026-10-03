"""Validação de CNPJ (dígitos verificadores, módulo 11)."""

import re

_PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_PESOS_DV2 = [6, *_PESOS_DV1]


def _digito(numeros: str, pesos: list[int]) -> str:
    resto = sum(int(n) * p for n, p in zip(numeros, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def normalizar(cnpj: str) -> str:
    """Remove pontuação: '12.345.678/0001-95' -> '12345678000195'."""
    return re.sub(r"\D", "", cnpj)


def is_valido(cnpj: str) -> bool:
    digitos = normalizar(cnpj)
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False
    dv1 = _digito(digitos[:12], _PESOS_DV1)
    dv2 = _digito(digitos[:12] + dv1, _PESOS_DV2)
    return digitos[12:] == dv1 + dv2


def gerar(base: int) -> str:
    """Gera um CNPJ válido e determinístico a partir de um inteiro (dados sintéticos)."""
    raiz = f"{base:08d}0001"
    dv1 = _digito(raiz, _PESOS_DV1)
    dv2 = _digito(raiz + dv1, _PESOS_DV2)
    return raiz + dv1 + dv2
