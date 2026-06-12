"""Bitácora de auditoría de consultas analíticas (BitacoraConsulta).

Requisito de auditoría interna (no opcional): cada ejecución registra el usuario,
el SQL ejecutado, las vistas usadas, las versiones de datos consultadas y el
resultado. Es la base de la citación de fuentes que exigirá M4.
"""

import uuid
from typing import Any

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BitacoraConsulta(Base, TimestampMixin):
    """Registro inmutable de una ejecución de consulta en el motor."""

    __tablename__ = "bitacora_consulta"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    sql_ejecutado: Mapped[str] = mapped_column(Text, nullable=False)
    # Vistas referenciadas y versiones de datos cargadas en la sesión de consulta.
    vistas_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    versiones_json: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    filas: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exito: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
