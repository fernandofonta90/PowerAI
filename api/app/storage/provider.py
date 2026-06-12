"""Proveedor del almacén de objetos (singleton por proceso).

La factoría construye el almacén de Azure Blob a partir de la configuración. En
tests se inyecta un doble en memoria con ``set_almacen`` para no depender de un
servicio externo, manteniendo la misma interfaz.
"""

from app.config import get_settings
from app.storage.base import AlmacenObjetos

_almacen: AlmacenObjetos | None = None


def set_almacen(almacen: AlmacenObjetos | None) -> None:
    """Fija (o limpia) el almacén global. Usado por los tests."""
    global _almacen
    _almacen = almacen


def get_almacen() -> AlmacenObjetos:
    """Devuelve el almacén configurado, construyéndolo de forma perezosa."""
    global _almacen
    if _almacen is None:
        from app.storage.azure_blob import AzureBlobAlmacen

        _almacen = AzureBlobAlmacen(get_settings().blob_connection_string)
    return _almacen
