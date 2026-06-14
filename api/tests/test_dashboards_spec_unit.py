"""Tests unitarios de la validación de la spec de dashboard (v1)."""

import pytest
from app.dashboards.spec import SpecInvalida, validar_spec


def _spec(visuales: list[dict]) -> dict:
    return {"version": 1, "titulo": "Cartera", "visuales": visuales}


def test_spec_valida() -> None:
    spec = validar_spec(
        _spec(
            [
                {
                    "tipo": "kpi",
                    "titulo": "Total",
                    "sql": "SELECT sum(monto) AS t FROM ar_abiertas",
                    "columna_valor": "t",
                    "formato": "decimal",
                },
                {
                    "tipo": "barras",
                    "titulo": "Por cliente",
                    "sql": "SELECT cliente, sum(monto) AS s FROM ar_abiertas GROUP BY cliente",
                    "eje_x": "cliente",
                    "eje_y": "s",
                    "formato": "decimal",
                },
            ]
        )
    )
    assert spec.version == 1
    assert len(spec.visuales) == 2


def test_kpi_sin_columna_valor_falla() -> None:
    with pytest.raises(SpecInvalida):
        validar_spec(
            _spec([{"tipo": "kpi", "titulo": "x", "sql": "SELECT 1 AS a FROM ar_abiertas"}])
        )


def test_barras_sin_ejes_falla() -> None:
    with pytest.raises(SpecInvalida):
        validar_spec(_spec([{"tipo": "barras", "titulo": "x", "sql": "SELECT a FROM ar_abiertas"}]))


def test_sql_no_select_falla() -> None:
    with pytest.raises(SpecInvalida):
        validar_spec(
            _spec(
                [
                    {
                        "tipo": "tabla",
                        "titulo": "x",
                        "sql": "DROP TABLE ar_abiertas",
                    }
                ]
            )
        )


def test_sin_visuales_falla() -> None:
    with pytest.raises(SpecInvalida):
        validar_spec(_spec([]))
