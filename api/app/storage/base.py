"""Interfaz de almacenamiento de objetos.

La lógica de negocio nunca toca el SDK de Azure directamente: depende de esta
interfaz. En prod/dev la implementación es Azure Blob (Azurite en dev); en tests
se usa un doble en memoria con la misma interfaz. Nunca filesystem local.
"""

from abc import ABC, abstractmethod

# Contenedores lógicos del storage de PowerAI.
CONTENEDOR_ORIGINALES = "originales"  # archivos cargados, inmutables y versionados
CONTENEDOR_DATASETS = "datasets"  # Parquet derivados


class ObjetoNoEncontrado(Exception):
    """El objeto solicitado no existe en el almacén."""


class AlmacenObjetos(ABC):
    """Contrato de un almacén de objetos binarios."""

    @abstractmethod
    def guardar(
        self, contenedor: str, ruta: str, datos: bytes, content_type: str | None = None
    ) -> None:
        """Guarda ``datos`` en ``contenedor/ruta``. No sobrescribe (inmutable)."""

    @abstractmethod
    def leer(self, contenedor: str, ruta: str) -> bytes:
        """Devuelve los bytes de ``contenedor/ruta`` o lanza ObjetoNoEncontrado."""

    @abstractmethod
    def existe(self, contenedor: str, ruta: str) -> bool:
        """Indica si existe ``contenedor/ruta``."""
