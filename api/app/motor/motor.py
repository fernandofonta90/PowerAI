"""Motor de consulta analítica con seguridad a nivel de fila por construcción.

Por cada request, el motor materializa en DuckDB la "fuente" de cada plantilla
del alcance del usuario, conteniendo SOLO la última versión por (país, periodo)
y SOLO los países que sus grants cubren (RLS por construcción). Luego crea las
vistas curadas sobre esas fuentes y BLOQUEA el acceso externo: el SQL del usuario
solo puede tocar esas vistas/fuentes ya filtradas — los datos fuera de su alcance
no existen en su sesión. Cada ejecución se registra en la bitácora de auditoría.

DECISIÓN A REVISITAR (potencialmente ADR si cambia): las fuentes se materializan
COMPLETAS en memoria (CREATE TEMP TABLE ... AS SELECT * FROM read_parquet(...))
para poder bloquear el acceso externo y, a la vez, mantener los datos
consultables. Es correcto para los volúmenes del SSC (decenas de miles a pocos
millones de filas por carga). Si los volúmenes crecieran de forma significativa,
habría que cambiar a vistas perezosas + un mecanismo de filtrado de SQL (en vez
del lockdown post-materialización), lo que altera el modelo de seguridad: ese
cambio amerita un ADR.

El lockdown depende de SET enable_external_access=false: ver la versión fija de
DuckDB en pyproject.toml.
"""

import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import duckdb
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.domain.enums import PAIS_TODOS, EstadoCarga, TipoColumna, Torre
from app.models.bitacora import BitacoraConsulta
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.models.vista import VistaCatalogo
from app.motor.parquet_reader import ParquetReader, get_parquet_reader
from app.storage import CONTENEDOR_DATASETS

_IDENT = re.compile(r"^[a-z_][a-z0-9_]*$")

_DUCKDB_TIPOS = {
    TipoColumna.TEXTO: "VARCHAR",
    TipoColumna.ENTERO: "BIGINT",
    TipoColumna.DECIMAL: "DECIMAL(18,2)",
    TipoColumna.FECHA: "DATE",
}


class ConsultaInvalida(Exception):
    """El SQL del usuario falló al ejecutarse contra sus vistas."""


class VersionDato(BaseModel):
    plantilla: str
    pais: str
    periodo: str
    version: int


class ResultadoConsulta(BaseModel):
    columnas: list[str]
    tipos: list[str]
    filas: list[list[Any]]
    n_filas: int
    sql_ejecutado: str
    vistas_usadas: list[str]
    versiones_datos: list[VersionDato]
    # Id de la entrada de bitácora generada (referencia para la auditoría del chat).
    bitacora_id: uuid.UUID | None = None


def _validar_ident(nombre: str) -> None:
    if not _IDENT.match(nombre):
        raise ValueError(f"Identificador no seguro para SQL: {nombre!r}")


def _paises_accesibles(usuario: UsuarioAutenticado, torre: Torre) -> tuple[bool, set[str]]:
    """(comodín, países) que el usuario puede ver en la torre."""
    paises: set[str] = set()
    comodin = False
    for g in usuario.grants:
        if g.torre != torre:
            continue
        if g.pais == PAIS_TODOS:
            comodin = True
        else:
            paises.add(g.pais)
    return comodin, paises


def _plantillas_en_alcance(db: Session, usuario: UsuarioAutenticado) -> list[PlantillaReporte]:
    torres = usuario.torres_accesibles()
    if not torres:
        return []
    return list(db.scalars(select(PlantillaReporte).where(PlantillaReporte.torre.in_(torres))))


def _vistas_en_alcance(db: Session, usuario: UsuarioAutenticado) -> list[VistaCatalogo]:
    torres = usuario.torres_accesibles()
    if not torres:
        return []
    return list(
        db.scalars(
            select(VistaCatalogo)
            .where(VistaCatalogo.torre.in_(torres))
            .order_by(VistaCatalogo.nombre)
        )
    )


def _cargas_ultima_version(
    db: Session, plantilla: PlantillaReporte, usuario: UsuarioAutenticado
) -> list[CargaArchivo]:
    """Cargas disponibles de la plantilla, última versión por (país, periodo),
    restringidas a los países accesibles (RLS)."""
    comodin, paises = _paises_accesibles(usuario, plantilla.torre)
    stmt = select(CargaArchivo).where(
        CargaArchivo.plantilla_id == plantilla.id,
        CargaArchivo.estado == EstadoCarga.DISPONIBLE,
    )
    if not comodin:
        if not paises:
            return []
        stmt = stmt.where(CargaArchivo.pais.in_(paises))

    ultima: dict[tuple[str, str], CargaArchivo] = {}
    for c in db.scalars(stmt):
        clave = (c.pais, c.periodo)
        if clave not in ultima or c.version > ultima[clave].version:
            ultima[clave] = c
    return list(ultima.values())


def _cols_ddl(plantilla: PlantillaReporte) -> str:
    return ", ".join(f'"{c.nombre}" {_DUCKDB_TIPOS[c.tipo]}' for c in plantilla.columnas)


def _json_safe(valor: Any) -> Any:
    if isinstance(valor, Decimal):
        return str(valor)  # preserva exactitud al centavo en JSON
    if isinstance(valor, date | datetime):
        return valor.isoformat()
    return valor


def _vistas_referenciadas(sql: str, vistas: list[VistaCatalogo]) -> list[str]:
    sql_low = sql.lower()
    return [v.nombre for v in vistas if re.search(rf"\b{v.nombre}\b", sql_low)]


def _auditar(
    db: Session,
    usuario_email: str,
    sql: str,
    vistas_usadas: list[str],
    versiones: list[VersionDato],
    filas: int,
    exito: bool,
    error: str | None,
) -> uuid.UUID:
    registro = BitacoraConsulta(
        usuario_email=usuario_email,
        sql_ejecutado=sql,
        vistas_json=vistas_usadas,
        versiones_json=[v.model_dump() for v in versiones],
        filas=filas,
        exito=exito,
        error=error,
    )
    db.add(registro)
    db.commit()
    return registro.id


def ejecutar_consulta(
    db: Session,
    usuario: UsuarioAutenticado,
    sql: str,
    *,
    reader: ParquetReader | None = None,
    vistas_permitidas: frozenset[str] | None = None,
) -> ResultadoConsulta:
    """Ejecuta ``sql`` contra las vistas pre-filtradas del usuario y audita.

    ``vistas_permitidas`` es una capa EXTRA sobre el RLS (no lo reemplaza): si se
    indica, solo se materializan esas vistas curadas, de modo que el SQL no puede
    siquiera nombrar una vista fuera del alcance del Experto. El RLS por fila
    (torre × país) se aplica igual sobre las fuentes subyacentes.
    """
    reader = reader or get_parquet_reader()
    con = duckdb.connect()
    # Versiones cargadas por plantilla; la citación reporta solo las referenciadas.
    versiones_por_plantilla: dict[str, list[VersionDato]] = {}
    try:
        reader.preparar(con)

        # 1. Fuentes (RLS + última versión) materializadas en memoria.
        for plantilla in _plantillas_en_alcance(db, usuario):
            _validar_ident(plantilla.codigo)
            cargas = _cargas_ultima_version(db, plantilla, usuario)
            if cargas:
                uris = []
                for c in cargas:
                    ruta = c.blob_path_parquet
                    assert ruta is not None  # garantizado por estado=DISPONIBLE
                    uris.append(
                        "'" + reader.uri(CONTENEDOR_DATASETS, ruta).replace("'", "''") + "'"
                    )
                con.execute(
                    f'CREATE TEMP TABLE "{plantilla.codigo}" AS '
                    f"SELECT * FROM read_parquet([{', '.join(uris)}])"
                )
                versiones_por_plantilla[plantilla.codigo] = [
                    VersionDato(
                        plantilla=plantilla.codigo,
                        pais=c.pais,
                        periodo=c.periodo,
                        version=c.version,
                    )
                    for c in cargas
                ]
            else:
                con.execute(f'CREATE TEMP TABLE "{plantilla.codigo}" ({_cols_ddl(plantilla)})')

        # 2. Vistas curadas sobre las fuentes (acotadas por el Experto si aplica).
        vistas = _vistas_en_alcance(db, usuario)
        if vistas_permitidas is not None:
            vistas = [v for v in vistas if v.nombre in vistas_permitidas]
        vista_a_plantilla = {v.nombre: v.plantilla.codigo for v in vistas}
        for v in vistas:
            _validar_ident(v.nombre)
            con.execute(f'CREATE TEMP VIEW "{v.nombre}" AS {v.sql}')

        # 3. Lockdown: el SQL del usuario ya no puede leer archivos externos.
        con.execute("SET enable_external_access=false")

        vistas_usadas = _vistas_referenciadas(sql, vistas)

        # Solo se citan las fuentes realmente referenciadas (por vista o por fuente).
        sql_low = sql.lower()
        referenciadas: set[str] = {
            vista_a_plantilla[v] for v in vistas_usadas if v in vista_a_plantilla
        }
        for codigo in versiones_por_plantilla:
            if re.search(rf"\b{codigo}\b", sql_low):
                referenciadas.add(codigo)
        versiones = [
            vd for codigo in referenciadas for vd in versiones_por_plantilla.get(codigo, [])
        ]

        # 4. Ejecutar el SQL del usuario.
        try:
            rel = con.sql(sql)
            columnas = list(rel.columns) if rel is not None else []
            tipos = [str(t) for t in rel.types] if rel is not None else []
            filas_raw = rel.fetchall() if rel is not None else []
        except duckdb.Error as exc:
            _auditar(db, usuario.email, sql, vistas_usadas, versiones, 0, False, str(exc))
            raise ConsultaInvalida(str(exc)) from exc

        filas = [[_json_safe(v) for v in fila] for fila in filas_raw]
        bitacora_id = _auditar(
            db, usuario.email, sql, vistas_usadas, versiones, len(filas), True, None
        )
        return ResultadoConsulta(
            columnas=columnas,
            tipos=tipos,
            filas=filas,
            n_filas=len(filas),
            sql_ejecutado=sql,
            vistas_usadas=vistas_usadas,
            versiones_datos=versiones,
            bitacora_id=bitacora_id,
        )
    finally:
        con.close()
