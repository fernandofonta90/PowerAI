"""Detección y parseo de fechas de reportes reales (M15).

Los reportes reales no traen fechas en ISO. El formato se detecta POR COLUMNA
analizando sus valores, no se adivina por celda:

- Si todas las celdas son ISO (YYYY-MM-DD) → formato "iso".
- Si todas son fecha con separador '/' o '-' y año de 4 dígitos al final:
  - si alguna celda tiene el PRIMER campo > 12 → solo puede ser día primero → "dmy"
    (DD/MM/YYYY);
  - si alguna tiene el SEGUNDO campo > 12 → solo puede ser día segundo → "mdy"
    (MM/DD/YYYY);
  - si aparecen AMBAS señales → conflicto → ambiguo (None);
  - si NINGUNA (todos los campos ≤ 12) → genuinamente ambiguo (None): no se puede
    saber si 10/06 es 6-oct o 10-jun.
- Cualquier mezcla de formas o forma desconocida → None.

Una columna ambigua (None) NO se parsea como fecha: se trata como texto y se avisa,
en vez de corromper la fecha eligiendo un orden al azar.
"""

import re
from datetime import date

from app.ingesta.coercion import ValorInvalido

_ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
_SLASH = re.compile(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}")


def _forma(valor: str) -> str:
    if _ISO.fullmatch(valor):
        return "iso"
    if _SLASH.fullmatch(valor):
        return "slash"
    return "otro"


def detectar_formato_fecha(valores: list[str]) -> str | None:
    """Detecta el formato de una columna de fechas. Devuelve 'iso'|'dmy'|'mdy'|None.

    None = la columna no es una fecha reconocible o es genuinamente ambigua.
    """
    vals = [v.strip() for v in valores if v and v.strip()]
    if not vals:
        return None
    formas = {_forma(v) for v in vals}
    if formas == {"iso"}:
        return "iso"
    if formas != {"slash"}:
        return None  # mezcla de formas o forma desconocida

    dia_primero = mes_primero = False
    for v in vals:
        a, b, _ = (int(p) for p in re.split(r"[/-]", v))
        if a > 12:
            dia_primero = True
        if b > 12:
            mes_primero = True
    if dia_primero and mes_primero:
        return None  # conflicto: la columna mezcla DD/MM y MM/DD
    if dia_primero:
        return "dmy"
    if mes_primero:
        return "mdy"
    return None  # todos los campos ≤ 12: no se puede desambiguar


def parsear_fecha(valor: str, formato: str) -> date:
    """Parsea ``valor`` según el ``formato`` detectado para su columna."""
    v = valor.strip()
    try:
        if formato == "iso":
            return date.fromisoformat(v)
        partes = re.split(r"[/-]", v)
        if len(partes) != 3:
            raise ValueError
        a, b, anio = (int(p) for p in partes)
        if formato == "dmy":
            return date(anio, b, a)
        if formato == "mdy":
            return date(anio, a, b)
    except ValueError as exc:
        raise ValorInvalido(f"'{valor}' no es una fecha {formato} válida") from exc
    raise ValorInvalido(f"Formato de fecha no soportado: {formato}")
