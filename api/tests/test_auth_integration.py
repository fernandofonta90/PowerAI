"""Tests de integración del mock auth y el RBAC torre × país (con Postgres)."""

import pytest

pytestmark = pytest.mark.integration


def test_me_sin_header_es_401(client: object, seed_usuarios: object) -> None:
    resp = client.get("/me")  # type: ignore[attr-defined]
    assert resp.status_code == 401


def test_me_usuario_desconocido_es_401(client: object, seed_usuarios: object) -> None:
    resp = client.get("/me", headers={"X-Mock-User": "nadie@powerai.dev"})  # type: ignore[attr-defined]
    assert resp.status_code == 401


def test_me_devuelve_matriz_de_acceso(client: object, seed_usuarios: object) -> None:
    resp = client.get(  # type: ignore[attr-defined]
        "/me", headers={"X-Mock-User": "multi.torre@powerai.dev"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "multi.torre@powerai.dev"
    torres = {t["torre"]: t["paises"] for t in data["torres"]}
    assert torres == {"OTC": ["MX"], "PTP": ["AR"]}


def test_ruta_protegida_concede_acceso_con_grant(client: object, seed_usuarios: object) -> None:
    resp = client.get(  # type: ignore[attr-defined]
        "/otc/aging",
        params={"pais": "MX"},
        headers={"X-Mock-User": "uploader.mx@powerai.dev"},
    )
    assert resp.status_code == 200
    assert resp.json()["pais"] == "MX"


def test_ruta_protegida_niega_pais_sin_grant(client: object, seed_usuarios: object) -> None:
    # El cargador de MX no tiene acceso a CO.
    resp = client.get(  # type: ignore[attr-defined]
        "/otc/aging",
        params={"pais": "CO"},
        headers={"X-Mock-User": "uploader.mx@powerai.dev"},
    )
    assert resp.status_code == 403


def test_admin_comodin_accede_a_cualquier_pais_de_la_torre(
    client: object, seed_usuarios: object
) -> None:
    resp = client.get(  # type: ignore[attr-defined]
        "/otc/aging",
        params={"pais": "PE"},
        headers={"X-Mock-User": "admin.otc@powerai.dev"},
    )
    assert resp.status_code == 200


def test_pais_invalido_es_422(client: object, seed_usuarios: object) -> None:
    resp = client.get(  # type: ignore[attr-defined]
        "/otc/aging",
        params={"pais": "ZZ"},
        headers={"X-Mock-User": "admin.otc@powerai.dev"},
    )
    assert resp.status_code == 422
