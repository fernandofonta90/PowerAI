"""Especificación de columnas de una plantilla (value object).

Las plantillas son DATOS, no código (decisión vinculante del arquitecto): el
esquema esperado de cada reporte se persiste como JSON y se ajusta con un update
de datos, nunca con un cambio de código.
"""

from pydantic import BaseModel

from app.domain.enums import TipoColumna


class ColumnaSpec(BaseModel):
    """Definición de una columna esperada en el archivo de origen."""

    nombre: str
    tipo: TipoColumna
    requerida: bool = True
    descripcion: str = ""


class ColumnaDescrita(BaseModel):
    """Columna de una vista del catálogo con su descripción de negocio.

    La descripción se redacta para un lector de NEGOCIO: el LLM la leerá (M4)
    para decidir qué consultar.
    """

    nombre: str
    descripcion: str
