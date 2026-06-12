"""Validación previa al motor: solo se permiten consultas SELECT de una sentencia.

Es defensa en profundidad: el motor ya bloquea el acceso externo, pero la tool
``ejecutar_sql`` solo debe aceptar lectura. Bloquea DDL/DML, múltiples sentencias
y comandos de extensión/configuración.
"""

import re

_PROHIBIDOS = (
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "attach",
    "detach",
    "copy",
    "pragma",
    "set",
    "call",
    "install",
    "load",
    "export",
    "import",
    "truncate",
    "grant",
    "revoke",
)


class SqlNoPermitido(Exception):
    """El SQL no es una consulta SELECT de una sola sentencia."""


def validar_select(sql: str) -> None:
    """Valida que ``sql`` sea una única sentencia de lectura. Lanza si no."""
    limpio = sql.strip().rstrip(";").strip()
    if not limpio:
        raise SqlNoPermitido("La consulta está vacía.")
    if ";" in limpio:
        raise SqlNoPermitido("Solo se permite una sentencia SQL.")

    low = limpio.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise SqlNoPermitido("Solo se permiten consultas SELECT.")

    for kw in _PROHIBIDOS:
        if re.search(rf"\b{kw}\b", low):
            raise SqlNoPermitido(f"Palabra clave no permitida en una consulta: '{kw}'.")
