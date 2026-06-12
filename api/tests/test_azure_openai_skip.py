"""Test de integración del AzureOpenAIProvider — SKIP hasta tener credenciales.

Se activa solo si POWERAI_AZURE_OPENAI_API_KEY y POWERAI_AZURE_OPENAI_ENDPOINT
están presentes en el entorno. Valida el cableado real del SDK de Azure OpenAI.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    not (
        os.environ.get("POWERAI_AZURE_OPENAI_API_KEY")
        and os.environ.get("POWERAI_AZURE_OPENAI_ENDPOINT")
    ),
    reason="Requiere credenciales de Azure OpenAI",
)


def test_azure_openai_completa() -> None:
    from app.ia.azure_openai import AzureOpenAIProvider
    from app.ia.proveedor import MensajeChat

    provider = AzureOpenAIProvider()
    resp = provider.completar([MensajeChat(rol="user", contenido="Responde solo 'ok'.")], [])
    assert resp.contenido is not None
