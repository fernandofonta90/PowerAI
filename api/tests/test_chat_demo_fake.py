"""El FakeProvider sin guion (modo demo) ejercita el flujo completo: ejecuta una
consulta y responde con datos + citación. Es lo que ve la demo y el E2E."""

from typing import Any

import pytest
from app.ia.fake import FakeProvider
from app.ia.proveedor import set_llm_provider

pytestmark = pytest.mark.integration

UPLOADER_MX = "uploader.mx@powerai.dev"


def test_demo_fake_responde_con_datos_y_citacion(
    client: Any, crear_carga: Any, reader_local: Any, seed_usuarios: Any, seed_vistas: Any
) -> None:
    crear_carga(pais="MX", filas=3)
    set_llm_provider(FakeProvider())  # modo demo (sin guion)

    conv = client.post("/conversaciones", json={}, headers={"X-Mock-User": UPLOADER_MX}).json()
    resp = client.post(
        f"/conversaciones/{conv['id']}/mensajes",
        json={"pregunta": "¿Cómo está la cartera?"},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    # Ejecutó la consulta de demo (saldo por cliente) → datos + citación con fuentes.
    assert cuerpo["datos_tabulares"] is not None
    assert cuerpo["datos_tabulares"]["columnas"] == ["cliente", "saldo"]
    assert len(cuerpo["citacion"]["fuentes"]) == 1
    assert "ar_abiertas" in cuerpo["citacion"]["vistas_usadas"]
    # Registro de consumo de tokens (insumo del control de costos).
    assert cuerpo["uso"]["entrada"] > 0
    assert cuerpo["uso"]["salida"] > 0
