"""Fixtures de test.

Los tests unitarios (lógica de autorización) no necesitan base de datos. Los
tests de integración levantan un PostgreSQL efímero con testcontainers, aplican
las migraciones de Alembic *desde cero* (igual que en producción) y siembran
datos sintéticos. No se usa ningún dato real del SSC.
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

        # env.py de Alembic toma la URL de la configuración (variable de entorno).
        os.environ["POWERAI_DATABASE_URL"] = url
        os.environ["POWERAI_ENTORNO"] = "test"

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
    """Sesión por test; limpia los datos al terminar para aislar cada caso."""
    from sqlalchemy import text
    from sqlalchemy.orm import sessionmaker

    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE usuario CASCADE"))


@pytest.fixture
def client(db_session: Any) -> Iterator[Any]:
    """TestClient con get_db apuntando a la sesión del test."""
    from app.db import get_db
    from app.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def seed_usuarios(db_session: Any) -> Any:
    """Siembra los usuarios de desarrollo en la base del test."""
    from app.scripts.seed_dev import sembrar

    sembrar(db_session)
    return db_session
