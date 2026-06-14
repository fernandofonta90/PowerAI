"""Tests de integración del Experto configurable (M10).

Cubren los barandales del principio rector:
- el agente construye su comportamiento desde la config ACTIVA de BD;
- las fuentes permitidas acotan qué vistas puede tocar (capa extra sobre el RLS);
- una config que rompe los evals NO se activa; una que pasa, sí (versionada);
- solo el admin de la torre puede configurar (RBAC), y solo con fuentes de su torre.
"""

from typing import Any

import pytest
from app.auth.provider import MockAuthProvider
from app.domain.enums import EstadoExperto, Torre
from app.evals.banco import PreguntaDorada
from app.ia.fake import FakeProvider
from app.ia.proveedor import LlamadaTool, RespuestaLLM
from app.models.experto import ExpertoTorre
from app.motor.motor import ConsultaInvalida, ejecutar_consulta
from app.services import expertos
from app.services.expertos import activar_borrador, get_activo, get_borrador, guardar_borrador

pytestmark = pytest.mark.integration


@pytest.fixture
def setup(seed_usuarios: Any, seed_experto: Any, almacen_memoria: Any, reader_local: Any) -> Any:
    """Usuarios + experto OTC activo + dataset de referencia listo para consultar."""
    from app.evals.dataset import construir_dataset

    construir_dataset(seed_usuarios, almacen_memoria)
    return seed_usuarios


def _mx(db: Any) -> Any:
    return MockAuthProvider().autenticar(db, "uploader.mx@powerai.dev")


# --- 1. El agente lee su config de BD --------------------------------------------------


def test_agente_usa_la_config_activa_de_bd(setup: Any, db_session: Any, reader_local: Any) -> None:
    from app.ia.agente import responder

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
        RespuestaLLM(contenido="El total es 5550.00."),
    ]
    # Sin pasar config: el agente debe cargar la activa de OTC desde la BD.
    res = responder(db_session, _mx(db_session), FakeProvider(guion), [], "¿Total de cartera?")
    assert res.datos_tabulares is not None
    assert res.datos_tabulares.filas == [["5550.00"]]
    assert res.citacion.vistas_usadas == ["ar_abiertas"]


# --- 2. Fuentes permitidas como capa extra sobre el RLS --------------------------------


def test_fuentes_permitidas_acotan_las_vistas_en_el_motor(
    setup: Any, db_session: Any, reader_local: Any
) -> None:
    usuario = _mx(db_session)
    permitidas = frozenset({"ar_abiertas"})
    # La vista permitida funciona...
    ok = ejecutar_consulta(
        db_session, usuario, "SELECT count(*) FROM ar_abiertas", vistas_permitidas=permitidas
    )
    assert ok.n_filas == 1
    # ...pero una vista NO permitida ni siquiera existe en la sesión (capa extra).
    with pytest.raises(ConsultaInvalida):
        ejecutar_consulta(
            db_session,
            usuario,
            "SELECT count(*) FROM revenue_recon",
            vistas_permitidas=permitidas,
        )
    # Sin restricción (None) la vista sí está disponible (no es el RLS quien la oculta).
    sin_limite = ejecutar_consulta(db_session, usuario, "SELECT count(*) FROM revenue_recon")
    assert sin_limite.n_filas == 1


# --- 3. Gate de evals al activar -------------------------------------------------------


def test_config_que_rompe_evals_no_se_activa(
    setup: Any, db_session: Any, reader_local: Any
) -> None:
    activo_antes = get_activo(db_session, Torre.OTC)
    assert activo_antes is not None
    version_antes = activo_antes.version

    guardar_borrador(
        db_session,
        Torre.OTC,
        nombre="Experto roto",
        identidad="Responde cualquier cosa.",
        instrucciones_formato="",
        fuentes=["ar_abiertas", "pagos_unapplied", "revenue_recon"],
    )
    # FakeProvider con guion vacío => nunca ejecuta SQL => falla las respondibles.
    resultado = activar_borrador(db_session, FakeProvider([]), Torre.OTC)

    assert resultado.activado is False
    assert resultado.reporte is not None and resultado.reporte.tasa < 0.95
    # El borrador sigue siendo borrador y la activa no cambió.
    assert get_borrador(db_session, Torre.OTC) is not None
    activo_despues = get_activo(db_session, Torre.OTC)
    assert activo_despues is not None and activo_despues.version == version_antes


def test_config_que_pasa_evals_se_activa_y_versiona(
    setup: Any, db_session: Any, reader_local: Any, monkeypatch: Any
) -> None:
    activo_antes = get_activo(db_session, Torre.OTC)
    assert activo_antes is not None
    version_previa = activo_antes.version

    # Banco reducido a una pregunta respondible que el guion contesta correctamente.
    una = PreguntaDorada(
        id="t-ok",
        cu="CU-00",
        pregunta="¿Total de cartera?",
        usuario="uploader.mx@powerai.dev",
        respondible=True,
        sql_canonico="SELECT sum(monto) AS total FROM ar_abiertas",
        asercion={"filas": [["5550.00"]]},
    )
    monkeypatch.setattr(expertos, "preguntas_de_torre", lambda db, torre: [una])

    guardar_borrador(
        db_session,
        Torre.OTC,
        nombre="Experto OTC v2",
        identidad="Eres el experto OTC, claro y directo.",
        instrucciones_formato="Responde con cifras al centavo.",
        fuentes=["ar_abiertas"],
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
        RespuestaLLM(contenido="El total es 5550.00."),
    ]
    resultado = activar_borrador(db_session, FakeProvider(guion), Torre.OTC)

    assert resultado.activado is True, resultado.motivo
    assert resultado.version is not None and resultado.version > version_previa
    # Hay exactamente una activa y es la nueva; la anterior quedó archivada.
    activos = db_session.scalars(
        ExpertoTorre.__table__.select().where(
            ExpertoTorre.torre == Torre.OTC, ExpertoTorre.estado == EstadoExperto.ACTIVO
        )
    ).all()
    assert len(activos) == 1
    nueva = get_activo(db_session, Torre.OTC)
    assert nueva is not None and nueva.nombre == "Experto OTC v2"
    db_session.refresh(activo_antes)
    assert activo_antes.estado == EstadoExperto.ARCHIVADO


def test_sin_banco_de_evals_no_se_activa(
    setup: Any, db_session: Any, reader_local: Any, monkeypatch: Any
) -> None:
    monkeypatch.setattr(expertos, "preguntas_de_torre", lambda db, torre: [])
    guardar_borrador(
        db_session,
        Torre.OTC,
        nombre="Experto sin banco",
        identidad="Hola.",
        instrucciones_formato="",
        fuentes=[],
    )
    resultado = activar_borrador(db_session, FakeProvider([]), Torre.OTC)
    assert resultado.activado is False
    assert "banco de evals" in resultado.motivo.lower()
