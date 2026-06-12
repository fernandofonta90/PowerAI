"""Tests del endpoint del motor de consulta y del catálogo de vistas."""

from typing import Any

import pytest

pytestmark = pytest.mark.integration

UPLOADER_MX = "uploader.mx@powerai.dev"
ADMIN = "admin.otc@powerai.dev"


@pytest.fixture(autouse=True)
def _setup(seed_usuarios: Any, seed_vistas: Any) -> None:
    """Usuarios, plantillas y vistas para todos los tests del módulo."""


def test_post_consulta_ok(client: Any, crear_carga: Any, reader_local: Any) -> None:
    crear_carga(pais="MX", filas=3)
    resp = client.post(
        "/consultas",
        json={"sql": "SELECT count(*) AS n FROM ar_abiertas"},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["filas"][0][0] == 3
    assert "ar_abiertas" in cuerpo["vistas_usadas"]


def test_post_consulta_respeta_rls(client: Any, crear_carga: Any, reader_local: Any) -> None:
    crear_carga(pais="MX", filas=3)
    crear_carga(pais="CO", filas=4)
    # El uploader de MX solo ve sus 3 filas, jamás las de CO.
    resp = client.post(
        "/consultas",
        json={"sql": "SELECT count(*) AS n FROM ar_abiertas"},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.json()["filas"][0][0] == 3


def test_post_sql_invalido_es_400(client: Any, reader_local: Any) -> None:
    resp = client.post(
        "/consultas",
        json={"sql": "SELECT * FROM no_existe"},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"]["motivo"] == "sql_invalido"


def test_post_consulta_requiere_auth(client: Any, reader_local: Any) -> None:
    resp = client.post("/consultas", json={"sql": "SELECT 1"})
    assert resp.status_code == 401


def test_get_vistas_lista_catalogo(client: Any) -> None:
    resp = client.get("/vistas", headers={"X-Mock-User": ADMIN})
    assert resp.status_code == 200
    nombres = {v["nombre"] for v in resp.json()}
    assert nombres == {"ar_abiertas", "pagos_unapplied", "revenue_recon"}
    # Las descripciones de columna están presentes (insumo del LLM en M4).
    ar = next(v for v in resp.json() if v["nombre"] == "ar_abiertas")
    assert any(c["nombre"] == "monto" for c in ar["columnas"])
