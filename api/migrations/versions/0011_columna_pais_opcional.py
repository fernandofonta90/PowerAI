"""Columna de país opcional en la plantilla (M15)

Revision ID: 0011_columna_pais_opcional
Revises: 0010_columna_periodo_opcional
Create Date: 2026-06-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_columna_pais_opcional"
down_revision: str | None = "0010_columna_periodo_opcional"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "plantilla_reporte", "columna_pais", existing_type=sa.String(length=120), nullable=True
    )


def downgrade() -> None:
    op.execute("UPDATE plantilla_reporte SET columna_pais = '' WHERE columna_pais IS NULL")
    op.alter_column(
        "plantilla_reporte", "columna_pais", existing_type=sa.String(length=120), nullable=False
    )
