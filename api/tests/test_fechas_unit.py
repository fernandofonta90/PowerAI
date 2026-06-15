"""Tests de detección/parseo de fechas de reportes reales (M15)."""

from datetime import date

import pytest
from app.ingesta.coercion import ValorInvalido
from app.ingesta.fechas import detectar_formato_fecha, parsear_fecha


def test_detecta_iso() -> None:
    assert detectar_formato_fecha(["2025-06-10", "2025-12-31"]) == "iso"


def test_detecta_dmy_por_dia_mayor_a_12() -> None:
    # "31/12" solo puede ser día/mes → DD/MM/YYYY.
    assert detectar_formato_fecha(["10/06/2025", "31/12/2025"]) == "dmy"


def test_detecta_mdy_por_segundo_campo_mayor_a_12() -> None:
    # "10/31" solo puede ser mes/día → MM/DD/YYYY.
    assert detectar_formato_fecha(["10/31/2025", "06/10/2025"]) == "mdy"


def test_ambiguo_sin_senal_es_none() -> None:
    # Todos los campos ≤ 12: no se puede saber el orden.
    assert detectar_formato_fecha(["10/06/2025", "07/08/2025"]) is None


def test_conflicto_dmy_y_mdy_es_none() -> None:
    assert detectar_formato_fecha(["31/12/2025", "12/31/2025"]) is None


def test_mezcla_de_formas_es_none() -> None:
    assert detectar_formato_fecha(["2025-06-10", "10/06/2025"]) is None


def test_columna_no_fecha_es_none() -> None:
    assert detectar_formato_fecha(["100", "200"]) is None
    assert detectar_formato_fecha([]) is None


def test_parsea_segun_formato() -> None:
    assert parsear_fecha("10/06/2025", "dmy") == date(2025, 6, 10)
    assert parsear_fecha("10/31/2025", "mdy") == date(2025, 10, 31)
    assert parsear_fecha("2025-06-10", "iso") == date(2025, 6, 10)


def test_parseo_invalido_lanza() -> None:
    with pytest.raises(ValorInvalido):
        parsear_fecha("32/01/2025", "dmy")  # día 32 no existe
