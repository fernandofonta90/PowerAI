"""Endpoints de dashboards (ADR-0004) con RBAC de propietario y de torre."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.auth.schemas import UsuarioAutenticado
from app.config import get_settings
from app.dashboards.generador import generar_spec
from app.dashboards.spec import SpecInvalida, validar_spec
from app.db import get_db
from app.domain.enums import Torre
from app.ia.proveedor import get_llm_provider
from app.models.dashboard import Dashboard
from app.services.dashboards import DashboardRenderizado, crear_dashboard, render_dashboard

router = APIRouter(tags=["dashboards"])


class GenerarRequest(BaseModel):
    peticion: str


class GenerarResponse(BaseModel):
    spec: dict[str, Any] | None
    mensaje: str


class CrearRequest(BaseModel):
    nombre: str
    torre: Torre
    spec: dict[str, Any]
    filtros: dict[str, Any] = {}


class DashboardMeta(BaseModel):
    id: uuid.UUID
    nombre: str
    torre: Torre
    creado_en: datetime


class RenombrarRequest(BaseModel):
    nombre: str


def _dashboard_propio(
    db: Session, usuario: UsuarioAutenticado, dashboard_id: uuid.UUID
) -> Dashboard:
    d = db.get(Dashboard, dashboard_id)
    if d is None or d.owner_email != usuario.email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado.")
    return d


@router.post("/dashboards/generar", response_model=GenerarResponse)
def generar(
    cuerpo: GenerarRequest,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> GenerarResponse:
    """Genera (sin persistir) una spec de dashboard desde una petición NL."""
    s = get_settings()
    resultado = generar_spec(
        db, usuario, get_llm_provider(), cuerpo.peticion, max_iteraciones=s.agente_max_iteraciones
    )
    return GenerarResponse(
        spec=resultado.spec.model_dump(mode="json") if resultado.spec else None,
        mensaje=resultado.mensaje,
    )


@router.post("/dashboards", response_model=DashboardMeta, status_code=status.HTTP_201_CREATED)
def crear(
    cuerpo: CrearRequest,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> DashboardMeta:
    """Crea un dashboard desde una spec (generada o manual)."""
    try:
        spec = validar_spec(cuerpo.spec)
    except SpecInvalida as exc:
        raise HTTPException(
            status_code=422, detail={"motivo": "spec_invalida", "error": str(exc)}
        ) from exc
    try:
        d = crear_dashboard(
            db, usuario, nombre=cuerpo.nombre, torre=cuerpo.torre, spec=spec, filtros=cuerpo.filtros
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return DashboardMeta(id=d.id, nombre=d.nombre, torre=d.torre, creado_en=d.creado_en)


@router.get("/dashboards", response_model=list[DashboardMeta])
def listar(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[DashboardMeta]:
    dashboards = db.scalars(
        select(Dashboard)
        .where(Dashboard.owner_email == usuario.email)
        .order_by(Dashboard.creado_en.desc())
    )
    return [
        DashboardMeta(id=d.id, nombre=d.nombre, torre=d.torre, creado_en=d.creado_en)
        for d in dashboards
    ]


@router.get("/dashboards/{dashboard_id}", response_model=DashboardRenderizado)
def obtener(
    dashboard_id: uuid.UUID,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> DashboardRenderizado:
    """Devuelve el dashboard con sus visuales re-ejecutados contra datos frescos."""
    d = _dashboard_propio(db, usuario, dashboard_id)
    return render_dashboard(db, usuario, d)


@router.patch("/dashboards/{dashboard_id}", response_model=DashboardMeta)
def renombrar(
    dashboard_id: uuid.UUID,
    cuerpo: RenombrarRequest,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> DashboardMeta:
    d = _dashboard_propio(db, usuario, dashboard_id)
    d.nombre = cuerpo.nombre
    db.commit()
    db.refresh(d)
    return DashboardMeta(id=d.id, nombre=d.nombre, torre=d.torre, creado_en=d.creado_en)


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    dashboard_id: uuid.UUID,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    d = _dashboard_propio(db, usuario, dashboard_id)
    db.delete(d)
    db.commit()
