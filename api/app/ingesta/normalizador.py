"""Normalización de una tabla validada a Parquet.

Coerce cada columna declarada a su tipo, ordena las columnas según la plantilla
y serializa a Parquet en memoria. Se asume que la tabla ya pasó la validación.
"""

import io
from decimal import ROUND_HALF_UP, Decimal

import pyarrow as pa
import pyarrow.parquet as pq

from app.domain.columnas import ColumnaSpec
from app.domain.enums import TipoColumna
from app.ingesta.coercion import coercer
from app.ingesta.lector import Tabla

# Montos: punto fijo DECIMAL(18,2). NUNCA float64: los montos financieros se
# concilian al centavo y el float binario introduce errores de redondeo.
DECIMAL_PRECISION = 18
DECIMAL_ESCALA = 2
_CENTAVO = Decimal(10) ** -DECIMAL_ESCALA  # Decimal("0.01")

_PA_TIPOS = {
    TipoColumna.TEXTO: pa.string(),
    TipoColumna.ENTERO: pa.int64(),
    TipoColumna.DECIMAL: pa.decimal128(DECIMAL_PRECISION, DECIMAL_ESCALA),
    TipoColumna.FECHA: pa.date32(),
}


def _valor_pa(valor: str, tipo: TipoColumna) -> object:
    if valor == "":
        return None
    coercido = coercer(valor, tipo)
    if isinstance(coercido, Decimal):
        # Cuantiza al centavo (half-up) para encajar en DECIMAL(18,2) exacto.
        return coercido.quantize(_CENTAVO, rounding=ROUND_HALF_UP)
    return coercido


def a_parquet(tabla: Tabla, columnas: list[ColumnaSpec]) -> bytes:
    """Serializa la tabla a Parquet usando el esquema de la plantilla."""
    campos = [pa.field(c.nombre, _PA_TIPOS[c.tipo]) for c in columnas]
    esquema = pa.schema(campos)

    # Se lee del archivo por el encabezado original (etiqueta) y se escribe bajo el
    # nombre técnico (slug), que es el que usan el Parquet, las vistas y DuckDB.
    datos_por_columna: dict[str, list[object]] = {}
    for col in columnas:
        datos_por_columna[col.nombre] = [
            _valor_pa(fila.get(col.etiqueta, ""), col.tipo) for fila in tabla.filas
        ]

    tabla_pa = pa.table(datos_por_columna, schema=esquema)
    buffer = io.BytesIO()
    pq.write_table(tabla_pa, buffer)
    return buffer.getvalue()
