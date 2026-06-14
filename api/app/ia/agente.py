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
from app.ia.experto import ConfigExperto, cargar_config_activa, construir_system_prompt
from app.ia.proveedor import (
    LLMProvider,
    MensajeChat,
    ProveedorLLMError,
    ToolSpec,
    UsoTokens,
)
from app.ia.sql_guard import SqlNoPermitido, validar_select
from app.models.carga import CargaArchivo
from app.models.vista import VistaCatalogo
from app.motor.motor import ConsultaInvalida, VersionDato, ejecutar_consulta
from app.motor.parquet_reader import ParquetReader
from app.services.frescura import estado_frescura

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
    uso: UsoTokens = UsoTokens()


@dataclass
class _Acumulador:
    bitacora_ids: list[uuid.UUID] = field(default_factory=list)
    versiones: list[VersionDato] = field(default_factory=list)
    vistas: set[str] = field(default_factory=set)
    datos: DatosTabulares | None = None
    tokens_entrada: int = 0
    tokens_salida: int = 0


def _vistas_json(
    db: Session, usuario: UsuarioAutenticado, fuentes_permitidas: frozenset[str] | None
) -> str:
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
        # Las fuentes permitidas del experto acotan qué vistas ve el agente (capa
        # extra sobre el RLS): si está acotado, solo se listan las permitidas.
        and (fuentes_permitidas is None or v.nombre in fuentes_permitidas)
    ]
    return json.dumps({"vistas": payload}, ensure_ascii=False)


def _ejecutar_sql_tool(
    db: Session,
    usuario: UsuarioAutenticado,
    sql: str,
    max_filas: int,
    acum: _Acumulador,
    reader: ParquetReader | None,
    fuentes_permitidas: frozenset[str] | None,
) -> str:
    try:
        validar_select(sql)
    except SqlNoPermitido as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)

    try:
        resultado = ejecutar_consulta(
            db, usuario, sql, reader=reader, vistas_permitidas=fuentes_permitidas
        )
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
        uso=UsoTokens(entrada=acum.tokens_entrada, salida=acum.tokens_salida),
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
    config: ConfigExperto | None = None,
) -> ResultadoAgente:
    """Ejecuta el loop del agente y devuelve la respuesta con su citación.

    El comportamiento (identidad, formato, fuentes) viene de la config del Experto
    de la torre: si no se pasa explícita (p. ej. para validar un borrador), se carga
    la ACTIVA de la torre del usuario. El núcleo estructural (honestidad, gobierno
    del SQL, RLS) es fijo y se inyecta siempre, sin importar la config.
    """
    if config is None:
        config = cargar_config_activa(db, usuario)
    fuentes = config.fuentes_permitidas

    mensajes: list[MensajeChat] = [
        MensajeChat(rol="system", contenido=construir_system_prompt(config)),
        *historial,
        MensajeChat(rol="user", contenido=pregunta),
    ]
    acum = _Acumulador()

    for _ in range(max_iteraciones):
        try:
            resp = provider.completar(mensajes, _TOOLS)
        except ProveedorLLMError:
            # Fallo del servicio de IA tras reintentos: responde con honestidad,
            # sin inventar, conservando lo que se haya podido citar.
            return _resultado(
                db,
                "No pude completar la respuesta por un problema temporal con el "
                "servicio de IA. Intenta de nuevo en unos momentos.",
                acum,
            )
        if resp.uso is not None:
            acum.tokens_entrada += resp.uso.entrada
            acum.tokens_salida += resp.uso.salida
        if not resp.tool_calls:
            return _resultado(db, resp.contenido or "", acum)

        mensajes.append(
            MensajeChat(rol="assistant", contenido=resp.contenido, tool_calls=resp.tool_calls)
        )
        for tc in resp.tool_calls:
            if tc.nombre == "listar_vistas":
                salida = _vistas_json(db, usuario, fuentes)
            elif tc.nombre == "ejecutar_sql":
                salida = _ejecutar_sql_tool(
                    db, usuario, str(tc.argumentos.get("sql", "")), max_filas, acum, reader, fuentes
                )
            else:
                salida = json.dumps({"error": f"Herramienta desconocida: {tc.nombre}"})
            mensajes.append(MensajeChat(rol="tool", contenido=salida, tool_call_id=tc.id))

    return _resultado(
        db,
        "No pude responder con las vistas disponibles dentro del límite de pasos.",
        acum,
    )
