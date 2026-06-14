"""Registro de consumo de tokens por mensaje

Revision ID: 0005_tokens_mensaje
Revises: 0004_conversaciones
Create Date: 2026-06-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_tokens_mensaje"
down_revision: str | None = "0004_conversaciones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "mensaje",
        sa.Column("tokens_entrada", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "mensaje",
        sa.Column("tokens_salida", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("mensaje", "tokens_salida")
    op.drop_column("mensaje", "tokens_entrada")
