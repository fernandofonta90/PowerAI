"""Agente analítico con tool-calling sobre el catálogo semántico.

Dos herramientas: ``listar_vistas`` (catálogo de la torre del usuario, con
descripciones de negocio) y ``ejecutar_sql`` (pasa por el motor de M3, que aplica
RLS por construcción; solo SELECT, con límite de filas). El loop tiene un máximo
de iteraciones y, si no puede responder con las vistas disponibles, lo dice con
honestidad — nunca inventa. Cada respuesta incluye la citación de fuentes.
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.domain.enums import EstadoFrescura
from app.ia.proveedor import LLMProvider, MensajeChat, ToolSpec
from app.ia.sql_guard import SqlNoPermitido, validar_select
from app.models.carga import CargaArchivo
from app.models.vista import VistaCatalogo
from app.motor.motor import ConsultaInvalida, VersionDato, ejecutar_consulta
from app.motor.parquet_reader import ParquetReader
from app.services.frescura import estado_frescura

_SISTEMA = (
    "Eres el asistente analítico de PowerAI para el SSC Finanzas LATAM. "
    "Respondes preguntas de negocio consultando ÚNICAMENTE las vistas del catálogo "
    "a las que el usuario tiene acceso. Usa la herramienta listar_vistas para "
    "descubrir qué vistas y columnas existen, y ejecutar_sql (solo SELECT de DuckDB) "
    "para obtener los datos. No inventes cifras: si la pregunta no puede responderse "
    "con las vistas disponibles, dilo con claridad. Cita siempre tus fuentes a partir "
    "de los datos consultados. Responde en español, de forma concisa y para negocio."
)

_TOOLS: list[ToolSpec] = [
    ToolSpec(
        nombre="listar_vistas",
        descripcion=(
            "Lista las vistas del catálogo disponibles para el usuario, con su "
            "descripción de negocio y la de cada columna."
        ),
        parametros={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolSpec(
        nombre="ejecutar_sql",
        descripcion=(
            "Ejecuta una consulta SELECT de DuckDB sobre las vistas del catálogo y "
            "devuelve las filas. La seguridad por país/torre ya está aplicada."
        ),
        parametros={
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "Consulta SELECT sobre las vistas del catálogo.",
                }
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
    ),
]


class Fuente(BaseModel):
    archivo: str
    version: int
    fecha_carga: datetime
    responsable: str
    frescura: EstadoFrescura
    plantilla: str
    pais: str
    periodo: str


class Citacion(BaseModel):
    fuentes: list[Fuente]
    sql_ejecutado_ids: list[uuid.UUID]
    vistas_usadas: list[str]


class DatosTabulares(BaseModel):
    columnas: list[str]
    filas: list[list[Any]]


class ResultadoAgente(BaseModel):
    texto: str
    datos_tabulares: DatosTabulares | None = None
    citacion: Citacion


@dataclass
class _Acumulador:
    bitacora_ids: list[uuid.UUID] = field(default_factory=list)
    versiones: list[VersionDato] = field(default_factory=list)
    vistas: set[str] = field(default_factory=set)
    datos: DatosTabulares | None = None


def _vistas_json(db: Session, usuario: UsuarioAutenticado) -> str:
    torres = usuario.torres_accesibles()
    vistas = db.scalars(
        select(VistaCatalogo).where(VistaCatalogo.torre.in_(torres)).order_by(VistaCatalogo.nombre)
    )
    payload = [
        {
            "nombre": v.nombre,
            "titulo": v.titulo,
            "descripcion": v.descripcion,
            "columnas": [c.model_dump() for c in v.columnas],
        }
        for v in vistas
        if v.torre in torres
    ]
    return json.dumps({"vistas": payload}, ensure_ascii=False)


def _ejecutar_sql_tool(
    db: Session,
    usuario: UsuarioAutenticado,
    sql: str,
    max_filas: int,
    acum: _Acumulador,
    reader: ParquetReader | None,
) -> str:
    try:
        validar_select(sql)
    except SqlNoPermitido as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    try:
        resultado = ejecutar_consulta(db, usuario, sql, reader=reader)
    except ConsultaInvalida as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    filas = resultado.filas[:max_filas]
    truncado = resultado.n_filas > max_filas
    if resultado.bitacora_id is not None:
        acum.bitacora_ids.append(resultado.bitacora_id)
    acum.versiones.extend(resultado.versiones_datos)
    acum.vistas.update(resultado.vistas_usadas)
    acum.datos = DatosTabulares(columnas=resultado.columnas, filas=filas)
    return json.dumps(
        {
            "columnas": resultado.columnas,
            "filas": filas,
            "n_filas": resultado.n_filas,
            "truncado": truncado,
        },
        ensure_ascii=False,
        default=str,
    )


def _fuentes(db: Session, versiones: list[VersionDato], ahora: datetime) -> list[Fuente]:
    vistos: dict[tuple[str, str, str, int], Fuente] = {}
    for v in versiones:
        clave = (v.plantilla, v.pais, v.periodo, v.version)
        if clave in vistos:
            continue
        carga = db.scalar(
            select(CargaArchivo)
            .join(CargaArchivo.plantilla)
            .where(
                CargaArchivo.pais == v.pais,
                CargaArchivo.periodo == v.periodo,
                CargaArchivo.version == v.version,
            )
            .where(CargaArchivo.plantilla.has(codigo=v.plantilla))
        )
        if carga is None:
            continue
        vistos[clave] = Fuente(
            archivo=carga.nombre_archivo_original,
            version=carga.version,
            fecha_carga=carga.creado_en,
            responsable=carga.responsable_email,
            frescura=estado_frescura(carga.plantilla.frecuencia, carga.creado_en, ahora),
            plantilla=v.plantilla,
            pais=v.pais,
            periodo=v.periodo,
        )
    return list(vistos.values())


def _resultado(db: Session, texto: str, acum: _Acumulador) -> ResultadoAgente:
    return ResultadoAgente(
        texto=texto,
        datos_tabulares=acum.datos,
        citacion=Citacion(
            fuentes=_fuentes(db, acum.versiones, datetime.now(UTC)),
            sql_ejecutado_ids=acum.bitacora_ids,
            vistas_usadas=sorted(acum.vistas),
        ),
    )


def responder(
    db: Session,
    usuario: UsuarioAutenticado,
    provider: LLMProvider,
    historial: list[MensajeChat],
    pregunta: str,
    *,
    max_iteraciones: int = 5,
    max_filas: int = 1000,
    reader: ParquetReader | None = None,
) -> ResultadoAgente:
    """Ejecuta el loop del agente y devuelve la respuesta con su citación."""
    mensajes: list[MensajeChat] = [
        MensajeChat(rol="system", contenido=_SISTEMA),
        *historial,
        MensajeChat(rol="user", contenido=pregunta),
    ]
    acum = _Acumulador()

    for _ in range(max_iteraciones):
        resp = provider.completar(mensajes, _TOOLS)
        if not resp.tool_calls:
            return _resultado(db, resp.contenido or "", acum)

        mensajes.append(
            MensajeChat(rol="assistant", contenido=resp.contenido, tool_calls=resp.tool_calls)
        )
        for tc in resp.tool_calls:
            if tc.nombre == "listar_vistas":
                salida = _vistas_json(db, usuario)
            elif tc.nombre == "ejecutar_sql":
                salida = _ejecutar_sql_tool(
                    db, usuario, str(tc.argumentos.get("sql", "")), max_filas, acum, reader
                )
            else:
                salida = json.dumps({"error": f"Herramienta desconocida: {tc.nombre}"})
            mensajes.append(MensajeChat(rol="tool", contenido=salida, tool_call_id=tc.id))

    return _resultado(
        db,
        "No pude responder con las vistas disponibles dentro del límite de pasos.",
        acum,
    )
