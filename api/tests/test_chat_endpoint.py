"""Tests del endpoint del chat analítico (conversaciones y mensajes)."""

from typing import Any

import pytest
from app.ia.proveedor import LlamadaTool, RespuestaLLM
from app.scripts.seed_plantillas import PLANTILLAS_OTC

pytestmark = pytest.mark.integration

AR = PLANTILLAS_OTC[0]
UPLOADER_MX = "uploader.mx@powerai.dev"
CONSULTA_CO = "consulta.co@powerai.dev"


@pytest.fixture(autouse=True)
def _setup(seed_usuarios: Any, seed_vistas: Any) -> None:
    """Usuarios, plantillas y vistas para todos los tests del módulo."""


def _guion_respuesta() -> list[RespuestaLLM]:
    return [
        RespuestaLLM(
            tool_calls=[
                LlamadaTool(
                    id="1",
                    nombre="ejecutar_sql",
                    argumentos={"sql": "SELECT count(*) AS n FROM ar_abiertas"},
                )
            ]
        ),
        RespuestaLLM(contenido="Hay 3 facturas abiertas."),
    ]


def test_crear_conversacion(client: Any) -> None:
    resp = client.post(
        "/conversaciones", json={"titulo": "Cartera"}, headers={"X-Mock-User": UPLOADER_MX}
    )
    assert resp.status_code == 201
    assert resp.json()["titulo"] == "Cartera"


def test_enviar_mensaje_responde_con_citacion(
    client: Any, crear_carga: Any, reader_local: Any, fake_llm: Any
) -> None:
    crear_carga(pais="MX", filas=3)
    fake_llm(_guion_respuesta())

    conv = client.post("/conversaciones", json={}, headers={"X-Mock-User": UPLOADER_MX}).json()
    resp = client.post(
        f"/conversaciones/{conv['id']}/mensajes",
        json={"pregunta": "¿Cuántas facturas abiertas hay?"},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert "3 facturas" in cuerpo["texto"]
    assert cuerpo["datos_tabulares"]["filas"][0][0] == 3
    assert len(cuerpo["citacion"]["fuentes"]) == 1
    assert cuerpo["citacion"]["fuentes"][0]["frescura"] in (
        "al_dia",
        "advertencia",
        "vencido",
    )


def test_listar_e_historial(
    client: Any, crear_carga: Any, reader_local: Any, fake_llm: Any
) -> None:
    crear_carga(pais="MX", filas=3)
    fake_llm(_guion_respuesta())
    conv = client.post("/conversaciones", json={}, headers={"X-Mock-User": UPLOADER_MX}).json()
    client.post(
        f"/conversaciones/{conv['id']}/mensajes",
        json={"pregunta": "¿Cuántas?"},
        headers={"X-Mock-User": UPLOADER_MX},
    )

    lista = client.get("/conversaciones", headers={"X-Mock-User": UPLOADER_MX}).json()
    assert any(c["id"] == conv["id"] for c in lista)

    detalle = client.get(
        f"/conversaciones/{conv['id']}", headers={"X-Mock-User": UPLOADER_MX}
    ).json()
    roles = [m["rol"] for m in detalle["mensajes"]]
    assert roles == ["user", "assistant"]
    # El mensaje del asistente trae su citación persistida.
    assert detalle["mensajes"][1]["citacion"]["vistas_usadas"] == ["ar_abiertas"]


def test_conversacion_de_otro_usuario_es_404(client: Any) -> None:
    conv = client.post("/conversaciones", json={}, headers={"X-Mock-User": UPLOADER_MX}).json()
    resp = client.get(f"/conversaciones/{conv['id']}", headers={"X-Mock-User": CONSULTA_CO})
    assert resp.status_code == 404


def test_enviar_requiere_auth(client: Any) -> None:
    resp = client.post("/conversaciones", json={})
    assert resp.status_code == 401
