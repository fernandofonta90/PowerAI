"""Tests de los endpoints del Experto (RBAC y separación estructural vía API)."""

from typing import Any

import pytest
from app.routers.expertos import ConfigExpertoIn

pytestmark = pytest.mark.integration

ADMIN = {"X-Mock-User": "admin.otc@powerai.dev"}
UPLOADER = {"X-Mock-User": "uploader.mx@powerai.dev"}


@pytest.fixture(autouse=True)
def _setup(seed_usuarios: Any, seed_experto: Any) -> None:
    """Usuarios y experto OTC activo sembrados."""


def test_get_experto_admin_ok(client: Any) -> None:
    resp = client.get("/torres/OTC/experto", headers=ADMIN)
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["activo"]["nombre"] == "Experto OTC"
    assert cuerpo["activo"]["estado"] == "activo"
    assert {v["nombre"] for v in cuerpo["vistas_torre"]} == {
        "ar_abiertas",
        "pagos_unapplied",
        "revenue_recon",
    }
    # Las garantías estructurales se exponen como fijas (transparencia).
    assert len(cuerpo["garantias_estructurales"]) >= 3


def test_get_experto_no_admin_es_403(client: Any) -> None:
    assert client.get("/torres/OTC/experto", headers=UPLOADER).status_code == 403


def test_admin_de_otc_no_configura_otra_torre(client: Any) -> None:
    # admin.otc es admin de OTC, no de PTP: no puede ver/editar el experto de PTP.
    assert client.get("/torres/PTP/experto", headers=ADMIN).status_code == 403


def test_guardar_borrador_con_fuente_ajena_es_400(client: Any) -> None:
    resp = client.put(
        "/torres/OTC/experto/borrador",
        headers=ADMIN,
        json={
            "nombre": "X",
            "identidad": "Soy el experto.",
            "instrucciones_formato": "",
            "fuentes": ["no_existe"],
        },
    )
    assert resp.status_code == 400


def test_guardar_borrador_ok(client: Any) -> None:
    resp = client.put(
        "/torres/OTC/experto/borrador",
        headers=ADMIN,
        json={
            "nombre": "Experto OTC editado",
            "identidad": "Soy el experto OTC.",
            "instrucciones_formato": "Sé conciso.",
            "fuentes": ["ar_abiertas"],
        },
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["estado"] == "borrador"
    assert cuerpo["fuentes"] == ["ar_abiertas"]


def test_activar_via_endpoint_respeta_el_gate_de_evals(client: Any, fake_llm: Any) -> None:
    # Provider con guion vacío: nunca contesta bien => evals por debajo del umbral.
    fake_llm([])
    resp = client.post(
        "/torres/OTC/experto/activar",
        headers=ADMIN,
        json={
            "nombre": "Experto roto",
            "identidad": "Responde lo que sea.",
            "instrucciones_formato": "",
            "fuentes": ["ar_abiertas"],
        },
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["activado"] is False
    assert cuerpo["reporte"] is not None and cuerpo["reporte"]["tasa"] < 0.95


def test_activar_no_admin_es_403(client: Any) -> None:
    resp = client.post(
        "/torres/OTC/experto/activar",
        headers=UPLOADER,
        json={"nombre": "X", "identidad": "Y", "instrucciones_formato": "", "fuentes": []},
    )
    assert resp.status_code == 403


def test_requiere_auth(client: Any) -> None:
    assert client.get("/torres/OTC/experto").status_code == 401


def test_schema_editable_no_expone_reglas_estructurales() -> None:
    # Barandal en el contrato: el admin SOLO puede editar estos 4 campos; no existe
    # ningún campo para tocar RLS, honestidad ni el gobierno del SQL.
    assert set(ConfigExpertoIn.model_fields) == {
        "nombre",
        "identidad",
        "instrucciones_formato",
        "fuentes",
    }
