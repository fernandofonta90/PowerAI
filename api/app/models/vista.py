"""Modelo de vista del catálogo semántico (VistaCatalogo).

Las vistas curadas son DATOS, no código (igual que las plantillas): nombre de
negocio, descripción, torre, SQL de definición sobre los Parquet y descripción
por columna. El LLM (M4) leerá estas descripciones para decidir qué consultar.

El SQL de la vista referencia la "fuente" de su plantilla por el ``codigo`` de la
plantilla; el motor materializa esa fuente ya filtrada (RLS torre × país + última
versión) antes de crear la vista.
"""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.columnas import ColumnaDescrita
from app.domain.enums import Torre
from app.models.base import Base, TimestampMixin
from app.models.plantilla import PlantillaReporte
from app.models.tipos import torre_enum


class VistaCatalogo(Base, TimestampMixin):
    """Vista curada del catálogo semántico sobre una plantilla."""

    __tablename__ = "vista_catalogo"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Identificador de la vista en DuckDB (snake_case, único).
    nombre: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    torre: Mapped[Torre] = mapped_column(torre_enum, nullable=False, index=True)

    plantilla_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plantilla_reporte.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # SELECT que define la vista sobre la fuente (codigo de la plantilla).
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    columnas_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    plantilla: Mapped[PlantillaReporte] = relationship(lazy="joined")

    @property
    def columnas(self) -> list[ColumnaDescrita]:
        return [ColumnaDescrita.model_validate(c) for c in self.columnas_json]
