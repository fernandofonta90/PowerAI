"""Tests unitarios del cálculo de frescura."""

from datetime import UTC, datetime, timedelta

from app.domain.enums import EstadoFrescura, Frecuencia
from app.services.frescura import estado_frescura

AHORA = datetime(2026, 6, 12, tzinfo=UTC)


def test_sin_datos() -> None:
    assert estado_frescura(Frecuencia.SEMANAL, None, AHORA) is EstadoFrescura.SIN_DATOS


def test_semanal_al_dia() -> None:
    ultima = AHORA - timedelta(days=5)
    assert estado_frescura(Frecuencia.SEMANAL, ultima, AHORA) is EstadoFrescura.AL_DIA


def test_semanal_advertencia() -> None:
    ultima = AHORA - timedelta(days=10)  # entre 7 y 14 días
    assert estado_frescura(Frecuencia.SEMANAL, ultima, AHORA) is EstadoFrescura.ADVERTENCIA


def test_semanal_vencido() -> None:
    ultima = AHORA - timedelta(days=30)
    assert estado_frescura(Frecuencia.SEMANAL, ultima, AHORA) is EstadoFrescura.VENCIDO


def test_mensual_al_dia() -> None:
    ultima = AHORA - timedelta(days=20)  # <= 30
    assert estado_frescura(Frecuencia.MENSUAL, ultima, AHORA) is EstadoFrescura.AL_DIA
