"""Fixtures de test.

Los tests unitarios (lógica pura) no necesitan base de datos. Los de integración
levantan un PostgreSQL efímero con testcontainers, aplican las migraciones de
Alembic *desde cero* (igual que en producción) y siembran datos sintéticos.
Celery corre en modo eager y el storage es un doble en memoria: ningún test
depende de servicios externos ni usa datos reales del SSC.
"""

import os
from collections.abc import Iterator
from typing import Any

import pytest


@pytest.fixture(scope="session")
def pg_url() -> Iterator[str]:
    """Levanta Postgres efímero, corre migraciones y devuelve su URL (psycopg v3)."""
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as container:
        url = container.get_connection_url(driver="psycopg")

        os.environ["POWERAI_DATABASE_URL"] = url
        os.environ["POWERAI_ENTORNO"] = "test"
        os.environ["POWERAI_CELERY_EAGER"] = "true"

        from app.config import get_settings

        get_settings.cache_clear()

        from alembic import command
        from alembic.config import Config

        command.upgrade(Config("alembic.ini"), "head")

        yield url


@pytest.fixture(scope="session")
def engine(pg_url: str) -> Iterator[Any]:
    from sqlalchemy import create_engine

    eng = create_engine(pg_url, future=True)
    yield eng
    eng.dispose()


@pytest.fixture
def db_session(engine: Any) -> Iterator[Any]:
    """Sesión para sembrar y hacer aserciones; limpia las tablas al terminar."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE usuario, plantilla_reporte, carga_archivo CASCADE"))


@pytest.fixture(autouse=True)
def almacen_memoria() -> Iterator[Any]:
    """Inyecta un almacén en memoria global; ningún test toca Azure Blob."""
    from app.storage import set_almacen
    from app.storage.memoria import MemoriaAlmacen

    almacen = MemoriaAlmacen()
    set_almacen(almacen)
    yield almacen
    set_almacen(None)


@pytest.fixture
def client(engine: Any) -> Iterator[Any]:
    """TestClient con get_db entregando una sesión fresca por request."""
    from app.db import get_db
    from app.main import create_app
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    fabrica = sessionmaker(bind=engine, expire_on_commit=False)

    def _get_db() -> Iterator[Any]:
        s = fabrica()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_usuarios(db_session: Any) -> Any:
    """Siembra los usuarios de desarrollo en la base del test."""
    from app.scripts.seed_dev import sembrar

    sembrar(db_session)
    return db_session


@pytest.fixture
def seed_plantillas(db_session: Any) -> Any:
    """Siembra las plantillas OTC en la base del test."""
    from app.scripts.seed_plantillas import sembrar_plantillas

    sembrar_plantillas(db_session)
    return db_session
