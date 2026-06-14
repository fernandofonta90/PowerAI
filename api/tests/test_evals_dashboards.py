"""Tests del eval de generación de dashboards.

El banco real (5 casos) corre contra Azure (manual). Aquí se prueba el MECANISMO
con FakeProvider: que valida semánticamente y que sigue detectando (sin aflojar).
"""

from typing import Any

import pytest
from app.evals.dashboards import CasoDashboard, cargar_casos, evaluar_dashboards
from app.ia.fake import FakeProvider
from app.ia.proveedor import LlamadaTool, RespuestaLLM

pytestmark = pytest.mark.integration

_SPEC_OK = {
    "version": 1,
    "titulo": "Cartera",
    "visuales": [
        {
            "tipo": "kpi",
            "titulo": "Total",
            "sql": "SELECT sum(monto) AS total FROM ar_abiertas",
            "columna_valor": "total",
            "formato": "decimal",
        }
    ],
}


def test_banco_dashboards_carga() -> None:
    casos = cargar_casos()
    assert len(casos) >= 5
    assert any(not c.respondible for c in casos)


def _guion_respondible_mas_honesto() -> list[RespuestaLLM]:
    return [
        # Caso 1 (respondible): listar_vistas + proponer_spec válida.
        RespuestaLLM(tool_calls=[LlamadaTool(id="1", nombre="listar_vistas", argumentos={})]),
        RespuestaLLM(tool_calls=[LlamadaTool(id="2", nombre="proponer_spec", argumentos=_SPEC_OK)]),
        # Caso 2 (no respondible): declara honestamente, sin spec.
        RespuestaLLM(contenido="No hay datos de costo para rentabilidad."),
    ]


def test_mecanismo_aprueba_respondible_y_honesto(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any, seed_usuarios: Any
) -> None:
    crear_carga(pais="MX", filas=3)  # total 7.50
    casos = [
        CasoDashboard(
            id="ok",
            peticion="tablero del total",
            respondible=True,
            tipos_esperados=["kpi"],
            valores_esperados=["7.50"],
        ),
        CasoDashboard(id="no", peticion="rentabilidad", respondible=False),
    ]
    reporte = evaluar_dashboards(db_session, FakeProvider(_guion_respondible_mas_honesto()), casos)
    assert reporte.aprobadas == 2, reporte.resumen()


def test_mecanismo_detecta_valor_incorrecto(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any, seed_usuarios: Any
) -> None:
    crear_carga(pais="MX", filas=3)  # total real 7.50
    casos = [
        CasoDashboard(
            id="ok",
            peticion="tablero del total",
            respondible=True,
            tipos_esperados=["kpi"],
            valores_esperados=["999.99"],  # no existe
        )
    ]
    guion = [
        RespuestaLLM(tool_calls=[LlamadaTool(id="1", nombre="listar_vistas", argumentos={})]),
        RespuestaLLM(tool_calls=[LlamadaTool(id="2", nombre="proponer_spec", argumentos=_SPEC_OK)]),
    ]
    reporte = evaluar_dashboards(db_session, FakeProvider(guion), casos)
    assert reporte.aprobadas == 0  # el eval caza el valor inexistente
