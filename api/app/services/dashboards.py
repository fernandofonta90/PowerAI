"""Servicio de dashboards: persistencia y render (re-ejecución contra datos frescos).

Toda query de la spec pasa por el motor de M3 (RLS por construcción): un dashboard
jamás muestra datos fuera del alcance torre × país del usuario que lo abre.
"""

from typing import Any

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.schemas import UsuarioAutenticado
from app.dashboards.spec import DashboardSpec, validar_spec
from app.domain.enums import Torre
from app.models.dashboard import Dashboard
from app.motor.motor import ConsultaInvalida, ejecutar_consulta
from app.motor.parquet_reader import ParquetReader


class VisualRenderizado(BaseModel):
    tipo: str
    titulo: str
    columna_valor: str | None
    eje_x: str | None
    eje_y: str | None
    formato: str
    columnas: list[str]
    filas: list[list[Any]]
    error: str | None = None


class DashboardRenderizado(BaseModel):
    id: str
    nombre: str
    torre: Torre
    filtros: dict[str, Any]
    titulo: str
    visuales: list[VisualRenderizado]


def crear_dashboard(
    db: Session,
    usuario: UsuarioAutenticado,
    *,
    nombre: str,
    torre: Torre,
    spec: DashboardSpec,
    filtros: dict[str, Any],
) -> Dashboard:
    """Persiste un dashboard. El usuario debe tener acceso a la torre."""
    if torre not in usuario.torres_accesibles():
        raise PermissionError(f"Sin acceso a la torre {torre.value}.")
    dashboard = Dashboard(
        nombre=nombre,
        torre=torre,
        owner_email=usuario.email,
        spec_json=spec.model_dump(mode="json"),
        filtros_json=filtros,
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    return dashboard


def render_dashboard(
    db: Session,
    usuario: UsuarioAutenticado,
    dashboard: Dashboard,
    *,
    reader: ParquetReader | None = None,
) -> DashboardRenderizado:
    """Re-ejecuta las queries de la spec contra los datos más recientes (RLS)."""
    spec = validar_spec(dashboard.spec_json)
    visuales: list[VisualRenderizado] = []
    for v in spec.visuales:
        columnas: list[str] = []
        filas: list[list[Any]] = []
        error: str | None = None
        try:
            r = ejecutar_consulta(db, usuario, v.sql, reader=reader)
            columnas, filas = r.columnas, r.filas
        except ConsultaInvalida as exc:
            error = str(exc)
        visuales.append(
            VisualRenderizado(
                tipo=v.tipo.value,
                titulo=v.titulo,
                columna_valor=v.columna_valor,
                eje_x=v.eje_x,
                eje_y=v.eje_y,
                formato=v.formato.value,
                columnas=columnas,
                filas=filas,
                error=error,
            )
        )
    return DashboardRenderizado(
        id=str(dashboard.id),
        nombre=dashboard.nombre,
        torre=dashboard.torre,
        filtros=dashboard.filtros_json,
        titulo=spec.titulo,
        visuales=visuales,
    )
