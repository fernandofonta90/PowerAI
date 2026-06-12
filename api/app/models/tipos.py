"""Tipos ENUM de SQLAlchemy compartidos entre modelos.

Se definen una sola vez (un único tipo nativo por nombre en Postgres) y se
reutilizan. Persistimos el ``.value`` de cada enum (no el ``.name``) para que
coincida con los tipos ENUM creados en las migraciones.
"""

from sqlalchemy import Enum as SAEnum

from app.domain.enums import EstadoCarga, Frecuencia, Rol, Torre

# Nota: TipoColumna no tiene tipo ENUM en BD; vive dentro del JSON de la plantilla.


def _enum(python_enum: type, nombre: str) -> SAEnum:
    return SAEnum(python_enum, name=nombre, values_callable=lambda e: [m.value for m in e])


torre_enum = _enum(Torre, "torre")
rol_enum = _enum(Rol, "rol")
frecuencia_enum = _enum(Frecuencia, "frecuencia")
estado_carga_enum = _enum(EstadoCarga, "estado_carga")
