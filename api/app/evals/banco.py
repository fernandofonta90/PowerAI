"""Carga del banco de preguntas doradas (YAML en evals/preguntas)."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class Asercion(BaseModel):
    filas: list[list[Any]]


class PreguntaDorada(BaseModel):
    id: str
    cu: str
    pregunta: str
    variantes: list[str] = []
    usuario: str
    respondible: bool
    sql_canonico: str | None = None
    asercion: Asercion | None = None

    def fraseos(self) -> list[str]:
        """La pregunta principal y todas sus variantes."""
        return [self.pregunta, *self.variantes]


def directorio_banco() -> Path:
    """Ruta a evals/preguntas en la raíz del repo (independiente del cwd)."""
    return Path(__file__).resolve().parents[3] / "evals" / "preguntas"


def cargar_banco() -> list[PreguntaDorada]:
    """Carga y valida todas las preguntas de los YAML del banco."""
    preguntas: list[PreguntaDorada] = []
    for archivo in sorted(directorio_banco().glob("*.yaml")):
        datos = yaml.safe_load(archivo.read_text(encoding="utf-8")) or []
        preguntas.extend(PreguntaDorada.model_validate(d) for d in datos)
    if not preguntas:
        raise RuntimeError(f"Banco vacío en {directorio_banco()}")
    return preguntas
