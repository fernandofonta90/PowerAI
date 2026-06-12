"""Endpoints de carga de archivos, catálogo y frescura (con RBAC torre × país)."""

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.domain.enums import EstadoCarga, EstadoFrescura, Pais, Rol, Torre
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.services.cargas import CargaRechazada, registrar_carga
from app.services.catalogo import frescura_datasets, listar_cargas
from app.storage import get_almacen

router = APIRouter(tags=["cargas"])

_ROLES_CARGA = {Rol.UPLOADER, Rol.ADMIN}


class CargaResponse(BaseModel):
    id: uuid.UUID
    plantilla_codigo: str
    torre: Torre
    pais: str
    periodo: str
    responsable_email: str
    nombre_archivo_original: str
    version: int
    estado: EstadoCarga
    mensaje_error: str | None
    filas: int | None
    creado_en: datetime
    actualizado_en: datetime

    @classmethod
    def desde(cls, carga: CargaArchivo) -> "CargaResponse":
        return cls(
            id=carga.id,
            plantilla_codigo=carga.plantilla.codigo,
            torre=carga.torre,
            pais=carga.pais,
            periodo=carga.periodo,
            responsable_email=carga.responsable_email,
            nombre_archivo_original=carga.nombre_archivo_original,
            version=carga.version,
            estado=carga.estado,
            mensaje_error=carga.mensaje_error,
            filas=carga.filas,
            creado_en=carga.creado_en,
            actualizado_en=carga.actualizado_en,
        )


class FrescuraResponse(BaseModel):
    plantilla_codigo: str
    plantilla_nombre: str
    pais: str
    ultima_actualizacion: datetime | None
    estado: EstadoFrescura


@router.post("/cargas", response_model=CargaResponse, status_code=status.HTTP_202_ACCEPTED)
async def crear_carga(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    plantilla_codigo: Annotated[str, Form()],
    pais: Annotated[Pais, Form()],
    periodo: Annotated[str, Form()],
    archivo: Annotated[UploadFile, File()],
) -> CargaResponse:
    """Recibe un archivo, valida su esquema y encola la normalización a Parquet."""
    plantilla = db.scalar(
        select(PlantillaReporte).where(PlantillaReporte.codigo == plantilla_codigo)
    )
    if plantilla is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plantilla desconocida: {plantilla_codigo}",
        )
    if not usuario.tiene_acceso(plantilla.torre, pais, roles=_ROLES_CARGA):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Sin permiso de carga sobre {plantilla.torre.value} en {pais.value}.",
        )

    datos = await archivo.read()
    try:
        carga = registrar_carga(
            db,
            get_almacen(),
            plantilla=plantilla,
            responsable_email=usuario.email,
            pais=pais.value,
            periodo=periodo.strip(),
            nombre_archivo=archivo.filename or "archivo",
            datos=datos,
        )
    except CargaRechazada as exc:
        raise HTTPException(
            status_code=422,
            detail={"motivo": "carga_rechazada", "errores": exc.errores},
        ) from exc

    return CargaResponse.desde(carga)


@router.get("/cargas/{carga_id}", response_model=CargaResponse)
def obtener_carga(
    carga_id: uuid.UUID,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> CargaResponse:
    """Devuelve el estado de una carga (RBAC torre × país)."""
    carga = db.get(CargaArchivo, carga_id)
    if carga is None or not usuario.tiene_acceso(carga.torre, Pais(carga.pais)):
        # No revelar existencia de cargas fuera del alcance del usuario.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga no encontrada.")
    return CargaResponse.desde(carga)


@router.get("/catalogo", response_model=list[CargaResponse])
def catalogo(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    torre: Torre | None = None,
    pais: Pais | None = None,
    plantilla: str | None = None,
) -> list[CargaResponse]:
    """Lista las cargas visibles para el usuario, con filtros opcionales."""
    cargas = listar_cargas(
        db,
        usuario,
        torre=torre,
        pais=pais.value if pais else None,
        plantilla_codigo=plantilla,
    )
    return [CargaResponse.desde(c) for c in cargas]


@router.get("/catalogo/frescura", response_model=list[FrescuraResponse])
def frescura(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    torre: Torre | None = None,
) -> list[FrescuraResponse]:
    """Frescura por (plantilla, país) de los datasets disponibles en el alcance."""
    ahora = datetime.now(UTC)
    items = frescura_datasets(db, usuario, ahora, torre=torre)
    return [
        FrescuraResponse(
            plantilla_codigo=i.plantilla_codigo,
            plantilla_nombre=i.plantilla_nombre,
            pais=i.pais,
            ultima_actualizacion=i.ultima_actualizacion,
            estado=i.estado,
        )
        for i in items
    ]
