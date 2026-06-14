"""Esquema declarativo de un dashboard (spec v1) — ADR-0004.

El LLM genera esta SPEC (datos, no código): una lista de visuales, cada uno con
su consulta SQL sobre las vistas del catálogo. El frontend la renderiza; el motor
de M3 ejecuta las queries (RLS por construcción). Versionado desde v1.
"""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ValidationError, model_validator

from app.ia.sql_guard import SqlNoPermitido, validar_select


class TipoVisual(StrEnum):
    """Vocabulario mínimo y suficiente de visuales para OTC."""

    KPI = "kpi"  # valor único
    TABLA = "tabla"
    BARRAS = "barras"
    LINEAS = "lineas"  # tendencia
    DISTRIBUCION = "distribucion"  # p. ej. aging por tramos


class FormatoValor(StrEnum):
    ENTERO = "entero"
    DECIMAL = "decimal"  # monto al centavo (string, sin float)
    TEXTO = "texto"


class Visual(BaseModel):
    tipo: TipoVisual
    titulo: str
    sql: str  # SELECT sobre las vistas del catálogo
    # Mapeo de columnas del resultado a la geometría del visual:
    columna_valor: str | None = None  # KPI: columna del valor único
    eje_x: str | None = None  # categoría/tiempo en barras/líneas/distribución
    eje_y: str | None = None  # valor numérico en barras/líneas/distribución
    formato: FormatoValor = FormatoValor.TEXTO

    @model_validator(mode="after")
    def _validar(self) -> "Visual":
        try:
            validar_select(self.sql)
        except SqlNoPermitido as exc:
            raise ValueError(f"SQL del visual '{self.titulo}' inválido: {exc}") from exc

        if self.tipo is TipoVisual.KPI and not self.columna_valor:
            raise ValueError(f"El visual KPI '{self.titulo}' requiere 'columna_valor'.")
        if self.tipo in (TipoVisual.BARRAS, TipoVisual.LINEAS, TipoVisual.DISTRIBUCION) and not (
            self.eje_x and self.eje_y
        ):
            raise ValueError(
                f"El visual '{self.titulo}' ({self.tipo.value}) requiere 'eje_x' y 'eje_y'."
            )
        return self


class DashboardSpec(BaseModel):
    version: Literal[1] = 1
    titulo: str
    visuales: list[Visual]

    @model_validator(mode="after")
    def _no_vacio(self) -> "DashboardSpec":
        if not self.visuales:
            raise ValueError("El dashboard debe tener al menos un visual.")
        return self


class SpecInvalida(Exception):
    """La spec del dashboard no es válida. Lleva el detalle legible."""


def validar_spec(datos: dict[str, Any]) -> DashboardSpec:
    """Valida un dict como DashboardSpec; lanza SpecInvalida con mensaje claro."""
    try:
        return DashboardSpec.model_validate(datos)
    except ValidationError as exc:
        errores = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()
        )
        raise SpecInvalida(errores) from exc
