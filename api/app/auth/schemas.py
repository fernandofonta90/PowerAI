"""Esquemas del usuario autenticado y su lógica de autorización.

Estos modelos son agnósticos del proveedor (mock o Entra ID): cualquier
proveedor debe construir un :class:`UsuarioAutenticado` con sus grants.
La evaluación de permisos torre × país vive aquí, no en los endpoints.
"""

from pydantic import BaseModel, EmailStr

from app.domain.enums import PAIS_TODOS, Pais, Rol, Torre


class Grant(BaseModel):
    """Una asignación de acceso: rol sobre una torre y país (o todos)."""

    torre: Torre
    pais: str  # país ISO alpha-2 o el comodín ``*`` (PAIS_TODOS).
    rol: Rol

    def cubre(self, torre: Torre, pais: Pais) -> bool:
        """Indica si este grant otorga acceso a la torre y país dados."""
        if self.torre != torre:
            return False
        return self.pais == PAIS_TODOS or self.pais == pais


class UsuarioAutenticado(BaseModel):
    """Identidad resuelta de quien hace el request, con sus grants."""

    email: EmailStr
    nombre: str
    grants: list[Grant]

    def tiene_acceso(self, torre: Torre, pais: Pais, roles: set[Rol] | None = None) -> bool:
        """¿El usuario puede operar en (torre, país) con alguno de ``roles``?

        Si ``roles`` es ``None`` basta cualquier rol (acceso de lectura).
        """
        return any(g.cubre(torre, pais) and (roles is None or g.rol in roles) for g in self.grants)

    def torres_accesibles(self) -> set[Torre]:
        """Conjunto de torres en las que el usuario tiene al menos un grant."""
        return {g.torre for g in self.grants}

    def paises_en(self, torre: Torre) -> set[str]:
        """Países (o ``*``) con grant en la torre indicada."""
        return {g.pais for g in self.grants if g.torre == torre}
