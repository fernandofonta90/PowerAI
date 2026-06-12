"""Consultas del catálogo de cargas con seguridad a nivel de fila (torre × país).

El filtro RBAC lo inyecta el motor de consulta (no se confía en el cliente):
una carga solo es visible si el usuario tiene un grant que cubre su torre y país.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, and_, false, func, or_, select
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.domain.enums import PAIS_TODOS, EstadoCarga, EstadoFrescura, Torre
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.services.frescura import estado_frescura


def condicion_rbac(usuario: UsuarioAutenticado) -> ColumnElement[bool]:
    """Condición SQL que limita las filas a las accesibles por el usuario."""
    condiciones: list[ColumnElement[bool]] = []
    for g in usuario.grants:
        if g.pais == PAIS_TODOS:
            condiciones.append(CargaArchivo.torre == g.torre)
        else:
            condiciones.append(and_(CargaArchivo.torre == g.torre, CargaArchivo.pais == g.pais))
    if not condiciones:
        return false()
    return or_(*condiciones)


def listar_cargas(
    db: Session,
    usuario: UsuarioAutenticado,
    *,
    torre: Torre | None = None,
    pais: str | None = None,
    plantilla_codigo: str | None = None,
) -> list[CargaArchivo]:
    """Lista cargas visibles para el usuario, con filtros opcionales."""
    stmt = select(CargaArchivo).where(condicion_rbac(usuario))
    if torre is not None:
        stmt = stmt.where(CargaArchivo.torre == torre)
    if pais is not None:
        stmt = stmt.where(CargaArchivo.pais == pais)
    if plantilla_codigo is not None:
        stmt = stmt.join(PlantillaReporte).where(PlantillaReporte.codigo == plantilla_codigo)
    stmt = stmt.order_by(CargaArchivo.creado_en.desc())
    return list(db.scalars(stmt).all())


@dataclass
class FrescuraDataset:
    plantilla_codigo: str
    plantilla_nombre: str
    pais: str
    ultima_actualizacion: datetime | None
    estado: EstadoFrescura


def frescura_datasets(
    db: Session,
    usuario: UsuarioAutenticado,
    ahora: datetime,
    *,
    torre: Torre | None = None,
) -> list[FrescuraDataset]:
    """Frescura por (plantilla, país) de los datasets disponibles en el alcance."""
    stmt = (
        select(
            CargaArchivo.plantilla_id,
            CargaArchivo.pais,
            func.max(CargaArchivo.creado_en).label("ultima"),
        )
        .where(condicion_rbac(usuario), CargaArchivo.estado == EstadoCarga.DISPONIBLE)
        .group_by(CargaArchivo.plantilla_id, CargaArchivo.pais)
    )
    if torre is not None:
        stmt = stmt.where(CargaArchivo.torre == torre)

    filas = db.execute(stmt).all()
    if not filas:
        return []

    ids = {f.plantilla_id for f in filas}
    plantillas = {
        p.id: p for p in db.scalars(select(PlantillaReporte).where(PlantillaReporte.id.in_(ids)))
    }

    resultado: list[FrescuraDataset] = []
    for f in filas:
        plantilla = plantillas[f.plantilla_id]
        resultado.append(
            FrescuraDataset(
                plantilla_codigo=plantilla.codigo,
                plantilla_nombre=plantilla.nombre,
                pais=f.pais,
                ultima_actualizacion=f.ultima,
                estado=estado_frescura(plantilla.frecuencia, f.ultima, ahora),
            )
        )
    resultado.sort(key=lambda r: (r.plantilla_codigo, r.pais))
    return resultado
