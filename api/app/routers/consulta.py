"""Endpoint interno del motor de consulta y listado del catálogo de vistas.

El SQL lo escribe (por ahora) un humano en tests; M4 le pondrá el agente encima.
La seguridad a nivel de fila la garantiza el motor por construcción.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.domain.columnas import ColumnaDescrita
from app.domain.enums import Torre
from app.models.vista import VistaCatalogo
from app.motor.motor import ConsultaInvalida, ResultadoConsulta, ejecutar_consulta

router = APIRouter(tags=["consulta"])


class ConsultaRequest(BaseModel):
    sql: str


class VistaResponse(BaseModel):
    nombre: str
    titulo: str
    descripcion: str
    torre: Torre
    columnas: list[ColumnaDescrita]


@router.post("/consultas", response_model=ResultadoConsulta)
def consultar(
    cuerpo: ConsultaRequest,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ResultadoConsulta:
    """Ejecuta SQL contra las vistas pre-filtradas del usuario (RLS por construcción)."""
    try:
        return ejecutar_consulta(db, usuario, cuerpo.sql)
    except ConsultaInvalida as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"motivo": "sql_invalido", "error": str(exc)},
        ) from exc


@router.get("/vistas", response_model=list[VistaResponse])
def listar_vistas(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    torre: Torre | None = None,
) -> list[VistaResponse]:
    """Lista las vistas del catálogo de las torres accesibles por el usuario."""
    accesibles = usuario.torres_accesibles()
    stmt = select(VistaCatalogo).order_by(VistaCatalogo.nombre)
    if torre is not None:
        stmt = stmt.where(VistaCatalogo.torre == torre)
    return [
        VistaResponse(
            nombre=v.nombre,
            titulo=v.titulo,
            descripcion=v.descripcion,
            torre=v.torre,
            columnas=v.columnas,
        )
        for v in db.scalars(stmt)
        if v.torre in accesibles
    ]
