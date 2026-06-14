"""Catálogo navegable de preguntas (M9).

El catálogo muestra las preguntas de TODAS las torres para que el piloto se vea
completo, pero el ``estado`` controla la clicabilidad: solo ``activa`` (hoy OTC) es
ejecutable. El RBAC del usuario se refleja en el flag ``ejecutable`` — una pregunta
de una torre a la que el usuario no tiene acceso nunca es ejecutable, aunque esté
activa. "Una pregunta clicable es una promesa": ``ejecutable`` es la promesa.

Decisión: estos endpoints NO devuelven 403 por torre (a diferencia de
``preguntas-sugeridas``), porque el catálogo es un mapa completo del producto; la
autorización vive en el flag ``ejecutable`` y, al ejecutar, en el chat/motor (RLS).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.models.pregunta_catalogo import PreguntaCatalogo

router = APIRouter(tags=["catalogo"])


class PreguntaItem(BaseModel):
    id: str
    texto: str
    estado: str  # "activa" | "proximamente"
    ejecutable: bool


class CategoriaCatalogo(BaseModel):
    nombre: str
    preguntas: list[PreguntaItem]


class TorreCatalogo(BaseModel):
    torre: str
    nombre: str
    estado_torre: str  # "activa" si tiene al menos una pregunta activa, si no "proximamente"
    categorias: list[CategoriaCatalogo]


def _construir_catalogo(
    db: Session, usuario: CurrentUser, *, torre_clave: str | None
) -> list[TorreCatalogo]:
    """Arma el catálogo agrupado torre → categoría → pregunta, preservando el orden.

    ``ejecutable`` = la pregunta está activa Y el usuario tiene acceso a su torre.
    """
    stmt = select(PreguntaCatalogo).order_by(PreguntaCatalogo.orden)
    if torre_clave is not None:
        stmt = stmt.where(PreguntaCatalogo.torre_clave == torre_clave)
    filas = db.scalars(stmt).all()

    accesibles = {t.value for t in usuario.torres_accesibles()}

    torres: dict[str, TorreCatalogo] = {}
    categorias: dict[tuple[str, str], CategoriaCatalogo] = {}
    for fila in filas:
        bloque = torres.get(fila.torre_clave)
        if bloque is None:
            bloque = TorreCatalogo(
                torre=fila.torre_clave,
                nombre=fila.torre_nombre,
                estado_torre="proximamente",
                categorias=[],
            )
            torres[fila.torre_clave] = bloque

        clave_cat = (fila.torre_clave, fila.categoria)
        categoria = categorias.get(clave_cat)
        if categoria is None:
            categoria = CategoriaCatalogo(nombre=fila.categoria, preguntas=[])
            categorias[clave_cat] = categoria
            bloque.categorias.append(categoria)

        ejecutable = fila.estado == "activa" and fila.torre_clave in accesibles
        if fila.estado == "activa":
            bloque.estado_torre = "activa"
        categoria.preguntas.append(
            PreguntaItem(
                id=fila.codigo,
                texto=fila.texto,
                estado=fila.estado,
                ejecutable=ejecutable,
            )
        )
    return list(torres.values())


@router.get("/catalogo/preguntas", response_model=list[TorreCatalogo])
def catalogo_preguntas(
    usuario: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> list[TorreCatalogo]:
    """Catálogo completo (todas las torres) para la pantalla 'Explorar preguntas'."""
    return _construir_catalogo(db, usuario, torre_clave=None)


@router.get("/torres/{torre}/preguntas", response_model=TorreCatalogo)
def preguntas_torre(
    torre: str, usuario: CurrentUser, db: Annotated[Session, Depends(get_db)]
) -> TorreCatalogo:
    """Catálogo de una torre: sus categorías con preguntas y estado (RBAC en ``ejecutable``)."""
    bloques = _construir_catalogo(db, usuario, torre_clave=torre)
    if not bloques:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sin preguntas en el catálogo para la torre {torre}.",
        )
    return bloques[0]
