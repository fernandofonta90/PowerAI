"""Tests del banco de preguntas doradas.

Nivel motor: ejecuta el banco completo contra el motor M3 y exige 100% (CI).
Nivel agente: verifica el runner con el FakeProvider (en CI no hay LLM real).
"""

from typing import Any

import pytest
from app.evals.banco import PreguntaDorada, cargar_banco
from app.evals.dataset import construir_dataset
from app.evals.runner import evaluar_agente, evaluar_motor
from app.ia.fake import FakeProvider
from app.ia.proveedor import LlamadaTool, RespuestaLLM

pytestmark = pytest.mark.integration


def test_banco_carga_y_estructura() -> None:
    preguntas = cargar_banco()
    respondibles = [p for p in preguntas if p.respondible]
    no_respondibles = [p for p in preguntas if not p.respondible]
    assert 25 <= len(respondibles) <= 30
    assert len(no_respondibles) >= 3
    # Toda respondible trae SQL canónico y aserción; toda no-respondible no.
    for p in respondibles:
        assert p.sql_canonico and p.asercion is not None
    for p in no_respondibles:
        assert p.sql_canonico is None


def test_nivel_motor_100_por_ciento(
    db_session: Any, almacen_memoria: Any, reader_local: Any, seed_vistas: Any, seed_usuarios: Any
) -> None:
    construir_dataset(db_session, almacen_memoria)
    reporte = evaluar_motor(db_session, cargar_banco())
    assert reporte.tasa == 1.0, reporte.resumen()


def test_nivel_agente_runner_con_fake(
    db_session: Any, almacen_memoria: Any, reader_local: Any, seed_vistas: Any, seed_usuarios: Any
) -> None:
    construir_dataset(db_session, almacen_memoria)
    # Pregunta respondible con guion que ejecuta el SQL correcto, y una honesta.
    respondible = PreguntaDorada(
        id="t-respondible",
        cu="CU-00",
        pregunta="¿Total de cartera?",
        usuario="uploader.mx@powerai.dev",
        respondible=True,
        sql_canonico="SELECT sum(monto) AS total FROM ar_abiertas",
        asercion={"filas": [["99091.50"]]},
    )
    honesta = PreguntaDorada(
        id="t-honesta",
        cu="CU-XX",
        pregunta="¿Tipo de cambio?",
        usuario="uploader.mx@powerai.dev",
        respondible=False,
    )
    guion = [
        RespuestaLLM(
            tool_calls=[
                LlamadaTool(
                    id="1",
                    nombre="ejecutar_sql",
                    argumentos={"sql": "SELECT sum(monto) AS total FROM ar_abiertas"},
                )
            ]
        ),
        RespuestaLLM(contenido="El total es 99091.50."),
        RespuestaLLM(contenido="No tengo esa información en el catálogo."),
    ]
    reporte = evaluar_agente(db_session, FakeProvider(guion), [respondible, honesta])
    assert reporte.total == 2
    assert reporte.aprobadas == 2, reporte.resumen()
