"""Cálculo de frescura de datasets contra la frecuencia esperada de la plantilla.

Alimenta el badge verde/ámbar/rojo del design system: al día si la última carga
está dentro de la cadencia esperada, advertencia hasta el doble, vencido más allá.
"""

from datetime import datetime

from app.domain.enums import DIAS_POR_FRECUENCIA, EstadoFrescura, Frecuencia


def estado_frescura(
    frecuencia: Frecuencia, ultima_actualizacion: datetime | None, ahora: datetime
) -> EstadoFrescura:
    """Determina el estado de frescura de un dataset."""
    if ultima_actualizacion is None:
        return EstadoFrescura.SIN_DATOS

    dias = (ahora - ultima_actualizacion).total_seconds() / 86400
    limite = DIAS_POR_FRECUENCIA[frecuencia]
    if dias <= limite:
        return EstadoFrescura.AL_DIA
    if dias <= 2 * limite:
        return EstadoFrescura.ADVERTENCIA
    return EstadoFrescura.VENCIDO
