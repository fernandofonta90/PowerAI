"""Tests de integración del motor de consulta (Postgres + DuckDB sobre Parquet).

Storage en memoria + ParquetReader local (mismo contrato que Azure). Cubre la RLS
por construcción (un usuario solo-MX jamás obtiene filas de CO), el multi-versión
(solo la última versión por país/periodo), la exactitud decimal vía DuckDB, el
lockdown (el SQL no puede escapar a archivos) y la bitácora de auditoría.
"""

from typing import Any

import pytest
from app.auth.schemas import Grant, UsuarioAutenticado
from app.domain.enums import PAIS_TODOS, Rol, Torre
from app.models.bitacora import BitacoraConsulta
from app.motor.motor import ConsultaInvalida, ejecutar_consulta
from app.scripts.seed_plantillas import PLANTILLAS_OTC
from app.services.rutas import ruta_parquet
from app.storage import CONTENEDOR_DATASETS
from sqlalchemy import select

pytestmark = pytest.mark.integration

AR = PLANTILLAS_OTC[0]  # otc_ar_abiertas


def _usuario_mx() -> UsuarioAutenticado:
    return UsuarioAutenticado(
        email="uploader.mx@powerai.dev",
        nombre="MX",
        grants=[Grant(torre=Torre.OTC, pais="MX", rol=Rol.CONSULTA)],
    )


def _usuario_admin() -> UsuarioAutenticado:
    return UsuarioAutenticado(
        email="admin.otc@powerai.dev",
        nombre="Admin",
        grants=[Grant(torre=Torre.OTC, pais=PAIS_TODOS, rol=Rol.ADMIN)],
    )


# --- RLS por construcción ----------------------------------------------------


def test_usuario_mx_nunca_ve_filas_de_co(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    crear_carga(pais="MX", filas=3)
    crear_carga(pais="CO", filas=4)

    mx = _usuario_mx()
    # Conteo total: solo las 3 filas de MX.
    r = ejecutar_consulta(db_session, mx, "SELECT count(*) AS n FROM ar_abiertas")
    assert r.filas[0][0] == 3
    # Forzar CO explícitamente: 0 filas (los datos de CO no existen en su sesión).
    r2 = ejecutar_consulta(
        db_session, mx, "SELECT count(*) AS n FROM ar_abiertas WHERE pais = 'CO'"
    )
    assert r2.filas[0][0] == 0
    # Países visibles: solo MX.
    r3 = ejecutar_consulta(db_session, mx, "SELECT DISTINCT pais FROM ar_abiertas")
    assert {fila[0] for fila in r3.filas} == {"MX"}


def test_admin_comodin_ve_todos_los_paises(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    crear_carga(pais="MX", filas=3)
    crear_carga(pais="CO", filas=4)

    r = ejecutar_consulta(db_session, _usuario_admin(), "SELECT count(*) AS n FROM ar_abiertas")
    assert r.filas[0][0] == 7


# --- multi-versión -----------------------------------------------------------


def test_solo_la_ultima_version_por_pais_periodo(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    crear_carga(pais="MX", periodo="2026-05", version=1, filas=3)
    crear_carga(pais="MX", periodo="2026-05", version=2, filas=5)

    mx = _usuario_mx()
    r = ejecutar_consulta(db_session, mx, "SELECT count(*) AS n FROM ar_abiertas")
    assert r.filas[0][0] == 5  # solo la v2

    versiones = [v for v in r.versiones_datos if v.plantilla == "otc_ar_abiertas"]
    assert len(versiones) == 1
    assert versiones[0].version == 2


# --- exactitud decimal vía DuckDB -------------------------------------------


def test_suma_de_montos_exacta_al_centavo(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    cols = ",".join(c.nombre for c in AR.columnas)
    filas = "\n".join(f"MX,2026-05,ACME,F-{i},2026-01-01,2026-02-01,0.10,10,USD" for i in range(10))
    crear_carga(pais="MX", contenido=f"{cols}\n{filas}\n".encode())

    r = ejecutar_consulta(db_session, _usuario_mx(), "SELECT sum(monto) AS total FROM ar_abiertas")
    # DECIMAL(18,2) → serializado como string exacto, sin error binario de float.
    assert r.filas[0][0] == "1.00"
    assert r.tipos[0].startswith("DECIMAL")


# --- lockdown ----------------------------------------------------------------


def test_sql_no_puede_escapar_a_archivos(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    crear_carga(pais="CO", filas=3)
    # El usuario MX intenta leer directamente el Parquet de CO: bloqueado.
    ruta_co = ruta_parquet(Torre.OTC, "otc_ar_abiertas", "CO", "2026-05", 1)
    uri = reader_local.uri(CONTENEDOR_DATASETS, ruta_co)
    with pytest.raises(ConsultaInvalida):
        ejecutar_consulta(db_session, _usuario_mx(), f"SELECT * FROM read_parquet('{uri}')")


# --- auditoría ---------------------------------------------------------------


def test_auditoria_registra_consulta_exitosa(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    crear_carga(pais="MX", filas=3)
    ejecutar_consulta(db_session, _usuario_mx(), "SELECT count(*) FROM ar_abiertas")

    bita = db_session.scalars(select(BitacoraConsulta)).all()
    assert len(bita) == 1
    assert bita[0].exito is True
    assert bita[0].usuario_email == "uploader.mx@powerai.dev"
    assert "ar_abiertas" in bita[0].vistas_json
    assert any(v["pais"] == "MX" for v in bita[0].versiones_json)


def test_auditoria_registra_consulta_fallida(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    with pytest.raises(ConsultaInvalida):
        ejecutar_consulta(db_session, _usuario_mx(), "SELECT * FROM tabla_que_no_existe")
    bita = db_session.scalars(select(BitacoraConsulta)).all()
    assert len(bita) == 1
    assert bita[0].exito is False
    assert bita[0].error


# --- alcance vacío -----------------------------------------------------------


def test_usuario_sin_datos_obtiene_cero_filas(
    db_session: Any, crear_carga: Any, reader_local: Any, seed_vistas: Any
) -> None:
    # Usuario con grant a PE, sin cargas en PE: vista vacía, sin error.
    pe = UsuarioAutenticado(
        email="pe@powerai.dev",
        nombre="PE",
        grants=[Grant(torre=Torre.OTC, pais="PE", rol=Rol.CONSULTA)],
    )
    r = ejecutar_consulta(db_session, pe, "SELECT count(*) AS n FROM ar_abiertas")
    assert r.filas[0][0] == 0
