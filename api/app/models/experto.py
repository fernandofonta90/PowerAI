"""Experto configurable por torre (M10).

Cada torre tiene un "Experto" con identidad/tono, instrucciones de formato y un
conjunto de fuentes permitidas (vistas del catálogo). La configuración con poder
necesita barandales: una config NO se activa hasta validarse contra el banco de
evals de su torre (ver app/services/expertos.py).

SEPARACIÓN configurable vs estructural: aquí viven solo los campos editables por
el admin (identidad, formato, fuentes, preguntas destacadas no incluidas en M10).
El RLS torre×país, el text-to-SQL gobernado sobre vistas curadas y la honestidad
ante métricas no soportadas viven en el motor/agente, NO en esta tabla: la
seguridad no se configura desde un formulario.

Versionado: cada fila es una versión. Al activar una nueva, la activa anterior
pasa a ARCHIVADO (rollback posible). Hay como máximo una versión ACTIVO por torre.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import EstadoExperto, Torre
from app.models.base import Base, TimestampMixin
from app.models.tipos import torre_enum
from app.models.vista import VistaCatalogo


class ExpertoFuente(Base):
    """Asociación experto ↔ vista del catálogo (fuentes permitidas).

    FK real a ``vista_catalogo``: una fuente permitida siempre apunta a una vista
    existente del catálogo. El borrado de la vista cae en cascada sobre la
    asignación (no sobre el experto).
    """

    __tablename__ = "experto_fuente"

    experto_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("experto_torre.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vista_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vista_catalogo.id", ondelete="CASCADE"),
        primary_key=True,
    )


class ExpertoTorre(Base, TimestampMixin):
    """Una versión de la configuración del Experto de una torre."""

    __tablename__ = "experto_torre"
    __table_args__ = (UniqueConstraint("torre", "version", name="uq_experto_torre_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    torre: Mapped[Torre] = mapped_column(torre_enum, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    # Identidad/tono configurable (parte del system prompt del agente).
    identidad: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Instrucciones de formato de la respuesta (parte del system prompt).
    instrucciones_formato: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # "borrador" | "activo" | "archivado".
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default=EstadoExperto.BORRADOR)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Fuentes permitidas: vistas del catálogo que este experto puede consultar.
    fuentes: Mapped[list[VistaCatalogo]] = relationship(
        VistaCatalogo, secondary="experto_fuente", lazy="selectin"
    )

    @property
    def nombres_fuentes(self) -> set[str]:
        return {v.nombre for v in self.fuentes}
