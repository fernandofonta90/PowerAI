"""Especificación de columnas de una plantilla (value object).

Las plantillas son DATOS, no código (decisión vinculante del arquitecto): el
esquema esperado de cada reporte se persiste como JSON y se ajusta con un update
de datos, nunca con un cambio de código.
"""

from pydantic import BaseModel, model_validator

from app.domain.enums import TipoColumna


class ColumnaSpec(BaseModel):
    """Definición de una columna esperada en el archivo de origen.

    ``nombre`` es el identificador técnico SQL-seguro (snake_case, usado en
    DuckDB/Parquet y en las vistas). ``etiqueta`` es el encabezado original legible
    del archivo (lo que el usuario ve y por lo que se mapea/valida la carga). Cuando
    no se especifica ``etiqueta``, se asume igual a ``nombre`` (caso de las
    plantillas en snake_case sembradas, donde encabezado == nombre técnico).
    """

    nombre: str
    tipo: TipoColumna
    requerida: bool = True
    descripcion: str = ""
    etiqueta: str = ""

    @model_validator(mode="after")
    def _etiqueta_por_defecto(self) -> "ColumnaSpec":
        if not self.etiqueta:
            self.etiqueta = self.nombre
        return self


class ColumnaDescrita(BaseModel):
    """Columna de una vista del catálogo con su descripción de negocio.

    La descripción se redacta para un lector de NEGOCIO: el LLM la leerá (M4)
    para decidir qué consultar.
    """

    nombre: str
    descripcion: str
