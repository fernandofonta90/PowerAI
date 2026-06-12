"""Almacén de objetos en memoria (para tests y exploración local).

Implementa la misma interfaz que el almacén de Azure Blob; no toca el filesystem.
"""

from app.storage.base import AlmacenObjetos, ObjetoNoEncontrado


class MemoriaAlmacen(AlmacenObjetos):
    """Almacén en memoria respaldado por un diccionario."""

    def __init__(self) -> None:
        self._datos: dict[tuple[str, str], bytes] = {}

    def guardar(
        self, contenedor: str, ruta: str, datos: bytes, content_type: str | None = None
    ) -> None:
        clave = (contenedor, ruta)
        if clave in self._datos:
            raise FileExistsError(f"El objeto ya existe: {contenedor}/{ruta}")
        self._datos[clave] = datos

    def leer(self, contenedor: str, ruta: str) -> bytes:
        try:
            return self._datos[(contenedor, ruta)]
        except KeyError as exc:
            raise ObjetoNoEncontrado(f"{contenedor}/{ruta}") from exc

    def existe(self, contenedor: str, ruta: str) -> bool:
        return (contenedor, ruta) in self._datos
