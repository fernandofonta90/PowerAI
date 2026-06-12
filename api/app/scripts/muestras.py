"""Generador de archivos de muestra SINTÉTICOS para una plantilla.

Útil para tests y para probar la carga en dev. No usa datos reales del SSC: los
valores se derivan del índice de fila de forma determinística.
"""

import csv
import io
from datetime import date, timedelta

from app.domain.columnas import ColumnaSpec
from app.domain.enums import TipoColumna

_FECHA_BASE = date(2026, 1, 1)


def _valor(col: ColumnaSpec, i: int) -> str:
    if col.tipo is TipoColumna.TEXTO:
        return f"{col.nombre}_{i}"
    if col.tipo is TipoColumna.ENTERO:
        return str(i)
    if col.tipo is TipoColumna.DECIMAL:
        return f"{i}.50"
    if col.tipo is TipoColumna.FECHA:
        return (_FECHA_BASE + timedelta(days=i)).isoformat()
    raise ValueError(f"Tipo no soportado: {col.tipo}")


def generar_csv(
    columnas: list[ColumnaSpec],
    columna_pais: str,
    columna_periodo: str,
    pais: str,
    periodo: str,
    filas: int = 5,
) -> bytes:
    """Genera un CSV válido para la plantilla, con país y periodo consistentes."""
    nombres = [c.nombre for c in columnas]
    buffer = io.StringIO()
    escritor = csv.writer(buffer)
    escritor.writerow(nombres)
    for i in range(1, filas + 1):
        fila = []
        for col in columnas:
            if col.nombre == columna_pais:
                fila.append(pais)
            elif col.nombre == columna_periodo:
                fila.append(periodo)
            else:
                fila.append(_valor(col, i))
        escritor.writerow(fila)
    return buffer.getvalue().encode("utf-8")
