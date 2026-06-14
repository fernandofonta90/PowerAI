"""Servicio del Experto configurable por torre (M10).

Reúne la configuración con sus barandales: edición del borrador, validación contra
el banco de evals de la torre y activación versionada. "Guardar" NO publica: una
config solo se activa si sus evals pasan el umbral; la activa anterior se archiva
(rollback posible).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.provider import MockAuthProvider
from app.auth.schemas import UsuarioAutenticado
from app.domain.enums import EstadoExperto, Rol, Torre
from app.evals.banco import PreguntaDorada, cargar_banco
from app.evals.runner import UMBRAL_AGENTE, ReporteEval, evaluar_agente
from app.ia.experto import config_desde_experto
from app.ia.proveedor import LLMProvider
from app.models.experto import ExpertoTorre
from app.models.vista import VistaCatalogo
from app.motor.parquet_reader import ParquetReader


class ConfigInvalida(Exception):
    """La configuración propuesta del experto no es válida (p. ej. fuente ajena)."""


@dataclass
class ResultadoActivacion:
    activado: bool
    motivo: str
    reporte: ReporteEval | None = None
    version: int | None = None


def es_admin_torre(usuario: UsuarioAutenticado, torre: Torre) -> bool:
    """¿El usuario es admin de la torre? (rol ADMIN en cualquier país de la torre)."""
    return any(g.torre == torre and g.rol == Rol.ADMIN for g in usuario.grants)


def get_activo(db: Session, torre: Torre) -> ExpertoTorre | None:
    return db.scalars(
        select(ExpertoTorre).where(
            ExpertoTorre.torre == torre, ExpertoTorre.estado == EstadoExperto.ACTIVO
        )
    ).first()


def get_borrador(db: Session, torre: Torre) -> ExpertoTorre | None:
    return db.scalars(
        select(ExpertoTorre).where(
            ExpertoTorre.torre == torre, ExpertoTorre.estado == EstadoExperto.BORRADOR
        )
    ).first()


def _resolver_fuentes(db: Session, torre: Torre, nombres: list[str]) -> list[VistaCatalogo]:
    """Resuelve nombres de vista a registros de la torre; rechaza fuentes ajenas."""
    if not nombres:
        return []
    vistas = list(
        db.scalars(
            select(VistaCatalogo).where(
                VistaCatalogo.torre == torre, VistaCatalogo.nombre.in_(nombres)
            )
        )
    )
    encontrados = {v.nombre for v in vistas}
    faltan = set(nombres) - encontrados
    if faltan:
        raise ConfigInvalida(
            f"Fuentes no válidas para la torre {torre.value}: {sorted(faltan)}. "
            "Solo se pueden elegir vistas del catálogo de la torre."
        )
    return vistas


def guardar_borrador(
    db: Session,
    torre: Torre,
    *,
    nombre: str,
    identidad: str,
    instrucciones_formato: str,
    fuentes: list[str],
) -> ExpertoTorre:
    """Crea o actualiza el borrador de la torre (NO valida ni activa)."""
    vistas = _resolver_fuentes(db, torre, fuentes)
    borrador = get_borrador(db, torre)
    if borrador is None:
        siguiente = (
            db.scalar(select(func.max(ExpertoTorre.version)).where(ExpertoTorre.torre == torre))
            or 0
        ) + 1
        borrador = ExpertoTorre(torre=torre, version=siguiente, estado=EstadoExperto.BORRADOR)
        db.add(borrador)
    borrador.nombre = nombre
    borrador.identidad = identidad
    borrador.instrucciones_formato = instrucciones_formato
    borrador.fuentes = vistas
    db.commit()
    db.refresh(borrador)
    return borrador


def preguntas_de_torre(db: Session, torre: Torre) -> list[PreguntaDorada]:
    """Preguntas doradas cuya usuario-de-evals tiene acceso a la torre."""
    auth = MockAuthProvider()
    seleccion: list[PreguntaDorada] = []
    for p in cargar_banco():
        try:
            usuario = auth.autenticar(db, p.usuario)
        except Exception:  # noqa: BLE001 - usuario de evals no sembrado: se omite
            continue
        if torre in usuario.torres_accesibles():
            seleccion.append(p)
    return seleccion


def validar_borrador(
    db: Session,
    provider: LLMProvider,
    torre: Torre,
    *,
    max_iteraciones: int = 5,
    max_filas: int = 1000,
    reader: ParquetReader | None = None,
) -> tuple[ReporteEval | None, ExpertoTorre]:
    """Corre el banco de evals de la torre contra el borrador. NO activa."""
    borrador = get_borrador(db, torre)
    if borrador is None:
        raise ConfigInvalida("No hay borrador que validar para esta torre.")
    preguntas = preguntas_de_torre(db, torre)
    if not preguntas:
        return None, borrador
    reporte = evaluar_agente(
        db,
        provider,
        preguntas,
        max_iteraciones=max_iteraciones,
        max_filas=max_filas,
        reader=reader,
        config=config_desde_experto(borrador),
    )
    return reporte, borrador


def activar_borrador(
    db: Session,
    provider: LLMProvider,
    torre: Torre,
    *,
    max_iteraciones: int = 5,
    max_filas: int = 1000,
    reader: ParquetReader | None = None,
) -> ResultadoActivacion:
    """Valida el borrador con evals y SOLO lo activa si pasa el umbral.

    Si pasa: la config activa anterior pasa a ARCHIVADO y el borrador a ACTIVO
    (rollback posible). Si no pasa, el borrador queda intacto y se reporta el fallo.
    """
    reporte, borrador = validar_borrador(
        db, provider, torre, max_iteraciones=max_iteraciones, max_filas=max_filas, reader=reader
    )
    if reporte is None:
        return ResultadoActivacion(
            activado=False,
            motivo=(
                f"No hay banco de evals para la torre {torre.value}: no se puede validar "
                "ni activar la configuración (barandal de seguridad)."
            ),
        )
    if reporte.tasa < UMBRAL_AGENTE:
        return ResultadoActivacion(
            activado=False,
            motivo=(
                f"La configuración no se activó: los evals dieron {reporte.tasa:.1%}, "
                f"por debajo del umbral requerido ({UMBRAL_AGENTE:.0%})."
            ),
            reporte=reporte,
        )

    activo = get_activo(db, torre)
    if activo is not None:
        activo.estado = EstadoExperto.ARCHIVADO
    borrador.estado = EstadoExperto.ACTIVO
    db.commit()
    db.refresh(borrador)
    return ResultadoActivacion(
        activado=True,
        motivo=f"Configuración activada (evals {reporte.tasa:.1%}).",
        reporte=reporte,
        version=borrador.version,
    )
