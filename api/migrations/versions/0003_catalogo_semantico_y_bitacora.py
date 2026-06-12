"""Catálogo semántico (vistas) y bitácora de consultas

Revision ID: 0003_catalogo_semantico
Revises: 0002_plantillas_y_cargas
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_catalogo_semantico"
down_revision: str | None = "0002_plantillas_y_cargas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

torre_enum = postgresql.ENUM(
    "OTC", "PTP", "RTR", "QCI", "CARE", "HTR", name="torre", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "vista_catalogo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=80), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("torre", torre_enum, nullable=False),
        sa.Column("plantilla_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sql", sa.Text(), nullable=False),
        sa.Column("columnas_json", postgresql.JSONB(), nullable=False),
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
    )
    op.create_index(op.f("ix_vista_catalogo_nombre"), "vista_catalogo", ["nombre"], unique=True)
    op.create_index(op.f("ix_vista_catalogo_torre"), "vista_catalogo", ["torre"])

    op.create_table(
        "bitacora_consulta",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_email", sa.String(length=320), nullable=False),
        sa.Column("sql_ejecutado", sa.Text(), nullable=False),
        sa.Column("vistas_json", postgresql.JSONB(), nullable=False),
        sa.Column("versiones_json", postgresql.JSONB(), nullable=False),
        sa.Column("filas", sa.Integer(), nullable=False),
        sa.Column("exito", sa.Boolean(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
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
        op.f("ix_bitacora_consulta_usuario_email"),
        "bitacora_consulta",
        ["usuario_email"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_bitacora_consulta_usuario_email"), table_name="bitacora_consulta")
    op.drop_table("bitacora_consulta")
    op.drop_index(op.f("ix_vista_catalogo_torre"), table_name="vista_catalogo")
    op.drop_index(op.f("ix_vista_catalogo_nombre"), table_name="vista_catalogo")
    op.drop_table("vista_catalogo")
