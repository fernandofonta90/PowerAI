"""Normalización de una tabla validada a Parquet.

Coerce cada columna declarada a su tipo, ordena las columnas según la plantilla
y serializa a Parquet en memoria. Se asume que la tabla ya pasó la validación.
"""

import io
from datetime import date
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq

from app.domain.columnas import ColumnaSpec
from app.domain.enums import TipoColumna
from app.ingesta.coercion import coercer
from app.ingesta.lector import Tabla

_PA_TIPOS = {
    TipoColumna.TEXTO: pa.string(),
    TipoColumna.ENTERO: pa.int64(),
    TipoColumna.DECIMAL: pa.float64(),
    TipoColumna.FECHA: pa.date32(),
}


def _valor_pa(valor: str, tipo: TipoColumna) -> object:
    if valor == "":
        return None
    coercido = coercer(valor, tipo)
    if isinstance(coercido, Decimal):
        return float(coercido)
    if isinstance(coercido, date):
        return coercido
    return coercido


def a_parquet(tabla: Tabla, columnas: list[ColumnaSpec]) -> bytes:
    """Serializa la tabla a Parquet usando el esquema de la plantilla."""
    campos = [pa.field(c.nombre, _PA_TIPOS[c.tipo]) for c in columnas]
    esquema = pa.schema(campos)

    datos_por_columna: dict[str, list[object]] = {}
    for col in columnas:
        datos_por_columna[col.nombre] = [
            _valor_pa(fila.get(col.nombre, ""), col.tipo) for fila in tabla.filas
        ]

    tabla_pa = pa.table(datos_por_columna, schema=esquema)
    buffer = io.BytesIO()
    pq.write_table(tabla_pa, buffer)
    return buffer.getvalue()
