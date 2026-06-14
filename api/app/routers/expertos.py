"""Endpoints de configuración del Experto por torre (M10).

Solo el admin de la torre puede ver/editar la config. "Guardar" no publica:
``/activar`` corre el banco de evals de la torre contra el borrador y solo lo
activa si pasa el umbral. Las reglas estructurales (RLS, anti-invención,
text-to-SQL gobernado) NO se exponen como editables: se devuelven como garantías
fijas para transparencia.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.auth.schemas import UsuarioAutenticado
from app.config import get_settings
from app.db import get_db
from app.domain.enums import Torre
from app.ia.experto import GARANTIAS_ESTRUCTURALES
from app.ia.proveedor import get_llm_provider
from app.models.experto import ExpertoTorre
from app.models.vista import VistaCatalogo
from app.services.expertos import (
    ConfigInvalida,
    activar_borrador,
    es_admin_torre,
    get_activo,
    get_borrador,
    guardar_borrador,
)

router = APIRouter(tags=["expertos"])


class ConfigExpertoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    identidad: str = Field(min_length=1)
    instrucciones_formato: str = ""
    fuentes: list[str] = []


class ConfigExpertoOut(BaseModel):
    nombre: str
    identidad: str
    instrucciones_formato: str
    fuentes: list[str]
    estado: str
    version: int

    @classmethod
    def desde(cls, e: ExpertoTorre) -> "ConfigExpertoOut":
        return cls(
            nombre=e.nombre,
            identidad=e.identidad,
            instrucciones_formato=e.instrucciones_formato,
            fuentes=sorted(e.nombres_fuentes),
            estado=e.estado,
            version=e.version,
        )


class VistaOut(BaseModel):
    nombre: str
    titulo: str
    descripcion: str


class FalloEvalOut(BaseModel):
    id: str
    fraseo: str
    motivo: str


class ReporteEvalOut(BaseModel):
    total: int
    aprobadas: int
    tasa: float
    fallos: list[FalloEvalOut]


class ActivacionResponse(BaseModel):
    activado: bool
    motivo: str
    version: int | None = None
    reporte: ReporteEvalOut | None = None


class ExpertoScreenResponse(BaseModel):
    torre: str
    activo: ConfigExpertoOut | None
    borrador: ConfigExpertoOut | None
    vistas_torre: list[VistaOut]
    garantias_estructurales: list[str]


def _exigir_admin(usuario: UsuarioAutenticado, torre: Torre) -> None:
    if not es_admin_torre(usuario, torre):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Se requiere rol admin sobre la torre {torre.value}.",
        )


def _vistas_torre(db: Session, torre: Torre) -> list[VistaOut]:
    vistas = db.scalars(
        select(VistaCatalogo).where(VistaCatalogo.torre == torre).order_by(VistaCatalogo.nombre)
    )
    return [VistaOut(nombre=v.nombre, titulo=v.titulo, descripcion=v.descripcion) for v in vistas]


@router.get("/torres/{torre}/experto", response_model=ExpertoScreenResponse)
def obtener_experto(
    torre: Torre, usuario: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> ExpertoScreenResponse:
    _exigir_admin(usuario, torre)
    activo = get_activo(db, torre)
    borrador = get_borrador(db, torre)
    return ExpertoScreenResponse(
        torre=torre.value,
        activo=ConfigExpertoOut.desde(activo) if activo else None,
        borrador=ConfigExpertoOut.desde(borrador) if borrador else None,
        vistas_torre=_vistas_torre(db, torre),
        garantias_estructurales=GARANTIAS_ESTRUCTURALES,
    )


@router.put("/torres/{torre}/experto/borrador", response_model=ConfigExpertoOut)
def guardar(
    torre: Torre,
    cuerpo: ConfigExpertoIn,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConfigExpertoOut:
    """Guarda el borrador (sin validar ni activar)."""
    _exigir_admin(usuario, torre)
    try:
        borrador = guardar_borrador(
            db,
            torre,
            nombre=cuerpo.nombre,
            identidad=cuerpo.identidad,
            instrucciones_formato=cuerpo.instrucciones_formato,
            fuentes=cuerpo.fuentes,
        )
    except ConfigInvalida as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ConfigExpertoOut.desde(borrador)


@router.post("/torres/{torre}/experto/activar", response_model=ActivacionResponse)
def activar(
    torre: Torre,
    cuerpo: ConfigExpertoIn,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ActivacionResponse:
    """Guarda el borrador, lo valida contra los evals de la torre y lo activa si pasa."""
    _exigir_admin(usuario, torre)
    try:
        guardar_borrador(
            db,
            torre,
            nombre=cuerpo.nombre,
            identidad=cuerpo.identidad,
            instrucciones_formato=cuerpo.instrucciones_formato,
            fuentes=cuerpo.fuentes,
        )
    except ConfigInvalida as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    s = get_settings()
    resultado = activar_borrador(
        db,
        get_llm_provider(),
        torre,
        max_iteraciones=s.agente_max_iteraciones,
        max_filas=s.agente_max_filas,
    )
    reporte_out = None
    if resultado.reporte is not None:
        r = resultado.reporte
        reporte_out = ReporteEvalOut(
            total=r.total,
            aprobadas=r.aprobadas,
            tasa=r.tasa,
            fallos=[FalloEvalOut(id=f.id, fraseo=f.fraseo, motivo=f.motivo) for f in r.fallos],
        )
    return ActivacionResponse(
        activado=resultado.activado,
        motivo=resultado.motivo,
        version=resultado.version,
        reporte=reporte_out,
    )
