"""Dependencias FastAPI para autenticación y autorización torre × país.

Toda ruta protegida valida permisos con ``requiere_acceso``: no existen
endpoints "internos sin auth" (regla de seguridad del proyecto).
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.provider import AuthError, build_auth_provider
from app.auth.schemas import UsuarioAutenticado
from app.config import get_settings
from app.db import get_db
from app.domain.enums import Pais, Rol, Torre


def get_current_user(
    db: Annotated[Session, Depends(get_db)],
    x_mock_user: Annotated[str | None, Header(alias="X-Mock-User")] = None,
) -> UsuarioAutenticado:
    """Resuelve el usuario del request usando el proveedor configurado."""
    provider = build_auth_provider(get_settings().auth_provider)
    try:
        return provider.autenticar(db, x_mock_user)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Mock"},
        ) from exc


CurrentUser = Annotated[UsuarioAutenticado, Depends(get_current_user)]


def requiere_acceso(
    torre: Torre, *, roles: set[Rol] | None = None
) -> Callable[[UsuarioAutenticado, Pais], UsuarioAutenticado]:
    """Construye una dependencia que exige acceso a ``torre`` para el país pedido.

    El país objetivo se toma del query/path param ``pais``. La seguridad a nivel
    de fila la aplica luego el motor de consulta; esta capa es la puerta de entrada.
    """

    def _dep(usuario: CurrentUser, pais: Pais) -> UsuarioAutenticado:
        if not usuario.tiene_acceso(torre, pais, roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso sobre {torre.value} en {pais.value}.",
            )
        return usuario

    return _dep
