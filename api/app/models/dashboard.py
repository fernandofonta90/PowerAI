"""Modelo de dashboard guardado (ADR-0004).

Guardar un dashboard = persistir su spec declarativa + filtros. Al abrirlo, las
queries de la spec se re-ejecutan por el motor (RLS), de modo que el dashboard se
actualiza con cada nueva carga. Es del owner (sin compartir entre usuarios en v1).
"""

import uuid
from typing import Any

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import Torre
from app.models.base import Base, TimestampMixin
from app.models.tipos import torre_enum


class Dashboard(Base, TimestampMixin):
    """Dashboard guardado como especificación declarativa."""

    __tablename__ = "dashboard"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    torre: Mapped[Torre] = mapped_column(torre_enum, nullable=False, index=True)
    owner_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    # Spec declarativa (lista de visuales con sus queries) y filtros de alcance.
    spec_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    filtros_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
