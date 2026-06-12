"""Coerción de valores de texto a los tipos del dominio."""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from app.domain.enums import TipoColumna


class ValorInvalido(Exception):
    """Un valor no pudo convertirse al tipo esperado."""


def coercer(valor: str, tipo: TipoColumna) -> Any:
    """Convierte ``valor`` (texto) al tipo Python correspondiente a ``tipo``.

    Lanza :class:`ValorInvalido` si la conversión falla.
    """
    if tipo is TipoColumna.TEXTO:
        return valor
    if tipo is TipoColumna.ENTERO:
        try:
            return int(valor)
        except ValueError as exc:
            raise ValorInvalido(f"'{valor}' no es un entero") from exc
    if tipo is TipoColumna.DECIMAL:
        try:
            return Decimal(valor)
        except InvalidOperation as exc:
            raise ValorInvalido(f"'{valor}' no es un decimal") from exc
    if tipo is TipoColumna.FECHA:
        try:
            return date.fromisoformat(valor)
        except ValueError as exc:
            raise ValorInvalido(f"'{valor}' no es una fecha ISO (YYYY-MM-DD)") from exc
    raise ValorInvalido(f"Tipo no soportado: {tipo}")
