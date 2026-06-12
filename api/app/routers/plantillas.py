"""Endpoint de consulta de plantillas de reporte (filtrado por torre accesible)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.domain.columnas import ColumnaSpec
from app.domain.enums import Frecuencia, Torre
from app.models.plantilla import PlantillaReporte

router = APIRouter(tags=["plantillas"])


class PlantillaResponse(BaseModel):
    codigo: str
    nombre: str
    torre: Torre
    descripcion: str
    frecuencia: Frecuencia
    columna_pais: str
    columna_periodo: str
    columnas: list[ColumnaSpec]


@router.get("/plantillas", response_model=list[PlantillaResponse])
def listar_plantillas(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    torre: Torre | None = None,
) -> list[PlantillaResponse]:
    """Lista las plantillas de las torres a las que el usuario tiene acceso."""
    accesibles = usuario.torres_accesibles()

    stmt = select(PlantillaReporte).order_by(PlantillaReporte.codigo)
    if torre is not None:
        stmt = stmt.where(PlantillaReporte.torre == torre)

    return [
        PlantillaResponse(
            codigo=p.codigo,
            nombre=p.nombre,
            torre=p.torre,
            descripcion=p.descripcion,
            frecuencia=p.frecuencia,
            columna_pais=p.columna_pais,
            columna_periodo=p.columna_periodo,
            columnas=p.columnas,
        )
        for p in db.scalars(stmt)
        if p.torre in accesibles
    ]
