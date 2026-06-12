"""Integración del adaptador Azure Blob contra Azurite (testcontainer).

Prueba que el cableado real del SDK funciona (guardar/leer/existe e
inmutabilidad). El resto de los tests usan el doble en memoria; este valida que
la implementación de producción no se rompió.
"""

from collections.abc import Iterator

import pytest

pytestmark = pytest.mark.integration

# Clave pública y bien conocida del emulador Azurite (no es un secreto real).
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


def test_round_trip_y_inmutabilidad(conn_azurite: str) -> None:
    from app.storage.azure_blob import AzureBlobAlmacen
    from app.storage.base import CONTENEDOR_ORIGINALES, ObjetoNoEncontrado

    almacen = AzureBlobAlmacen(conn_azurite)
    ruta = "OTC/otc_ar_abiertas/MX/2026-05/v1/aging.csv"
    datos = b"pais,periodo\nMX,2026-05\n"

    assert not almacen.existe(CONTENEDOR_ORIGINALES, ruta)
    almacen.guardar(CONTENEDOR_ORIGINALES, ruta, datos)
    assert almacen.existe(CONTENEDOR_ORIGINALES, ruta)
    assert almacen.leer(CONTENEDOR_ORIGINALES, ruta) == datos

    # Inmutabilidad: no se puede sobrescribir.
    with pytest.raises(Exception):  # noqa: B017 - el SDK lanza ResourceExistsError
        almacen.guardar(CONTENEDOR_ORIGINALES, ruta, b"otro")

    # Lectura de objeto inexistente.
    with pytest.raises(ObjetoNoEncontrado):
        almacen.leer(CONTENEDOR_ORIGINALES, "no/existe.bin")
