"""Catálogo navegable de preguntas del SSC (M9).

Sembrado desde evals/catalogo_preguntas_seed.yaml (texto fiel al levantamiento).
Muestra las preguntas de las 6 torres para que el piloto se vea completo, pero el
``estado`` controla la clicabilidad: solo ``activa`` (hoy OTC) es ejecutable;
``proximamente`` se muestra en gris. ``torre_clave`` es un string (no el enum Torre)
porque el catálogo incluye agrupaciones como "General" (transversales).
"""

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PreguntaCatalogo(Base, TimestampMixin):
    """Una pregunta del catálogo, asociada a una torre y categoría."""

    __tablename__ = "pregunta_catalogo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    torre_clave: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    torre_nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    categoria: Mapped[str] = mapped_column(String(120), nullable=False)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    # "activa" | "proximamente" — controla la clicabilidad en el catálogo.
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    # Orden global de inserción para preservar el orden del seed (torre/categoría/pregunta).
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
