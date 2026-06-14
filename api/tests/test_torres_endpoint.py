"""Tests del endpoint de preguntas sugeridas (chips del home)."""

from typing import Any

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _setup(seed_usuarios: Any, seed_vistas: Any) -> None:
    """Usuarios y catálogo sembrados."""


def test_sugeridas_otc(client: Any) -> None:
    resp = client.get(
        "/torres/OTC/preguntas-sugeridas", headers={"X-Mock-User": "uploader.mx@powerai.dev"}
    )
    assert resp.status_code == 200
    preguntas = resp.json()
    assert 3 <= len(preguntas) <= 4
    assert all(isinstance(p, str) and p for p in preguntas)


def test_sugeridas_torre_sin_acceso_es_403(client: Any) -> None:
    # uploader.mx solo tiene OTC: PTP debe negarse.
    resp = client.get(
        "/torres/PTP/preguntas-sugeridas", headers={"X-Mock-User": "uploader.mx@powerai.dev"}
    )
    assert resp.status_code == 403


def test_sugeridas_requiere_auth(client: Any) -> None:
    assert client.get("/torres/OTC/preguntas-sugeridas").status_code == 401
