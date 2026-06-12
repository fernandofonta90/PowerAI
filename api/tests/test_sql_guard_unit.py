"""Tests unitarios del guard de SQL (solo SELECT de una sentencia)."""

import pytest
from app.ia.sql_guard import SqlNoPermitido, validar_select


def test_select_simple_permitido() -> None:
    validar_select("SELECT * FROM ar_abiertas")


def test_with_cte_permitido() -> None:
    validar_select("WITH t AS (SELECT 1 AS n) SELECT n FROM t")


def test_select_con_punto_y_coma_final_permitido() -> None:
    validar_select("SELECT 1;")


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE ar_abiertas",
        "DELETE FROM ar_abiertas",
        "INSERT INTO ar_abiertas VALUES (1)",
        "UPDATE ar_abiertas SET monto = 0",
        "ATTACH 'x.db'",
        "COPY ar_abiertas TO 'x.csv'",
        "SET enable_external_access=true",
        "INSTALL azure",
        "SELECT 1; DROP TABLE ar_abiertas",
        "",
    ],
)
def test_no_select_bloqueado(sql: str) -> None:
    with pytest.raises(SqlNoPermitido):
        validar_select(sql)
