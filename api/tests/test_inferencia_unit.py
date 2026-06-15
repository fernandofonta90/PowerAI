"""Tests de la inferencia de tipos al inspeccionar (M12). SUGIERE, no impone."""

from app.domain.enums import TipoColumna
from app.services.plantillas import inferir_tipo


def test_decimal() -> None:
    assert inferir_tipo(["100.50", "0.01", "1250.00"], "monto") is TipoColumna.DECIMAL


def test_entero() -> None:
    assert inferir_tipo(["1", "42", "100"], "dias_vencido") is TipoColumna.ENTERO


def test_fecha_iso() -> None:
    assert inferir_tipo(["2026-01-01", "2026-05-31"], "fecha_emision") is TipoColumna.FECHA


def test_fecha_dd_mm_se_infiere_fecha() -> None:
    # Formato real DD/MM/YYYY (con un 31 que lo desambigua) → fecha.
    assert inferir_tipo(["10/06/2025", "31/12/2025"], "invoice_date") is TipoColumna.FECHA


def test_fecha_ambigua_se_infiere_texto() -> None:
    # Sin señal para desambiguar → texto (no se corrompe eligiendo orden).
    assert inferir_tipo(["10/06/2025", "07/08/2025"], "fecha") is TipoColumna.TEXTO


def test_texto() -> None:
    assert inferir_tipo(["ACME", "GLOBEX", "INITECH"], "cliente") is TipoColumna.TEXTO


def test_id_numerico_por_nombre_es_texto() -> None:
    # Aunque sean enteros, un nombre tipo id/number sugiere TEXTO (no se operan).
    assert inferir_tipo(["1001", "1002", "1003"], "invoice_number") is TipoColumna.TEXTO
    assert inferir_tipo(["7", "8", "9"], "id") is TipoColumna.TEXTO


def test_id_por_ceros_a_la_izquierda_es_texto() -> None:
    # Ceros a la izquierda: es un código, no un número.
    assert inferir_tipo(["007", "012", "099"], "sucursal") is TipoColumna.TEXTO


def test_columna_vacia_es_texto() -> None:
    assert inferir_tipo(["", "  ", ""], "vacia") is TipoColumna.TEXTO


def test_mezcla_no_numerica_es_texto() -> None:
    assert inferir_tipo(["100", "N/A", "200"], "monto") is TipoColumna.TEXTO
