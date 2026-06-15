"""Endpoints de plantillas y vistas: consulta, creación por descubrimiento (M11)
y edición gobernada del molde.

Gobierno (decisiones inviolables):
- Crear plantilla + su vista 1:1 = admin O uploader de la torre.
- Editar el MOLDE (schema de la plantilla) = solo admin de la torre, con aviso de
  impacto a las cargas existentes. Nunca un consultante.
- El mapeo de una carga acomoda el archivo a la plantilla; cambiar el molde es este
  camino explícito, no un efecto colateral de cargar.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.domain.columnas import ColumnaSpec
from app.domain.enums import Frecuencia, Torre
from app.models.plantilla import PlantillaReporte
from app.models.vista import VistaCatalogo
from app.services.plantillas import (
    DefinicionInvalida,
    crear_plantilla_con_vista,
    editar_plantilla,
    editar_vista,
    es_admin_torre,
    impacto_edicion,
    puede_definir,
)

router = APIRouter(tags=["plantillas"])


class PlantillaResponse(BaseModel):
    codigo: str
    nombre: str
    torre: Torre
    descripcion: str
    frecuencia: Frecuencia
    columna_pais: str
    columna_periodo: str | None
    columnas: list[ColumnaSpec]

    @classmethod
    def desde(cls, p: PlantillaReporte) -> "PlantillaResponse":
        return cls(
            codigo=p.codigo,
            nombre=p.nombre,
            torre=p.torre,
            descripcion=p.descripcion,
            frecuencia=p.frecuencia,
            columna_pais=p.columna_pais,
            columna_periodo=p.columna_periodo,
            columnas=p.columnas,
        )


class VistaResponse(BaseModel):
    nombre: str
    titulo: str
    descripcion: str
    plantilla_codigo: str
    columnas: list[dict[str, str]]

    @classmethod
    def desde(cls, v: VistaCatalogo) -> "VistaResponse":
        return cls(
            nombre=v.nombre,
            titulo=v.titulo,
            descripcion=v.descripcion,
            plantilla_codigo=v.plantilla.codigo,
            columnas=[c.model_dump() for c in v.columnas],
        )


class CrearPlantillaIn(BaseModel):
    torre: Torre
    nombre: str = Field(min_length=1, max_length=200)
    frecuencia: Frecuencia
    columnas: list[ColumnaSpec] = Field(min_length=1)
    columna_pais: str
    columna_periodo: str | None = None
    vista_nombre_negocio: str = Field(min_length=1, max_length=200)
    vista_descripcion: str = ""
    descripciones_columnas: dict[str, str] = {}


class EditarPlantillaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    frecuencia: Frecuencia
    columnas: list[ColumnaSpec] = Field(min_length=1)
    columna_pais: str
    columna_periodo: str | None = None


class EditarVistaIn(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    descripcion: str = ""
    descripciones_columnas: dict[str, str] = {}


class PlantillaConVistaResponse(BaseModel):
    plantilla: PlantillaResponse
    vista: VistaResponse
    # Avisos de la creación (p. ej. colisiones de nombre técnico desambiguadas).
    avisos: list[str] = []


class PlantillaEditadaResponse(BaseModel):
    plantilla: PlantillaResponse
    cargas_afectadas: int


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
    return [PlantillaResponse.desde(p) for p in db.scalars(stmt) if p.torre in accesibles]


@router.post(
    "/plantillas", response_model=PlantillaConVistaResponse, status_code=status.HTTP_201_CREATED
)
def crear_plantilla(
    cuerpo: CrearPlantillaIn,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> PlantillaConVistaResponse:
    """Crea una plantilla y su vista 1:1 (primera carga). Admin o uploader de la torre."""
    if not puede_definir(usuario, cuerpo.torre):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Se requiere rol admin o uploader sobre la torre {cuerpo.torre.value}.",
        )
    try:
        res = crear_plantilla_con_vista(
            db,
            cuerpo.torre,
            nombre_plantilla=cuerpo.nombre,
            frecuencia=cuerpo.frecuencia,
            columnas=cuerpo.columnas,
            columna_pais=cuerpo.columna_pais,
            columna_periodo=cuerpo.columna_periodo,
            vista_nombre_negocio=cuerpo.vista_nombre_negocio,
            vista_descripcion=cuerpo.vista_descripcion,
            descripciones_columnas=cuerpo.descripciones_columnas,
        )
    except DefinicionInvalida as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlantillaConVistaResponse(
        plantilla=PlantillaResponse.desde(res.plantilla),
        vista=VistaResponse.desde(res.vista),
        avisos=res.avisos,
    )


def _plantilla_de(db: Session, codigo: str, usuario: CurrentUser) -> PlantillaReporte:
    plantilla = db.scalar(select(PlantillaReporte).where(PlantillaReporte.codigo == codigo))
    if plantilla is None or plantilla.torre not in usuario.torres_accesibles():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plantilla no encontrada."
        )
    return plantilla


@router.get("/plantillas/{codigo}/impacto")
def impacto(
    codigo: str, usuario: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> dict[str, int]:
    """Cuántas cargas dependen de la plantilla (aviso antes de editar el molde)."""
    plantilla = _plantilla_de(db, codigo, usuario)
    if not es_admin_torre(usuario, plantilla.torre):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editar el molde requiere rol admin de la torre.",
        )
    return {"cargas_afectadas": impacto_edicion(db, plantilla)}


@router.put("/plantillas/{codigo}", response_model=PlantillaEditadaResponse)
def editar_plantilla_endpoint(
    codigo: str,
    cuerpo: EditarPlantillaIn,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> PlantillaEditadaResponse:
    """Edita explícitamente el molde de la plantilla. SOLO admin de la torre."""
    plantilla = _plantilla_de(db, codigo, usuario)
    if not es_admin_torre(usuario, plantilla.torre):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editar el molde requiere rol admin de la torre.",
        )
    afectadas = impacto_edicion(db, plantilla)
    try:
        editada = editar_plantilla(
            db,
            plantilla,
            nombre_plantilla=cuerpo.nombre,
            frecuencia=cuerpo.frecuencia,
            columnas=cuerpo.columnas,
            columna_pais=cuerpo.columna_pais,
            columna_periodo=cuerpo.columna_periodo,
        )
    except DefinicionInvalida as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return PlantillaEditadaResponse(
        plantilla=PlantillaResponse.desde(editada), cargas_afectadas=afectadas
    )


@router.put("/vistas/{nombre}", response_model=VistaResponse)
def editar_vista_endpoint(
    nombre: str,
    cuerpo: EditarVistaIn,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> VistaResponse:
    """Edita el nombre de negocio y las descripciones de la vista. SOLO admin.

    Editar lo establecido (molde y vista) es solo admin: el nombre y las
    descripciones de la vista son lo que el experto lee para decidir qué consultar,
    tan sensible como el molde. Crear sí es admin|uploader (parte del flujo de carga).
    """
    vista = db.scalar(select(VistaCatalogo).where(VistaCatalogo.nombre == nombre))
    if vista is None or vista.torre not in usuario.torres_accesibles():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vista no encontrada.")
    if not es_admin_torre(usuario, vista.torre):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Editar la vista requiere rol admin de la torre {vista.torre.value}.",
        )
    try:
        editada = editar_vista(
            db,
            vista,
            titulo=cuerpo.titulo,
            descripcion=cuerpo.descripcion,
            descripciones_columnas=cuerpo.descripciones_columnas,
        )
    except DefinicionInvalida as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return VistaResponse.desde(editada)
