"""Endpoints de identidad y una ruta protegida de ejemplo (RBAC torre × país)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.deps import CurrentUser, requiere_acceso
from app.auth.schemas import UsuarioAutenticado
from app.domain.enums import Pais, Torre

router = APIRouter(tags=["auth"])

# Dependencia de acceso a OTC construida una sola vez (evita llamadas en defaults).
AccesoOTC = Annotated[UsuarioAutenticado, Depends(requiere_acceso(Torre.OTC))]


class TorreAccesible(BaseModel):
    torre: Torre
    paises: list[str]


class MeResponse(BaseModel):
    email: str
    nombre: str
    torres: list[TorreAccesible]


@router.get("/me", response_model=MeResponse)
def me(usuario: CurrentUser) -> MeResponse:
    """Devuelve la identidad del usuario y su matriz de acceso torre × país."""
    torres = [
        TorreAccesible(torre=t, paises=sorted(usuario.paises_en(t)))
        for t in sorted(usuario.torres_accesibles())
    ]
    return MeResponse(email=usuario.email, nombre=usuario.nombre, torres=torres)


class AgingResumen(BaseModel):
    torre: Torre
    pais: Pais
    mensaje: str


@router.get("/otc/aging", response_model=AgingResumen)
def aging_otc(pais: Pais, usuario: AccesoOTC) -> AgingResumen:
    """Ruta protegida de ejemplo: exige acceso a OTC en el país solicitado.

    En M1 solo demuestra el control de acceso; el dato real del Aging llega en M2/M3.
    """
    return AgingResumen(
        torre=Torre.OTC,
        pais=pais,
        mensaje=f"Acceso concedido a {usuario.email} para OTC/{pais.value}.",
    )
