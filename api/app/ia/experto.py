"""Configuración del Experto por torre y composición del system prompt (M10).

El comportamiento del agente deja de estar hardcodeado: se construye desde la
configuración ACTIVA del Experto de la torre del usuario. Pero la separación es
inviolable:

- CONFIGURABLE (vive en ``ExpertoTorre``, lo edita el admin): identidad/tono e
  instrucciones de formato (este módulo las inyecta), y las fuentes permitidas.
- ESTRUCTURAL (vive aquí como texto FIJO, no editable desde ningún formulario):
  consultar solo vistas curadas del catálogo, el RLS lo aplica el motor, y la
  honestidad ante métricas no soportadas. ``_BASE_ESTRUCTURAL`` se inyecta SIEMPRE
  entre la identidad y el formato, sin importar la config.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.domain.enums import EstadoExperto, Torre

if TYPE_CHECKING:
    from app.models.experto import ExpertoTorre

# --- Núcleo estructural (NO configurable): se inyecta en todo prompt del agente.
_BASE_ESTRUCTURAL = (
    "Respondes ÚNICAMENTE consultando las vistas del catálogo a las que el usuario "
    "tiene acceso, mediante las herramientas disponibles: listar_vistas (para "
    "descubrir qué vistas y columnas existen) y ejecutar_sql (solo SELECT de DuckDB, "
    "para obtener los datos). La seguridad por torre y país (RLS) la aplica el motor; "
    "tú no la gestionas ni la puedes desactivar. No inventes cifras: si la pregunta no "
    "puede responderse con las vistas disponibles, dilo con claridad. Cita siempre tus "
    "fuentes a partir de los datos consultados.\n"
    "HONESTIDAD ANTE MÉTRICAS NO SOPORTADAS: si la métrica o el dato pedido NO mapea a "
    "una columna existente de las vistas del catálogo, es una pregunta NO respondible: "
    "declara explícitamente que no puedes responderla con las vistas disponibles y NO "
    "ejecutes SQL. NUNCA sustituyas la métrica pedida por otra: aproximar es inventar."
)

# Garantías estructurales que la UI muestra como fijas (transparencia). Son la cara
# visible de _BASE_ESTRUCTURAL y del motor; ninguna es editable.
GARANTIAS_ESTRUCTURALES: list[str] = [
    "Seguridad a nivel de fila (torre × país): cada consulta ve solo los datos del "
    "alcance del usuario. La aplica el motor; no es configurable.",
    "Text-to-SQL gobernado: el experto solo consulta vistas curadas del catálogo, "
    "nunca tablas crudas. No es configurable.",
    "Honestidad ante métricas no soportadas: si el dato no existe en el catálogo, el "
    "experto lo declara y no inventa ni aproxima. No es configurable.",
]

# --- Configuración por defecto del Experto OTC (extraída del prompt hardcodeado).
# La usa el seed (registro activo inicial) y el fallback si una torre no tiene experto.
NOMBRE_OTC = "Experto OTC"
IDENTIDAD_OTC = (
    "Eres el asistente analítico de PowerAI para el SSC Finanzas LATAM, especializado "
    "en la torre OTC (Order to Cash). Respondes preguntas de negocio en español, de "
    "forma concisa y orientada a negocio. Ten presente que el catálogo de OTC no tiene "
    "datos de costo, por lo que no puedes calcular rentabilidad, margen ni utilidad."
)
FORMATO_OTC = (
    "Reglas para el SQL que generes:\n"
    "- Selecciona SOLO las columnas que la pregunta pide; no agregues columnas de "
    "contexto (moneda, descripción, fechas) salvo que se pidan explícitamente.\n"
    "- Si la pregunta pide un único valor agregado (un total, una suma, un conteo), "
    "devuelve UNA sola columna con ese valor, sin agrupar por otras columnas.\n"
    "- Para la antigüedad de la cartera (aging) usa exactamente estos tramos por días "
    "vencidos: 'corriente' (=0), '1-30' (1 a 30), '31-60' (31 a 60) y '60+' (más de "
    "60), una fila por tramo con la suma de monto."
)

# Fallback genérico cuando una torre no tiene experto activo (evita romper el agente).
_IDENTIDAD_GENERICA = (
    "Eres el asistente analítico de PowerAI para el SSC Finanzas LATAM. Respondes "
    "preguntas de negocio en español, de forma concisa y orientada a negocio."
)


@dataclass(frozen=True)
class ConfigExperto:
    """Configuración efectiva que el agente usa para una respuesta.

    ``fuentes_permitidas`` None significa "todas las vistas accesibles del usuario"
    (no hay restricción extra del experto sobre el RLS); un conjunto las acota.
    """

    torre: Torre | None
    nombre: str
    identidad: str
    instrucciones_formato: str
    fuentes_permitidas: frozenset[str] | None = field(default=None)


def construir_system_prompt(config: ConfigExperto) -> str:
    """Compone identidad (config) + base estructural (FIJA) + formato (config).

    La base estructural va SIEMPRE en medio: ni la identidad ni el formato pueden
    sustituirla, así un experto no puede editar la honestidad ni el gobierno del SQL.
    """
    partes = [config.identidad.strip(), _BASE_ESTRUCTURAL]
    formato = config.instrucciones_formato.strip()
    if formato:
        partes.append(formato)
    return "\n".join(partes)


def config_fallback(torre: Torre | None = None) -> ConfigExperto:
    """Config genérica cuando no hay experto activo para la torre."""
    return ConfigExperto(
        torre=torre,
        nombre="Asistente PowerAI",
        identidad=_IDENTIDAD_GENERICA,
        instrucciones_formato="",
        fuentes_permitidas=None,
    )


def config_desde_experto(experto: ExpertoTorre) -> ConfigExperto:
    """Construye la ConfigExperto a partir de un registro ExpertoTorre."""
    return ConfigExperto(
        torre=experto.torre,
        nombre=experto.nombre,
        identidad=experto.identidad,
        instrucciones_formato=experto.instrucciones_formato,
        fuentes_permitidas=frozenset(experto.nombres_fuentes),
    )


def cargar_config_activa(db: Session, usuario: UsuarioAutenticado) -> ConfigExperto:
    """Resuelve la ConfigExperto activa para la torre del usuario.

    Si el usuario tiene varias torres con experto activo, se elige de forma
    determinista (orden por valor de torre). Si ninguna torre tiene experto activo,
    devuelve el fallback genérico. (Hoy solo OTC tiene experto activo.)
    """
    from app.models.experto import ExpertoTorre

    torres = usuario.torres_accesibles()
    if not torres:
        return config_fallback()
    experto = db.scalars(
        select(ExpertoTorre)
        .where(
            ExpertoTorre.torre.in_(torres),
            ExpertoTorre.estado == EstadoExperto.ACTIVO,
        )
        .order_by(ExpertoTorre.torre)
    ).first()
    if experto is None:
        return config_fallback(next(iter(sorted(torres, key=lambda t: t.value))))
    return config_desde_experto(experto)
