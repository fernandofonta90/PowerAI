"""Construcción de rutas versionadas en el storage de objetos.

El Parquet derivado comparte las coordenadas (torre/plantilla/país/periodo/
versión) del archivo origen, de modo que referencia su versión exacta.
"""

from app.domain.enums import Torre


def _base(torre: Torre, plantilla_codigo: str, pais: str, periodo: str, version: int) -> str:
    return f"{torre.value}/{plantilla_codigo}/{pais}/{periodo}/v{version}"


def ruta_original(
    torre: Torre,
    plantilla_codigo: str,
    pais: str,
    periodo: str,
    version: int,
    nombre_archivo: str,
) -> str:
    """Ruta del archivo original e inmutable."""
    return f"{_base(torre, plantilla_codigo, pais, periodo, version)}/{nombre_archivo}"


def ruta_parquet(torre: Torre, plantilla_codigo: str, pais: str, periodo: str, version: int) -> str:
    """Ruta del Parquet derivado (misma versión que el origen)."""
    return f"{_base(torre, plantilla_codigo, pais, periodo, version)}/data.parquet"
