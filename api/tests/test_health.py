"""Tests del health check."""

import pytest
from app import __version__


def test_health_liveness() -> None:
    """Liveness no depende de la base: se prueba sin contenedor."""
    from app.main import create_app
    from fastapi.testclient import TestClient

    with TestClient(create_app()) as c:
        resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "version": __version__}


@pytest.mark.integration
def test_health_readiness_ok(client: object) -> None:
    """Readiness en verde con PostgreSQL accesible."""
    resp = client.get("/health/ready")  # type: ignore[attr-defined]
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "database": "ok"}
