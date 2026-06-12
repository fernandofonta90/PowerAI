"""Proveedores de autenticación intercambiables.

Interfaz ``AuthProvider`` con una implementación mock para dev/test que resuelve
la identidad contra la base de datos a partir de un header. En producción se
añadirá ``EntraAuthProvider`` validando tokens de Microsoft Entra ID sin tocar
los endpoints ni la lógica de autorización (misma forma de salida).
"""

from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.schemas import Grant, UsuarioAutenticado
from app.models.usuario import Usuario


class AuthError(Exception):
    """La identidad no pudo resolverse (credencial ausente o inválida)."""


class AuthProvider(ABC):
    """Contrato de un proveedor de autenticación."""

    @abstractmethod
    def autenticar(self, db: Session, credencial: str | None) -> UsuarioAutenticado:
        """Resuelve la credencial del request a un usuario autenticado.

        Args:
            db: sesión de base de datos para resolver grants.
            credencial: valor crudo de la credencial (header), puede ser ``None``.

        Raises:
            AuthError: si la credencial falta o no corresponde a un usuario activo.
        """


class MockAuthProvider(AuthProvider):
    """Proveedor de desarrollo: la credencial es el email del usuario.

    Se envía en el header ``X-Mock-User``. El usuario debe existir y estar activo
    en la tabla ``usuario`` (sembrar con ``app.scripts.seed_dev``).
    """

    def autenticar(self, db: Session, credencial: str | None) -> UsuarioAutenticado:
        if not credencial:
            raise AuthError("Falta el header X-Mock-User (mock auth).")

        usuario = db.scalar(
            select(Usuario).where(Usuario.email == credencial, Usuario.activo.is_(True))
        )
        if usuario is None:
            raise AuthError(f"Usuario desconocido o inactivo: {credencial}")

        grants = [Grant(torre=a.torre, pais=a.pais, rol=a.rol) for a in usuario.asignaciones]
        return UsuarioAutenticado(email=usuario.email, nombre=usuario.nombre, grants=grants)


def build_auth_provider(nombre: str) -> AuthProvider:
    """Fábrica de proveedores según la configuración (``POWERAI_AUTH_PROVIDER``)."""
    if nombre == "mock":
        return MockAuthProvider()
    raise NotImplementedError(f"Proveedor de auth no soportado todavía: {nombre}")
