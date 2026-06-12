"""Endpoints del chat analítico (conversaciones y mensajes) con RBAC de propietario."""

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
from app.db import get_db
from app.ia.agente import Citacion, DatosTabulares
from app.ia.proveedor import get_llm_provider
from app.models.conversacion import Conversacion, Mensaje
from app.services.conversaciones import crear_conversacion, enviar_mensaje

router = APIRouter(tags=["chat"])


class CrearConversacion(BaseModel):
    titulo: str = ""


class ConversacionResponse(BaseModel):
    id: uuid.UUID
    titulo: str
    creado_en: datetime


class MensajeResponse(BaseModel):
    id: uuid.UUID
    rol: str
    contenido: str
    citacion: dict[str, Any] | None
    creado_en: datetime

    @classmethod
    def desde(cls, m: Mensaje) -> "MensajeResponse":
        return cls(
            id=m.id,
            rol=m.rol,
            contenido=m.contenido,
            citacion=m.citacion_json,
            creado_en=m.creado_en,
        )


class ConversacionDetalle(ConversacionResponse):
    mensajes: list[MensajeResponse]


class PreguntaRequest(BaseModel):
    pregunta: str


class RespuestaChat(BaseModel):
    mensaje_id: uuid.UUID
    texto: str
    datos_tabulares: DatosTabulares | None
    citacion: Citacion


def _conversacion_propia(
    db: Session, usuario: UsuarioAutenticado, conversacion_id: uuid.UUID
) -> Conversacion:
    conv = db.get(Conversacion, conversacion_id)
    if conv is None or conv.usuario_email != usuario.email:
        # No revelar conversaciones de otros usuarios.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrada.")
    return conv


@router.post(
    "/conversaciones", response_model=ConversacionResponse, status_code=status.HTTP_201_CREATED
)
def crear(
    cuerpo: CrearConversacion,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversacionResponse:
    conv = crear_conversacion(db, usuario, cuerpo.titulo)
    return ConversacionResponse(id=conv.id, titulo=conv.titulo, creado_en=conv.creado_en)


@router.get("/conversaciones", response_model=list[ConversacionResponse])
def listar(
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> list[ConversacionResponse]:
    convs = db.scalars(
        select(Conversacion)
        .where(Conversacion.usuario_email == usuario.email)
        .order_by(Conversacion.creado_en.desc())
    )
    return [ConversacionResponse(id=c.id, titulo=c.titulo, creado_en=c.creado_en) for c in convs]


@router.get("/conversaciones/{conversacion_id}", response_model=ConversacionDetalle)
def obtener(
    conversacion_id: uuid.UUID,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> ConversacionDetalle:
    conv = _conversacion_propia(db, usuario, conversacion_id)
    return ConversacionDetalle(
        id=conv.id,
        titulo=conv.titulo,
        creado_en=conv.creado_en,
        mensajes=[MensajeResponse.desde(m) for m in conv.mensajes],
    )


@router.post("/conversaciones/{conversacion_id}/mensajes", response_model=RespuestaChat)
def enviar(
    conversacion_id: uuid.UUID,
    cuerpo: PreguntaRequest,
    usuario: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> RespuestaChat:
    conv = _conversacion_propia(db, usuario, conversacion_id)
    s = get_settings()
    mensaje, resultado = enviar_mensaje(
        db,
        usuario,
        get_llm_provider(),
        conv,
        cuerpo.pregunta,
        max_iteraciones=s.agente_max_iteraciones,
        max_filas=s.agente_max_filas,
    )
    return RespuestaChat(
        mensaje_id=mensaje.id,
        texto=resultado.texto,
        datos_tabulares=resultado.datos_tabulares,
        citacion=resultado.citacion,
    )
