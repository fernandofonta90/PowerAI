"""Generación de dashboards por IA (ADR-0004).

Un flujo de agente con tool-calling produce una SPEC declarativa validada a partir
de una petición en lenguaje natural. Reusa el catálogo semántico y la honestidad ya
blindada: si la métrica pedida no mapea a una columna del catálogo (rentabilidad,
margen, costo), lo declara en vez de inventar visuales. Cada query de la spec se
valida ejecutándola por el motor (RLS por construcción).
"""

import json
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.dashboards.spec import DashboardSpec, SpecInvalida, validar_spec
from app.ia.proveedor import (
    LLMProvider,
    MensajeChat,
    ProveedorLLMError,
    ToolSpec,
)
from app.models.vista import VistaCatalogo
from app.motor.motor import ConsultaInvalida, ejecutar_consulta
from app.motor.parquet_reader import ParquetReader

_SISTEMA = (
    "Eres el generador de dashboards de PowerAI. A partir de una petición de negocio, "
    "produces una especificación declarativa de dashboard (NO código) sobre las vistas "
    "del catálogo a las que el usuario tiene acceso. Usa listar_vistas para conocer las "
    "vistas y columnas, y luego llama proponer_spec con la especificación.\n"
    "- Cada visual lleva una consulta SELECT de DuckDB sobre las vistas; usa solo "
    "columnas existentes.\n"
    "- Tipos de visual: kpi (valor único, requiere columna_valor), tabla, barras, "
    "lineas, distribucion (estos tres requieren eje_x y eje_y).\n"
    "- Para montos usa formato 'decimal'.\n"
    "- HONESTIDAD: si la petición pide una métrica que no existe en el catálogo "
    "(rentabilidad, margen, costo — no hay datos de costo), NO inventes visuales: "
    "responde con texto explicando que no puede generarse con las vistas disponibles."
)

_SCHEMA_SPEC = {
    "type": "object",
    "properties": {
        "version": {"type": "integer", "enum": [1]},
        "titulo": {"type": "string"},
        "visuales": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tipo": {
                        "type": "string",
                        "enum": ["kpi", "tabla", "barras", "lineas", "distribucion"],
                    },
                    "titulo": {"type": "string"},
                    "sql": {"type": "string"},
                    "columna_valor": {"type": ["string", "null"]},
                    "eje_x": {"type": ["string", "null"]},
                    "eje_y": {"type": ["string", "null"]},
                    "formato": {
                        "type": "string",
                        "enum": ["entero", "decimal", "texto"],
                    },
                },
                "required": ["tipo", "titulo", "sql"],
            },
        },
    },
    "required": ["titulo", "visuales"],
}

_TOOLS: list[ToolSpec] = [
    ToolSpec(
        nombre="listar_vistas",
        descripcion="Lista las vistas del catálogo del usuario, con descripción por columna.",
        parametros={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    ToolSpec(
        nombre="proponer_spec",
        descripcion="Propone la especificación del dashboard para validarla y guardarla.",
        parametros=_SCHEMA_SPEC,
    ),
]


class ResultadoGeneracion(BaseModel):
    spec: DashboardSpec | None = None
    mensaje: str


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


def _validar_spec_y_queries(
    db: Session,
    usuario: UsuarioAutenticado,
    args: dict[str, Any],
    reader: ParquetReader | None,
) -> tuple[DashboardSpec | None, str]:
    """Valida la spec y que cada query corra por el motor. Devuelve (spec|None, error)."""
    try:
        spec = validar_spec(args)
    except SpecInvalida as exc:
        return None, f"Spec inválida: {exc}"
    for visual in spec.visuales:
        try:
            ejecutar_consulta(db, usuario, visual.sql, reader=reader)
        except ConsultaInvalida as exc:
            return None, f"La query del visual '{visual.titulo}' falló: {exc}"
    return spec, ""


def generar_spec(
    db: Session,
    usuario: UsuarioAutenticado,
    provider: LLMProvider,
    peticion: str,
    *,
    max_iteraciones: int = 5,
    reader: ParquetReader | None = None,
) -> ResultadoGeneracion:
    """Genera una spec de dashboard validada a partir de la petición NL."""
    mensajes: list[MensajeChat] = [
        MensajeChat(rol="system", contenido=_SISTEMA),
        MensajeChat(rol="user", contenido=peticion),
    ]
    for _ in range(max_iteraciones):
        try:
            resp = provider.completar(mensajes, _TOOLS)
        except ProveedorLLMError:
            return ResultadoGeneracion(
                mensaje="No pude generar el dashboard por un problema con el servicio de IA."
            )
        if not resp.tool_calls:
            return ResultadoGeneracion(mensaje=resp.contenido or "")
        mensajes.append(
            MensajeChat(rol="assistant", contenido=resp.contenido, tool_calls=resp.tool_calls)
        )
        for tc in resp.tool_calls:
            if tc.nombre == "listar_vistas":
                salida = _vistas_json(db, usuario)
            elif tc.nombre == "proponer_spec":
                spec, error = _validar_spec_y_queries(db, usuario, tc.argumentos, reader)
                if spec is not None:
                    return ResultadoGeneracion(
                        spec=spec, mensaje=f"Dashboard generado: {spec.titulo}."
                    )
                salida = json.dumps({"error": error}, ensure_ascii=False)
            else:
                salida = json.dumps({"error": f"Herramienta desconocida: {tc.nombre}"})
            mensajes.append(MensajeChat(rol="tool", contenido=salida, tool_call_id=tc.id))
    return ResultadoGeneracion(
        mensaje="No pude generar un dashboard válido dentro del límite de pasos."
    )
