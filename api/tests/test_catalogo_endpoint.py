"""Tests del catálogo navegable de preguntas (M9).

Cubren el principio rector: el catálogo muestra TODAS las torres, pero solo las
preguntas ``activa`` de una torre accesible son ``ejecutable``; ninguna
``proximamente`` lo es jamás. Y el RBAC: un usuario sin la torre no puede ejecutar
sus preguntas aunque estén activas.
"""

from typing import Any

import pytest
from app.auth.schemas import Grant, UsuarioAutenticado
from app.domain.enums import Rol, Torre
from app.routers.catalogo import _construir_catalogo

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _setup(seed_usuarios: Any, seed_catalogo: Any) -> None:
    """Usuarios y catálogo sembrados desde el seed real."""


def _todas_las_preguntas(bloques: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p for b in bloques for c in b["categorias"] for p in c["preguntas"]]


def test_catalogo_completo_muestra_todas_las_torres(client: Any) -> None:
    resp = client.get("/catalogo/preguntas", headers={"X-Mock-User": "uploader.mx@powerai.dev"})
    assert resp.status_code == 200
    bloques = resp.json()
    torres = {b["torre"] for b in bloques}
    # Las 6 torres del seed (incluida "General"/transversales) para que el piloto se vea completo.
    assert {"OTC", "PTP", "RTR", "QCI", "HTR", "General"} <= torres


def test_otc_activas_ejecutables_proximamente_no(client: Any) -> None:
    resp = client.get("/torres/OTC/preguntas", headers={"X-Mock-User": "uploader.mx@powerai.dev"})
    assert resp.status_code == 200
    bloque = resp.json()
    assert bloque["torre"] == "OTC"
    assert bloque["estado_torre"] == "activa"
    preguntas = [p for c in bloque["categorias"] for p in c["preguntas"]]
    activas = [p for p in preguntas if p["estado"] == "activa"]
    proximas = [p for p in preguntas if p["estado"] == "proximamente"]
    assert activas, "OTC debe tener preguntas activas"
    assert all(p["ejecutable"] for p in activas)
    # OTC tiene preguntas 'proximamente' (Conciliaciones, Reservas) que NO son ejecutables.
    assert proximas
    assert all(not p["ejecutable"] for p in proximas)


def test_ninguna_proximamente_es_ejecutable_en_todo_el_catalogo(client: Any) -> None:
    resp = client.get("/catalogo/preguntas", headers={"X-Mock-User": "admin.otc@powerai.dev"})
    assert resp.status_code == 200
    preguntas = _todas_las_preguntas(resp.json())
    proximas = [p for p in preguntas if p["estado"] == "proximamente"]
    assert proximas, "el catálogo debe incluir preguntas 'proximamente'"
    # Principio rector: una pregunta 'proximamente' NUNCA es clicable/ejecutable.
    assert all(not p["ejecutable"] for p in proximas)


def test_rbac_usuario_sin_la_torre_no_puede_ejecutar(db_session: Any) -> None:
    """Un usuario sin acceso a OTC ve sus preguntas pero ninguna es ejecutable."""
    usuario = UsuarioAutenticado(
        email="solo.ptp@powerai.dev",
        nombre="Solo PTP",
        grants=[Grant(torre=Torre.PTP, pais="MX", rol=Rol.CONSULTA)],
    )
    bloques = _construir_catalogo(db_session, usuario, torre_clave="OTC")
    assert bloques
    preguntas = [p for c in bloques[0].categorias for p in c.preguntas]
    activas = [p for p in preguntas if p.estado == "activa"]
    assert activas, "OTC tiene activas en el seed"
    # Aunque estén activas, el usuario no tiene OTC → no ejecutables (RBAC).
    assert all(not p.ejecutable for p in activas)


def test_torre_desconocida_devuelve_404(client: Any) -> None:
    resp = client.get(
        "/torres/NOEXISTE/preguntas", headers={"X-Mock-User": "uploader.mx@powerai.dev"}
    )
    assert resp.status_code == 404


def test_catalogo_requiere_auth(client: Any) -> None:
    assert client.get("/catalogo/preguntas").status_code == 401
