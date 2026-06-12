"""Integración del motor con el reader de producción (Azure Blob vía Azurite).

Prueba que DuckDB lee los Parquet DIRECTAMENTE de Blob con la extensión azure y
que la RLS por construcción se mantiene con el reader real. El resto de los tests
del motor usan el reader local; este valida el cableado de producción.
"""

import hashlib
from collections.abc import Iterator
from typing import Any

import pytest

pytestmark = pytest.mark.integration

_AZURITE_KEY = (
    "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw=="
)


@pytest.fixture(scope="module")
def conn_azurite() -> Iterator[str]:
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    contenedor = (
        DockerContainer("mcr.microsoft.com/azure-storage/azurite:latest")
        .with_command("azurite-blob --blobHost 0.0.0.0 --blobPort 10000 --skipApiVersionCheck")
        .with_exposed_ports(10000)
    )
    with contenedor as c:
        wait_for_logs(c, "successfully listens", timeout=60)
        host = c.get_container_host_ip()
        puerto = c.get_exposed_port(10000)
        yield (
            "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
            f"AccountKey={_AZURITE_KEY};"
            f"BlobEndpoint=http://{host}:{puerto}/devstoreaccount1;"
        )


def _sembrar_carga_en_azure(db: Any, almacen: Any, *, pais: str, filas: int) -> None:
    from app.domain.enums import EstadoCarga
    from app.ingesta.lector import leer_tabla
    from app.ingesta.normalizador import a_parquet
    from app.models.carga import CargaArchivo
    from app.models.plantilla import PlantillaReporte
    from app.scripts.muestras import generar_csv
    from app.services.rutas import ruta_parquet
    from app.storage import CONTENEDOR_DATASETS
    from sqlalchemy import select

    plantilla = db.scalar(
        select(PlantillaReporte).where(PlantillaReporte.codigo == "otc_ar_abiertas")
    )
    datos = generar_csv(plantilla.columnas, "pais", "periodo", pais, "2026-05", filas)
    parquet = a_parquet(leer_tabla(datos, "x.csv"), plantilla.columnas)
    ruta = ruta_parquet(plantilla.torre, "otc_ar_abiertas", pais, "2026-05", 1)
    almacen.guardar(CONTENEDOR_DATASETS, ruta, parquet)
    db.add(
        CargaArchivo(
            plantilla_id=plantilla.id,
            torre=plantilla.torre,
            pais=pais,
            periodo="2026-05",
            responsable_email="seed@powerai.dev",
            nombre_archivo_original="x.csv",
            hash_sha256=hashlib.sha256(f"{pais}".encode() + parquet).hexdigest(),
            version=1,
            estado=EstadoCarga.DISPONIBLE,
            blob_path_original=f"orig/{ruta}",
            blob_path_parquet=ruta,
            filas=filas,
        )
    )
    db.commit()


def test_motor_lee_de_azure_y_respeta_rls(
    db_session: Any, conn_azurite: str, seed_vistas: Any
) -> None:
    from app.auth.schemas import Grant, UsuarioAutenticado
    from app.domain.enums import Rol, Torre
    from app.motor.motor import ejecutar_consulta
    from app.motor.parquet_reader import AzureBlobParquetReader, set_parquet_reader
    from app.storage import set_almacen
    from app.storage.azure_blob import AzureBlobAlmacen

    almacen = AzureBlobAlmacen(conn_azurite)
    set_almacen(almacen)
    set_parquet_reader(AzureBlobParquetReader(conn_azurite))
    try:
        _sembrar_carga_en_azure(db_session, almacen, pais="MX", filas=3)
        _sembrar_carga_en_azure(db_session, almacen, pais="CO", filas=4)

        mx = UsuarioAutenticado(
            email="uploader.mx@powerai.dev",
            nombre="MX",
            grants=[Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA)],
        )
        r = ejecutar_consulta(db_session, mx, "SELECT count(*) AS n FROM ar_abiertas")
        # Lee de Azure y solo ve MX (RLS), no las filas de CO.
        assert r.filas[0][0] == 3
    finally:
        set_parquet_reader(None)
        set_almacen(None)
