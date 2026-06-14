"""Modelos ORM (SQLAlchemy). Importados aquí para el autogenerate de Alembic."""

from app.models.base import Base
from app.models.bitacora import BitacoraConsulta
from app.models.carga import CargaArchivo
from app.models.conversacion import Conversacion, Mensaje, mensaje_consulta
from app.models.dashboard import Dashboard
from app.models.plantilla import PlantillaReporte
from app.models.usuario import AsignacionPermiso, Usuario
from app.models.vista import VistaCatalogo

__all__ = [
    "Base",
    "Usuario",
    "AsignacionPermiso",
    "PlantillaReporte",
    "CargaArchivo",
    "VistaCatalogo",
    "BitacoraConsulta",
    "Conversacion",
    "Mensaje",
    "mensaje_consulta",
    "Dashboard",
]
