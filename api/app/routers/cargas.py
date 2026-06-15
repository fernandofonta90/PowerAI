"""Endpoints de carga de archivos, catálogo y frescura (con RBAC torre × país)."""

import json
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
from app.ingesta.lector import ArchivoIlegible
from app.models.carga import CargaArchivo
from app.models.plantilla import PlantillaReporte
from app.services.cargas import CargaRechazada, registrar_carga
from app.services.catalogo import frescura_datasets, listar_cargas
from app.services.plantillas import (
    CandidataPlantilla,
    emparejar,
    inspeccionar,
    puede_definir,
)
from app.storage import get_almacen

router = APIRouter(tags=["cargas"])

_ROLES_CARGA = {Rol.UPLOADER, Rol.ADMIN}


class PlantillaCandidataResponse(BaseModel):
    codigo: str
    nombre: str
    columnas_esperadas: list[str]
    columna_pais: str | None
    columna_periodo: str | None
    faltantes: list[str]
    extra: list[str]
    calza: bool


class InspeccionResponse(BaseModel):
    columnas: list[str]
    filas_muestra: list[list[str]]
    # Tipo sugerido por columna (la UI lo pre-selecciona; el usuario confirma).
    tipos_sugeridos: dict[str, str]
    # Plantilla cuyo esquema calza tal cual (flujo B directo), si existe.
    calce: PlantillaCandidataResponse | None
    # Todas las plantillas de la torre con su diff (para mapear o decidir crear).
    candidatas: list[PlantillaCandidataResponse]


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


def _candidata(c: CandidataPlantilla) -> PlantillaCandidataResponse:
    return PlantillaCandidataResponse(
        codigo=c.plantilla.codigo,
        nombre=c.plantilla.nombre,
        # Encabezados reales que la plantilla espera (para mapear el archivo nuevo).
        columnas_esperadas=[col.etiqueta for col in c.plantilla.columnas],
        columna_pais=c.plantilla.columna_pais,
        columna_periodo=c.plantilla.columna_periodo,
        faltantes=c.faltantes,
        extra=c.extra,
        calza=c.calza,
    )


@router.post("/cargas/inspeccionar", response_model=InspeccionResponse)
async def inspeccionar_archivo(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    torre: Annotated[Torre, Form()],
    archivo: Annotated[UploadFile, File()],
) -> InspeccionResponse:
    """Lee encabezados (sin procesar) y los compara con las plantillas de la torre.

    Decide el flujo: si una plantilla calza → flujo B (previsualizar y guardar); si
    ninguna calza → flujo A (crear plantilla) o mapear contra una candidata cercana.
    """
    if not puede_definir(usuario, torre):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Se requiere rol admin o uploader sobre la torre {torre.value}.",
        )
    datos = await archivo.read()
    try:
        insp = inspeccionar(datos, archivo.filename or "archivo")
    except ArchivoIlegible as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    candidatas = emparejar(db, torre, insp.columnas)
    calce = next((c for c in candidatas if c.calza), None)
    return InspeccionResponse(
        columnas=insp.columnas,
        filas_muestra=insp.filas_muestra,
        tipos_sugeridos={c: t.value for c, t in insp.tipos_sugeridos.items()},
        calce=_candidata(calce) if calce else None,
        candidatas=[_candidata(c) for c in candidatas],
    )


@router.post("/cargas", response_model=CargaResponse, status_code=status.HTTP_202_ACCEPTED)
async def crear_carga(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    plantilla_codigo: Annotated[str, Form()],
    pais: Annotated[Pais, Form()],
    periodo: Annotated[str, Form()],
    archivo: Annotated[UploadFile, File()],
    mapeo: Annotated[str | None, Form()] = None,
) -> CargaResponse:
    """Recibe un archivo, valida su esquema y encola la normalización a Parquet.

    ``mapeo`` (JSON opcional, {columna_esperada: columna_en_archivo}) acomoda un
    archivo que no calza con la plantilla; nunca redefine el molde.
    """
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

    mapeo_dict: dict[str, str] | None = None
    if mapeo:
        try:
            cargado = json.loads(mapeo)
            if not isinstance(cargado, dict):
                raise ValueError
            mapeo_dict = {str(k): str(v) for k, v in cargado.items()}
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="mapeo no es un JSON válido."
            ) from exc

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
            mapeo=mapeo_dict,
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
