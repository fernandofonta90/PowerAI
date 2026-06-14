"""Dashboards guardados (spec declarativa)

Revision ID: 0006_dashboards
Revises: 0005_tokens_mensaje
Create Date: 2026-06-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_dashboards"
down_revision: str | None = "0005_tokens_mensaje"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

torre_enum = postgresql.ENUM(
    "OTC", "PTP", "RTR", "QCI", "CARE", "HTR", name="torre", create_type=False
)


def upgrade() -> None:
    op.create_table(
        "dashboard",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("torre", torre_enum, nullable=False),
        sa.Column("owner_email", sa.String(length=320), nullable=False),
        sa.Column("spec_json", postgresql.JSONB(), nullable=False),
        sa.Column("filtros_json", postgresql.JSONB(), nullable=False),
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
    op.create_index(op.f("ix_dashboard_torre"), "dashboard", ["torre"])
    op.create_index(op.f("ix_dashboard_owner_email"), "dashboard", ["owner_email"])


def downgrade() -> None:
    op.drop_index(op.f("ix_dashboard_owner_email"), table_name="dashboard")
    op.drop_index(op.f("ix_dashboard_torre"), table_name="dashboard")
    op.drop_table("dashboard")
