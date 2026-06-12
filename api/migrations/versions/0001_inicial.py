"""Esquema inicial: usuarios y asignaciones de permiso (RBAC torre x pais)

Revision ID: 0001_inicial
Revises:
Create Date: 2026-06-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_inicial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

torre_enum = postgresql.ENUM(
    "OTC", "PTP", "RTR", "QCI", "CARE", "HTR", name="torre", create_type=False
)
rol_enum = postgresql.ENUM("uploader", "consulta", "admin", name="rol", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    torre_enum.create(bind, checkfirst=True)
    rol_enum.create(bind, checkfirst=True)

    op.create_table(
        "usuario",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
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
    op.create_index(op.f("ix_usuario_email"), "usuario", ["email"], unique=True)

    op.create_table(
        "asignacion_permiso",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("torre", torre_enum, nullable=False),
        sa.Column("pais", sa.String(length=2), nullable=False),
        sa.Column("rol", rol_enum, nullable=False),
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
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("usuario_id", "torre", "pais", "rol", name="uq_asignacion"),
    )


def downgrade() -> None:
    op.drop_table("asignacion_permiso")
    op.drop_index(op.f("ix_usuario_email"), table_name="usuario")
    op.drop_table("usuario")
    rol_enum.drop(op.get_bind(), checkfirst=True)
    torre_enum.drop(op.get_bind(), checkfirst=True)
