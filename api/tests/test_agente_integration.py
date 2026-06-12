"""Tests del agente analítico con el FakeProvider (guionizado).

Cubre: pregunta respondible (tool-call + respuesta citada), pregunta fuera del
catálogo (respuesta honesta), intento de SQL no-SELECT (bloqueado, sin tocar el
motor) y límite de iteraciones alcanzado.
"""

from typing import Any

import pytest
from app.auth.schemas import Grant, UsuarioAutenticado
from app.domain.enums import Rol, Torre
from app.ia.agente import responder
from app.ia.fake import FakeProvider
from app.ia.proveedor import LlamadaTool, RespuestaLLM
from app.models.bitacora import BitacoraConsulta
from app.scripts.seed_plantillas import PLANTILLAS_OTC
from sqlalchemy import select

pytestmark = pytest.mark.integration

AR = PLANTILLAS_OTC[0]


def _mx() -> UsuarioAutenticado:
    return UsuarioAutenticado(
        email="uploader.mx@powerai.dev",
        nombre="MX",
        grants=[Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA)],
    )


def _carga_montos(crear_carga: Any) -> None:
    cols = ",".join(c.nombre for c in AR.columnas)
    filas = "\n".join(f"MX,2026-05,ACME,F-{i},2026-01-01,2026-02-01,0.10,10,USD" for i in range(10))
    crear_carga(pais="MX", contenido=f"{cols}\n{filas}\n".encode())


def test_pregunta_respondible_cita_fuentes(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    _carga_montos(crear_carga)
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
        RespuestaLLM(contenido="El total de cartera abierta es 1.00 USD."),
    ]
    res = responder(db_session, _mx(), FakeProvider(guion), [], "¿Cuál es el total?")

    assert "1.00" in res.texto
    assert res.datos_tabulares is not None
    assert res.datos_tabulares.filas[0][0] == "1.00"
    assert len(res.citacion.fuentes) == 1
    assert res.citacion.fuentes[0].pais == "MX"
    assert len(res.citacion.sql_ejecutado_ids) == 1
    assert "ar_abiertas" in res.citacion.vistas_usadas


def test_pregunta_fuera_de_catalogo_respuesta_honesta(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    guion = [RespuestaLLM(contenido="No tengo datos sobre eso en el catálogo.")]
    res = responder(db_session, _mx(), FakeProvider(guion), [], "¿Clima en Marte?")

    assert "No tengo datos" in res.texto
    assert res.citacion.fuentes == []
    assert res.citacion.sql_ejecutado_ids == []
    assert res.datos_tabulares is None


def test_sql_no_select_es_bloqueado(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    _carga_montos(crear_carga)
    guion = [
        RespuestaLLM(
            tool_calls=[
                LlamadaTool(
                    id="1",
                    nombre="ejecutar_sql",
                    argumentos={"sql": "DROP TABLE ar_abiertas"},
                )
            ]
        ),
        RespuestaLLM(contenido="No pude ejecutar esa operación."),
    ]
    provider = FakeProvider(guion)
    res = responder(db_session, _mx(), provider, [], "Borra la tabla")

    # El motor nunca se invocó: no hay bitácora ni fuentes.
    assert db_session.scalars(select(BitacoraConsulta)).all() == []
    assert res.citacion.sql_ejecutado_ids == []
    # El modelo recibió el error de la tool en el segundo turno.
    ultimo_hilo = provider.hilos[-1]
    assert any(
        m.rol == "tool" and m.contenido and "permit" in m.contenido.lower() for m in ultimo_hilo
    )


def test_limite_de_iteraciones(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    # El modelo nunca da una respuesta final: solo llama tools.
    guion = [
        RespuestaLLM(tool_calls=[LlamadaTool(id=str(i), nombre="listar_vistas", argumentos={})])
        for i in range(5)
    ]
    res = responder(db_session, _mx(), FakeProvider(guion), [], "Da vueltas", max_iteraciones=2)
    assert "límite" in res.texto.lower()
