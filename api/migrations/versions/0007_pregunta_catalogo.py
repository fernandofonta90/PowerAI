"""Catálogo navegable de preguntas del SSC

Revision ID: 0007_pregunta_catalogo
Revises: 0006_dashboards
Create Date: 2026-06-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_pregunta_catalogo"
down_revision: str | None = "0006_dashboards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pregunta_catalogo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("torre_clave", sa.String(length=40), nullable=False),
        sa.Column("torre_nombre", sa.String(length=120), nullable=False),
        sa.Column("categoria", sa.String(length=120), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
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
        op.f("ix_pregunta_catalogo_codigo"), "pregunta_catalogo", ["codigo"], unique=True
    )
    op.create_index(
        op.f("ix_pregunta_catalogo_torre_clave"), "pregunta_catalogo", ["torre_clave"]
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_pregunta_catalogo_torre_clave"), table_name="pregunta_catalogo")
    op.drop_index(op.f("ix_pregunta_catalogo_codigo"), table_name="pregunta_catalogo")
    op.drop_table("pregunta_catalogo")
