"""Modelos de usuario y asignaciones de permiso (RBAC torre × país).

El RBAC se persiste desde el día 1 (no se parcha después). En dev, el mock auth
resuelve usuarios contra estas tablas; en prod, Entra ID provee la identidad y el
mapeo de grupos a asignaciones se sincroniza aquí.
"""

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import Rol, Torre
from app.models.base import Base, TimestampMixin

# Persistimos el .value de los enums (no el .name), para que coincida con los
# tipos ENUM creados en la migración (p. ej. rol -> "admin", no "ADMIN").
_torre_enum = SAEnum(Torre, name="torre", values_callable=lambda e: [m.value for m in e])
_rol_enum = SAEnum(Rol, name="rol", values_callable=lambda e: [m.value for m in e])


class Usuario(Base, TimestampMixin):
    """Usuario autenticable de PowerAI, identificado por su email corporativo."""

    __tablename__ = "usuario"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    asignaciones: Mapped[list["AsignacionPermiso"]] = relationship(
        back_populates="usuario",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class AsignacionPermiso(Base, TimestampMixin):
    """Grant de acceso de un usuario a una torre y país con un rol concreto.

    El país se guarda como texto para admitir el comodín ``*`` (todos los países
    de la torre); la validación contra el enum :class:`~app.domain.enums.Pais`
    ocurre en la capa de aplicación.
    """

    __tablename__ = "asignacion_permiso"
    __table_args__ = (UniqueConstraint("usuario_id", "torre", "pais", "rol", name="uq_asignacion"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False
    )
    torre: Mapped[Torre] = mapped_column(_torre_enum, nullable=False)
    pais: Mapped[str] = mapped_column(String(2), nullable=False)
    rol: Mapped[Rol] = mapped_column(_rol_enum, nullable=False)

    usuario: Mapped[Usuario] = relationship(back_populates="asignaciones")
