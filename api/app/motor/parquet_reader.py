"""Abstracción de lectura de Parquet para el motor DuckDB.

En producción, DuckDB lee los Parquet DIRECTAMENTE de Azure Blob vía la extensión
``azure`` (Azurite en dev, mismo path que prod). La abstracción ``ParquetReader``
existe para poder añadir un cache local más adelante sin tocar el motor; por ahora
no hay cache.
"""

from abc import ABC, abstractmethod

import duckdb

from app.config import get_settings


class ParquetReader(ABC):
    """Prepara una conexión DuckDB y resuelve URIs legibles de Parquet."""

    @abstractmethod
    def preparar(self, con: duckdb.DuckDBPyConnection) -> None:
        """Instala/carga extensiones y credenciales necesarias en la conexión."""

    @abstractmethod
    def uri(self, contenedor: str, ruta: str) -> str:
        """Devuelve un URI que DuckDB puede leer con ``read_parquet``."""


class AzureBlobParquetReader(ParquetReader):
    """Lee Parquet directo de Azure Blob (Azurite en dev) con la extensión azure."""

    def __init__(self, connection_string: str) -> None:
        self._connection_string = connection_string

    def preparar(self, con: duckdb.DuckDBPyConnection) -> None:
        con.execute("INSTALL azure; LOAD azure;")
        # El secret se parametriza para no interpolar la cadena en el SQL.
        con.execute(
            "CREATE OR REPLACE SECRET az (TYPE azure, CONNECTION_STRING ?)",
            [self._connection_string],
        )

    def uri(self, contenedor: str, ruta: str) -> str:
        return f"azure://{contenedor}/{ruta}"


_reader: ParquetReader | None = None


def set_parquet_reader(reader: ParquetReader | None) -> None:
    """Fija (o limpia) el reader global. Usado por los tests."""
    global _reader
    _reader = reader


def get_parquet_reader() -> ParquetReader:
    """Devuelve el reader configurado, construyéndolo de forma perezosa."""
    global _reader
    if _reader is None:
        _reader = AzureBlobParquetReader(get_settings().blob_connection_string)
    return _reader
