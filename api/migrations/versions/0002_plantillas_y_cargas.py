"""Plantillas de reporte y catálogo de cargas

Revision ID: 0002_plantillas_y_cargas
Revises: 0001_inicial
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_plantillas_y_cargas"
down_revision: str | None = "0001_inicial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# El tipo `torre` ya existe (migración 0001); aquí solo se referencia.
torre_enum = postgresql.ENUM(
    "OTC", "PTP", "RTR", "QCI", "CARE", "HTR", name="torre", create_type=False
)
frecuencia_enum = postgresql.ENUM(
    "diaria", "semanal", "quincenal", "mensual", name="frecuencia", create_type=False
)
estado_carga_enum = postgresql.ENUM(
    "recibida",
    "procesando",
    "disponible",
    "fallida",
    name="estado_carga",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    frecuencia_enum.create(bind, checkfirst=True)
    estado_carga_enum.create(bind, checkfirst=True)

    op.create_table(
        "plantilla_reporte",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=80), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("torre", torre_enum, nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("frecuencia", frecuencia_enum, nullable=False),
        sa.Column("columnas_json", postgresql.JSONB(), nullable=False),
        sa.Column("columna_pais", sa.String(length=120), nullable=False),
        sa.Column("columna_periodo", sa.String(length=120), nullable=False),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_plantilla_reporte_codigo"),
        "plantilla_reporte",
        ["codigo"],
        unique=True,
    )

    op.create_table(
        "carga_archivo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plantilla_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("torre", torre_enum, nullable=False),
        sa.Column("pais", sa.String(length=2), nullable=False),
        sa.Column("periodo", sa.String(length=20), nullable=False),
        sa.Column("responsable_email", sa.String(length=320), nullable=False),
        sa.Column("nombre_archivo_original", sa.String(length=500), nullable=False),
        sa.Column("hash_sha256", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("estado", estado_carga_enum, nullable=False),
        sa.Column("mensaje_error", sa.Text(), nullable=True),
        sa.Column("blob_path_original", sa.String(length=1000), nullable=False),
        sa.Column("blob_path_parquet", sa.String(length=1000), nullable=True),
        sa.Column("filas", sa.Integer(), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "actualizado_en",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["plantilla_id"], ["plantilla_reporte.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plantilla_id", "hash_sha256", name="uq_carga_hash"),
        sa.UniqueConstraint("plantilla_id", "pais", "periodo", "version", name="uq_carga_version"),
    )
    op.create_index(
        op.f("ix_carga_archivo_plantilla_id"),
        "carga_archivo",
        ["plantilla_id"],
    )
    op.create_index(op.f("ix_carga_archivo_torre"), "carga_archivo", ["torre"])
    op.create_index(op.f("ix_carga_archivo_pais"), "carga_archivo", ["pais"])


def downgrade() -> None:
    op.drop_index(op.f("ix_carga_archivo_pais"), table_name="carga_archivo")
    op.drop_index(op.f("ix_carga_archivo_torre"), table_name="carga_archivo")
    op.drop_index(op.f("ix_carga_archivo_plantilla_id"), table_name="carga_archivo")
    op.drop_table("carga_archivo")
    op.drop_index(op.f("ix_plantilla_reporte_codigo"), table_name="plantilla_reporte")
    op.drop_table("plantilla_reporte")
    estado_carga_enum.drop(op.get_bind(), checkfirst=True)
    frecuencia_enum.drop(op.get_bind(), checkfirst=True)
