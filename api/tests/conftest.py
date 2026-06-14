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
            conn.execute(
                text(
                    "TRUNCATE usuario, plantilla_reporte, carga_archivo, "
                    "vista_catalogo, bitacora_consulta, conversacion, mensaje, "
                    "mensaje_consulta CASCADE"
                )
            )


@pytest.fixture(autouse=True)
def _reset_llm() -> Iterator[None]:
    """Limpia el proveedor LLM global entre tests para evitar fugas de estado."""
    yield
    from app.ia.proveedor import set_llm_provider

    set_llm_provider(None)


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


@pytest.fixture
def seed_vistas(db_session: Any) -> Any:
    """Siembra plantillas y vistas del catálogo OTC."""
    from app.scripts.seed_plantillas import sembrar_plantillas
    from app.scripts.seed_vistas import sembrar_vistas

    sembrar_plantillas(db_session)
    sembrar_vistas(db_session)
    return db_session


@pytest.fixture
def crear_carga(db_session: Any, almacen_memoria: Any) -> Any:
    """Factory: crea una carga DISPONIBLE con su Parquet en el almacén en memoria."""
    import hashlib

    from app.domain.enums import EstadoCarga
    from app.ingesta.lector import leer_tabla
    from app.ingesta.normalizador import a_parquet
    from app.models.carga import CargaArchivo
    from app.models.plantilla import PlantillaReporte
    from app.scripts.muestras import generar_csv
    from app.services.rutas import ruta_parquet
    from app.storage import CONTENEDOR_DATASETS
    from sqlalchemy import select

    def _crear(
        *,
        codigo: str = "otc_ar_abiertas",
        pais: str = "MX",
        periodo: str = "2026-05",
        version: int = 1,
        filas: int = 3,
        contenido: bytes | None = None,
    ) -> Any:
        plantilla = db_session.scalar(
            select(PlantillaReporte).where(PlantillaReporte.codigo == codigo)
        )
        datos = contenido or generar_csv(
            plantilla.columnas, "pais", "periodo", pais, periodo, filas
        )
        parquet = a_parquet(leer_tabla(datos, "x.csv"), plantilla.columnas)
        ruta = ruta_parquet(plantilla.torre, codigo, pais, periodo, version)
        almacen_memoria.guardar(CONTENEDOR_DATASETS, ruta, parquet)
        h = hashlib.sha256(f"{codigo}{pais}{periodo}{version}".encode() + parquet).hexdigest()
        carga = CargaArchivo(
            plantilla_id=plantilla.id,
            torre=plantilla.torre,
            pais=pais,
            periodo=periodo,
            responsable_email="seed@powerai.dev",
            nombre_archivo_original="x.csv",
            hash_sha256=h,
            version=version,
            estado=EstadoCarga.DISPONIBLE,
            blob_path_original=f"orig/{ruta}",
            blob_path_parquet=ruta,
            filas=filas,
        )
        db_session.add(carga)
        db_session.commit()
        return carga

    return _crear


@pytest.fixture
def fake_llm() -> Iterator[Any]:
    """Inyecta un FakeProvider global con un guion dado. Devuelve un setter."""
    from app.ia.fake import FakeProvider
    from app.ia.proveedor import set_llm_provider

    def _set(guion: Any) -> Any:
        provider = FakeProvider(guion)
        set_llm_provider(provider)
        return provider

    yield _set
    set_llm_provider(None)


@pytest.fixture
def reader_local(almacen_memoria: Any, tmp_path: Any) -> Iterator[Any]:
    """ParquetReader de test: materializa los bytes del almacén en memoria a
    archivos locales y los entrega a DuckDB. Mismo contrato que el reader de
    Azure, de modo que el motor no cambia."""
    from app.motor.parquet_reader import ParquetReader, set_parquet_reader

    class LocalParquetReader(ParquetReader):
        def __init__(self) -> None:
            self._materializados: dict[tuple[str, str], str] = {}

        def preparar(self, con: Any) -> None:  # noqa: ANN401 - duck-typed en test
            pass

        def uri(self, contenedor: str, ruta: str) -> str:
            clave = (contenedor, ruta)
            if clave not in self._materializados:
                datos = almacen_memoria.leer(contenedor, ruta)
                destino = tmp_path / contenedor / ruta
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(datos)
                self._materializados[clave] = str(destino)
            return self._materializados[clave]

    reader = LocalParquetReader()
    set_parquet_reader(reader)
    yield reader
    set_parquet_reader(None)
