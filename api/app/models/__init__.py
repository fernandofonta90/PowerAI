"""Modelos ORM (SQLAlchemy). Importados aquí para el autogenerate de Alembic."""

from app.models.base import Base
from app.models.usuario import AsignacionPermiso, Usuario

__all__ = ["Base", "Usuario", "AsignacionPermiso"]
