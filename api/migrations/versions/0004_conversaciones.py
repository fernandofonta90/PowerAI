"""Conversaciones y mensajes del chat analítico

Revision ID: 0004_conversaciones
Revises: 0003_catalogo_semantico
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_conversaciones"
down_revision: str | None = "0003_catalogo_semantico"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversacion",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_email", sa.String(length=320), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
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
    op.create_index(op.f("ix_conversacion_usuario_email"), "conversacion", ["usuario_email"])

    op.create_table(
        "mensaje",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversacion_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("contenido", sa.Text(), nullable=False),
        sa.Column("citacion_json", postgresql.JSONB(), nullable=True),
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
        sa.ForeignKeyConstraint(["conversacion_id"], ["conversacion.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mensaje_conversacion_id"), "mensaje", ["conversacion_id"])

    op.create_table(
        "mensaje_consulta",
        sa.Column("mensaje_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bitacora_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["mensaje_id"], ["mensaje.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bitacora_id"], ["bitacora_consulta.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("mensaje_id", "bitacora_id"),
    )


def downgrade() -> None:
    op.drop_table("mensaje_consulta")
    op.drop_index(op.f("ix_mensaje_conversacion_id"), table_name="mensaje")
    op.drop_table("mensaje")
    op.drop_index(op.f("ix_conversacion_usuario_email"), table_name="conversacion")
    op.drop_table("conversacion")
