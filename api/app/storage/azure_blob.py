"""Almacén de objetos sobre Azure Blob Storage (Azurite en dev).

Crea el contenedor on-demand y sube los blobs sin sobrescribir (inmutabilidad).
"""

import contextlib

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from app.storage.base import AlmacenObjetos, ObjetoNoEncontrado


class AzureBlobAlmacen(AlmacenObjetos):
    """Implementación de AlmacenObjetos contra Azure Blob."""

    def __init__(self, connection_string: str) -> None:
        self._svc = BlobServiceClient.from_connection_string(connection_string)

    def _asegurar_contenedor(self, contenedor: str) -> None:
        with contextlib.suppress(ResourceExistsError):
            self._svc.create_container(contenedor)

    def guardar(
        self, contenedor: str, ruta: str, datos: bytes, content_type: str | None = None
    ) -> None:
        self._asegurar_contenedor(contenedor)
        blob = self._svc.get_blob_client(container=contenedor, blob=ruta)
        # overwrite=False: una carga es inmutable; los paths ya son versionados.
        blob.upload_blob(datos, overwrite=False)

    def leer(self, contenedor: str, ruta: str) -> bytes:
        blob = self._svc.get_blob_client(container=contenedor, blob=ruta)
        try:
            descarga = blob.download_blob()
        except ResourceNotFoundError as exc:
            raise ObjetoNoEncontrado(f"{contenedor}/{ruta}") from exc
        return descarga.readall()

    def existe(self, contenedor: str, ruta: str) -> bool:
        blob = self._svc.get_blob_client(container=contenedor, blob=ruta)
        return blob.exists()
