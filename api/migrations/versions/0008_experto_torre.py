"""Experto configurable por torre (M10)

Revision ID: 0008_experto_torre
Revises: 0007_pregunta_catalogo
Create Date: 2026-06-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_experto_torre"
down_revision: str | None = "0007_pregunta_catalogo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# El tipo ENUM "torre" ya existe (creado en una migración previa); no recrearlo.
torre_enum = postgresql.ENUM(name="torre", create_type=False)


def upgrade() -> None:
    op.create_table(
        "experto_torre",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("torre", torre_enum, nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("identidad", sa.Text(), nullable=False),
        sa.Column("instrucciones_formato", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
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
        sa.UniqueConstraint("torre", "version", name="uq_experto_torre_version"),
    )
    op.create_index(op.f("ix_experto_torre_torre"), "experto_torre", ["torre"])

    op.create_table(
        "experto_fuente",
        sa.Column("experto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vista_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["experto_id"], ["experto_torre.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vista_id"], ["vista_catalogo.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("experto_id", "vista_id"),
    )


def downgrade() -> None:
    op.drop_table("experto_fuente")
    op.drop_index(op.f("ix_experto_torre_torre"), table_name="experto_torre")
    op.drop_table("experto_torre")
