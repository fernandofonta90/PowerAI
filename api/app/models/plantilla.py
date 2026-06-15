"""Modelo de plantilla de reporte (esquema esperado de un reporte recurrente).

Una PlantillaReporte describe la estructura que debe tener un archivo cargado:
columnas esperadas con su tipo, qué columna identifica el país y el periodo
(para verificarlos contra lo declarado por el uploader) y la frecuencia esperada
de carga (insumo del cálculo de frescura).
"""

import uuid
from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.columnas import ColumnaSpec
from app.domain.enums import Frecuencia, Torre
from app.models.base import Base, TimestampMixin
from app.models.tipos import frecuencia_enum, torre_enum


class PlantillaReporte(Base, TimestampMixin):
    """Definición declarativa de un tipo de reporte recurrente."""

    __tablename__ = "plantilla_reporte"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    torre: Mapped[Torre] = mapped_column(torre_enum, nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, default="", nullable=False)
    frecuencia: Mapped[Frecuencia] = mapped_column(frecuencia_enum, nullable=False)

    # Esquema esperado: lista serializada de ColumnaSpec.
    columnas_json: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)

    # Columnas del archivo que portan país y periodo (para verificación).
    # ``columna_periodo`` es OPCIONAL: si el reporte no trae periodo en una columna,
    # el usuario lo declara al cargar y aplica a todo el archivo (M12).
    columna_pais: Mapped[str] = mapped_column(String(120), nullable=False)
    columna_periodo: Mapped[str | None] = mapped_column(String(120), nullable=True)

    @property
    def columnas(self) -> list[ColumnaSpec]:
        """Columnas esperadas como objetos ColumnaSpec."""
        return [ColumnaSpec.model_validate(c) for c in self.columnas_json]
