"""Tests de integración de dashboards: generación por IA, persistencia y render."""

from typing import Any

import pytest
from app.ia.proveedor import LlamadaTool, RespuestaLLM

pytestmark = pytest.mark.integration

UPLOADER_MX = "uploader.mx@powerai.dev"
CONSULTA_CO = "consulta.co@powerai.dev"

SPEC = {
    "version": 1,
    "titulo": "Cartera MX",
    "visuales": [
        {
            "tipo": "kpi",
            "titulo": "Total cartera",
            "sql": "SELECT sum(monto) AS total FROM ar_abiertas",
            "columna_valor": "total",
            "formato": "decimal",
        },
        {
            "tipo": "barras",
            "titulo": "Saldo por cliente",
            "sql": "SELECT cliente, sum(monto) AS saldo FROM ar_abiertas GROUP BY cliente",
            "eje_x": "cliente",
            "eje_y": "saldo",
            "formato": "decimal",
        },
    ],
}


@pytest.fixture(autouse=True)
def _datos(seed_usuarios: Any, seed_vistas: Any) -> None:
    """Usuarios y catálogo sembrados."""


def test_generar_dashboard_con_ia(
    client: Any, crear_carga: Any, reader_local: Any, fake_llm: Any
) -> None:
    crear_carga(pais="MX", filas=3)
    fake_llm(
        [
            RespuestaLLM(tool_calls=[LlamadaTool(id="1", nombre="listar_vistas", argumentos={})]),
            RespuestaLLM(tool_calls=[LlamadaTool(id="2", nombre="proponer_spec", argumentos=SPEC)]),
        ]
    )
    resp = client.post(
        "/dashboards/generar",
        json={"peticion": "Dame un tablero de la cartera de MX"},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["spec"] is not None
    assert len(cuerpo["spec"]["visuales"]) == 2


def test_generar_honesto_sin_spec(client: Any, reader_local: Any, fake_llm: Any) -> None:
    fake_llm([RespuestaLLM(contenido="No hay datos de costo para calcular rentabilidad.")])
    resp = client.post(
        "/dashboards/generar",
        json={"peticion": "Tablero de rentabilidad por cliente"},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["spec"] is None
    assert "rentabilidad" in cuerpo["mensaje"].lower() or "costo" in cuerpo["mensaje"].lower()


def test_crear_listar_obtener_render(client: Any, crear_carga: Any, reader_local: Any) -> None:
    crear_carga(pais="MX", filas=3)  # montos 1.50+2.50+3.50 = 7.50
    creado = client.post(
        "/dashboards",
        json={"nombre": "Cartera MX", "torre": "OTC", "spec": SPEC, "filtros": {"pais": "MX"}},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert creado.status_code == 201
    did = creado.json()["id"]

    lista = client.get("/dashboards", headers={"X-Mock-User": UPLOADER_MX}).json()
    assert any(d["id"] == did for d in lista)

    render = client.get(f"/dashboards/{did}", headers={"X-Mock-User": UPLOADER_MX}).json()
    assert render["titulo"] == "Cartera MX"
    kpi = next(v for v in render["visuales"] if v["tipo"] == "kpi")
    assert kpi["filas"][0][0] == "7.50"  # decimal exacto, re-ejecutado fresco
    barras = next(v for v in render["visuales"] if v["tipo"] == "barras")
    assert len(barras["filas"]) == 3


def test_crear_spec_invalida_422(client: Any, reader_local: Any) -> None:
    mala = {
        "version": 1,
        "titulo": "x",
        "visuales": [{"tipo": "kpi", "titulo": "x", "sql": "SELECT 1 AS a FROM ar_abiertas"}],
    }
    resp = client.post(
        "/dashboards",
        json={"nombre": "x", "torre": "OTC", "spec": mala},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["motivo"] == "spec_invalida"


def test_crear_torre_sin_acceso_403(client: Any) -> None:
    resp = client.post(
        "/dashboards",
        json={"nombre": "x", "torre": "PTP", "spec": SPEC},
        headers={"X-Mock-User": UPLOADER_MX},
    )
    assert resp.status_code == 403


def test_renombrar_y_eliminar(client: Any, crear_carga: Any, reader_local: Any) -> None:
    crear_carga(pais="MX", filas=3)
    did = client.post(
        "/dashboards",
        json={"nombre": "Viejo", "torre": "OTC", "spec": SPEC},
        headers={"X-Mock-User": UPLOADER_MX},
    ).json()["id"]

    ren = client.patch(
        f"/dashboards/{did}", json={"nombre": "Nuevo"}, headers={"X-Mock-User": UPLOADER_MX}
    )
    assert ren.json()["nombre"] == "Nuevo"

    assert (
        client.delete(f"/dashboards/{did}", headers={"X-Mock-User": UPLOADER_MX}).status_code == 204
    )
    assert client.get(f"/dashboards/{did}", headers={"X-Mock-User": UPLOADER_MX}).status_code == 404


def test_dashboard_de_otro_usuario_es_404(client: Any, crear_carga: Any, reader_local: Any) -> None:
    crear_carga(pais="MX", filas=3)
    did = client.post(
        "/dashboards",
        json={"nombre": "MX", "torre": "OTC", "spec": SPEC},
        headers={"X-Mock-User": UPLOADER_MX},
    ).json()["id"]
    resp = client.get(f"/dashboards/{did}", headers={"X-Mock-User": CONSULTA_CO})
    assert resp.status_code == 404
