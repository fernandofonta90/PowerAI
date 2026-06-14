"""Modelos de conversación del chat analítico.

Una Conversacion pertenece a un usuario y agrupa Mensajes (de usuario y del
asistente). Cada mensaje del asistente se liga, mediante la tabla de asociación
``mensaje_consulta``, a las entradas de ``bitacora_consulta`` que generó (un
mensaje puede ejecutar N consultas). La bitácora de M3 NO se modifica: se referencia.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.bitacora import BitacoraConsulta

mensaje_consulta = Table(
    "mensaje_consulta",
    Base.metadata,
    Column(
        "mensaje_id",
        UUID(as_uuid=True),
        ForeignKey("mensaje.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "bitacora_id",
        UUID(as_uuid=True),
        ForeignKey("bitacora_consulta.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
)


class Conversacion(Base, TimestampMixin):
    """Hilo de chat analítico de un usuario."""

    __tablename__ = "conversacion"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(300), default="", nullable=False)

    mensajes: Mapped[list["Mensaje"]] = relationship(
        back_populates="conversacion",
        cascade="all, delete-orphan",
        order_by="Mensaje.creado_en",
        lazy="selectin",
    )


class Mensaje(Base, TimestampMixin):
    """Mensaje de una conversación (de ``usuario`` o del ``assistant``)."""

    __tablename__ = "mensaje"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversacion.id", ondelete="CASCADE"), nullable=False
    )
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    # Citación estructurada de la respuesta del asistente (fuentes, sql ids, vistas).
    citacion_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Consumo de tokens del mensaje del asistente (insumo del control de costos).
    tokens_entrada: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_salida: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    conversacion: Mapped[Conversacion] = relationship(back_populates="mensajes")
    consultas: Mapped[list["BitacoraConsulta"]] = relationship(
        "BitacoraConsulta", secondary=mensaje_consulta, lazy="selectin"
    )
