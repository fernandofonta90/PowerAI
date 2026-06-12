"""Capa de almacenamiento de objetos (Azure Blob vía SDK; Azurite en dev)."""

from app.storage.base import (
    CONTENEDOR_DATASETS,
    CONTENEDOR_ORIGINALES,
    AlmacenObjetos,
)
from app.storage.provider import get_almacen, set_almacen

__all__ = [
    "AlmacenObjetos",
    "CONTENEDOR_ORIGINALES",
    "CONTENEDOR_DATASETS",
    "get_almacen",
    "set_almacen",
]
