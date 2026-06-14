"""Modelo del catálogo de archivos cargados (CargaArchivo).

Cada carga es inmutable y versionada: nunca se sobrescribe. El Parquet derivado
referencia la misma versión del archivo origen (mismo path versionado). El estado
recorre recibida → procesando → disponible / fallida.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import EstadoCarga, Torre
from app.models.base import Base, TimestampMixin
from app.models.plantilla import PlantillaReporte
from app.models.tipos import estado_carga_enum, torre_enum


class CargaArchivo(Base, TimestampMixin):
    """Una carga concreta de un archivo contra una plantilla, torre y país."""

    __tablename__ = "carga_archivo"
    __table_args__ = (
        # Mismo contenido (hash) ya cargado para la misma plantilla = duplicado.
        UniqueConstraint("plantilla_id", "hash_sha256", name="uq_carga_hash"),
        # Integridad del versionado por plantilla × país × periodo.
        UniqueConstraint("plantilla_id", "pais", "periodo", "version", name="uq_carga_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plantilla_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plantilla_reporte.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Denormalizado desde la plantilla para filtrar por RBAC sin join.
    torre: Mapped[Torre] = mapped_column(torre_enum, nullable=False, index=True)
    pais: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    periodo: Mapped[str] = mapped_column(String(20), nullable=False)
    responsable_email: Mapped[str] = mapped_column(String(320), nullable=False)

    nombre_archivo_original: Mapped[str] = mapped_column(String(500), nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    estado: Mapped[EstadoCarga] = mapped_column(
        estado_carga_enum, nullable=False, default=EstadoCarga.RECIBIDA
    )
    mensaje_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    blob_path_original: Mapped[str] = mapped_column(String(1000), nullable=False)
    blob_path_parquet: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    filas: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Mapeo aplicado a esta carga (columna_esperada -> columna_en_archivo), si el
    # archivo no calzaba con la plantilla. NULL = el archivo calzaba tal cual.
    mapeo_json: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True)

    plantilla: Mapped[PlantillaReporte] = relationship(lazy="joined")
