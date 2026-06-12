"""Tests unitarios de la ingesta (sin base de datos): coerción, lectura,
validación y normalización a Parquet. Datos 100% sintéticos."""

import io
from datetime import date
from decimal import Decimal

import pyarrow.parquet as pq
import pytest
from app.domain.enums import TipoColumna
from app.ingesta.coercion import ValorInvalido, coercer
from app.ingesta.lector import ArchivoIlegible, leer_tabla
from app.ingesta.normalizador import a_parquet
from app.ingesta.validacion import validar
from app.scripts.muestras import generar_csv
from app.scripts.seed_plantillas import PLANTILLAS_OTC

AR = PLANTILLAS_OTC[0]  # otc_ar_abiertas


def _csv(pais: str = "MX", periodo: str = "2026-05", filas: int = 4) -> bytes:
    return generar_csv(AR.columnas, AR.columna_pais, AR.columna_periodo, pais, periodo, filas)


# --- coerción ---------------------------------------------------------------


def test_coercer_tipos_validos() -> None:
    assert coercer("hola", TipoColumna.TEXTO) == "hola"
    assert coercer("42", TipoColumna.ENTERO) == 42
    assert coercer("3.50", TipoColumna.DECIMAL) == Decimal("3.50")
    assert coercer("2026-05-01", TipoColumna.FECHA) == date(2026, 5, 1)


@pytest.mark.parametrize(
    ("valor", "tipo"),
    [
        ("abc", TipoColumna.ENTERO),
        ("x", TipoColumna.DECIMAL),
        ("2026-13-99", TipoColumna.FECHA),
    ],
)
def test_coercer_invalido(valor: str, tipo: TipoColumna) -> None:
    with pytest.raises(ValorInvalido):
        coercer(valor, tipo)


# --- lectura ----------------------------------------------------------------


def test_leer_csv_columnas_y_filas() -> None:
    tabla = leer_tabla(_csv(filas=3), "aging.csv")
    assert tabla.columnas == [c.nombre for c in AR.columnas]
    assert len(tabla.filas) == 3


def test_leer_formato_no_soportado() -> None:
    with pytest.raises(ArchivoIlegible):
        leer_tabla(b"algo", "archivo.txt")


# --- validación -------------------------------------------------------------


def _validar(tabla_bytes: bytes, pais: str = "MX", periodo: str = "2026-05") -> list[str]:
    tabla = leer_tabla(tabla_bytes, "aging.csv")
    return validar(tabla, AR.columnas, AR.columna_pais, AR.columna_periodo, pais, periodo)


def test_validar_archivo_correcto() -> None:
    assert _validar(_csv()) == []


def test_validar_pais_declarado_no_coincide() -> None:
    errores = _validar(_csv(pais="MX"), pais="CO")
    assert any("país declarado" in e for e in errores)


def test_validar_periodo_declarado_no_coincide() -> None:
    errores = _validar(_csv(periodo="2026-05"), periodo="2026-04")
    assert any("periodo declarado" in e for e in errores)


def test_validar_columna_faltante() -> None:
    csv = b"pais,periodo,cliente\nMX,2026-05,ACME\n"
    errores = _validar(csv)
    assert any("Falta la columna requerida" in e for e in errores)


def test_validar_tipo_invalido() -> None:
    cols = ",".join(c.nombre for c in AR.columnas)
    # 'monto' recibe texto no numérico.
    fila = "MX,2026-05,ACME,F-1,2026-01-01,2026-02-01,NO_NUMERO,10,USD"
    errores = _validar(f"{cols}\n{fila}\n".encode())
    assert any("monto" in e for e in errores)


# --- normalización ----------------------------------------------------------


def test_a_parquet_preserva_esquema_y_tipos() -> None:
    tabla = leer_tabla(_csv(filas=5), "aging.csv")
    parquet = a_parquet(tabla, AR.columnas)
    pa_tabla = pq.read_table(io.BytesIO(parquet))

    assert pa_tabla.num_rows == 5
    assert pa_tabla.column_names == [c.nombre for c in AR.columnas]
    # Tipos: monto decimal→float, dias_vencido entero, fecha_emision date.
    esquema = {campo.name: str(campo.type) for campo in pa_tabla.schema}
    assert esquema["monto"] == "double"
    assert esquema["dias_vencido"] == "int64"
    assert esquema["fecha_emision"] == "date32[day]"
