"""Tests unitarios del helper de reintentos (sin red)."""

import pytest
from app.ia.proveedor import ProveedorLLMError
from app.ia.reintentos import reintentar


class _Transitorio(Exception):
    pass


class _Fatal(Exception):
    pass


def _es_transitorio(e: Exception) -> bool:
    return isinstance(e, _Transitorio)


def test_reintenta_y_tiene_exito() -> None:
    intentos = {"n": 0}

    def fn() -> str:
        intentos["n"] += 1
        if intentos["n"] < 3:
            raise _Transitorio()
        return "ok"

    assert reintentar(fn, es_transitorio=_es_transitorio, dormir=lambda _: None) == "ok"
    assert intentos["n"] == 3


def test_agota_reintentos_lanza_proveedor_error() -> None:
    def fn() -> str:
        raise _Transitorio()

    with pytest.raises(ProveedorLLMError):
        reintentar(fn, es_transitorio=_es_transitorio, intentos=3, dormir=lambda _: None)


def test_error_no_transitorio_se_propaga_sin_reintento() -> None:
    intentos = {"n": 0}

    def fn() -> str:
        intentos["n"] += 1
        raise _Fatal()

    with pytest.raises(_Fatal):
        reintentar(fn, es_transitorio=_es_transitorio, dormir=lambda _: None)
    assert intentos["n"] == 1  # no reintentó


def test_provider_azure_sin_credenciales_falla_claro() -> None:
    from app.ia.azure_openai import AzureOpenAIProvider

    # En el entorno de test las variables de Azure están vacías.
    with pytest.raises(ProveedorLLMError) as exc:
        AzureOpenAIProvider()
    assert "Azure OpenAI" in str(exc.value)
