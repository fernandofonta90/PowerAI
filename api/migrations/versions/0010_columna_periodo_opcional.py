"""Columna de periodo opcional en la plantilla (M12)

Revision ID: 0010_columna_periodo_opcional
Revises: 0009_carga_mapeo
Create Date: 2026-06-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_columna_periodo_opcional"
down_revision: str | None = "0009_carga_mapeo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "plantilla_reporte", "columna_periodo", existing_type=sa.String(length=120), nullable=True
    )


def downgrade() -> None:
    # Las filas con NULL se rellenan con '' para poder volver a NOT NULL.
    op.execute("UPDATE plantilla_reporte SET columna_periodo = '' WHERE columna_periodo IS NULL")
    op.alter_column(
        "plantilla_reporte", "columna_periodo", existing_type=sa.String(length=120), nullable=False
    )
