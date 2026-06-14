"""Siembra el catálogo navegable de preguntas desde el seed real.

Fuente de verdad: ``evals/catalogo_preguntas_seed.yaml`` (texto fiel al
levantamiento del SSC). NO se inventan preguntas: se respetan id, texto, torre,
categoría y estado tal cual el YAML. Idempotente por ``codigo``.

    uv run python -m app.scripts.seed_catalogo
"""

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.pregunta_catalogo import PreguntaCatalogo

ESTADOS_VALIDOS = {"activa", "proximamente"}


def ruta_seed() -> Path:
    """Ruta al seed del catálogo en la raíz del repo (independiente del cwd)."""
    return Path(__file__).resolve().parents[3] / "evals" / "catalogo_preguntas_seed.yaml"


def _filas_desde_yaml(datos: dict[str, Any]) -> list[dict[str, Any]]:
    """Aplana el YAML (torres → categorías → preguntas) a filas, preservando el orden."""
    filas: list[dict[str, Any]] = []
    orden = 0
    torres = datos.get("torres") or {}
    for clave_torre, bloque in torres.items():
        torre_nombre = bloque.get("nombre") or clave_torre
        for categoria in bloque.get("categorias") or []:
            nombre_cat = categoria["nombre"]
            for pregunta in categoria.get("preguntas") or []:
                estado = pregunta["estado"]
                if estado not in ESTADOS_VALIDOS:
                    raise ValueError(
                        f"Estado inválido '{estado}' en {pregunta['id']}; "
                        f"esperado uno de {sorted(ESTADOS_VALIDOS)}."
                    )
                filas.append(
                    {
                        "codigo": pregunta["id"],
                        "torre_clave": clave_torre,
                        "torre_nombre": torre_nombre,
                        "categoria": nombre_cat,
                        "texto": pregunta["texto"],
                        "estado": estado,
                        "orden": orden,
                    }
                )
                orden += 1
    if not filas:
        raise RuntimeError(f"Catálogo vacío en {ruta_seed()}")
    return filas


def cargar_filas() -> list[dict[str, Any]]:
    """Lee y valida el seed del catálogo."""
    datos = yaml.safe_load(ruta_seed().read_text(encoding="utf-8")) or {}
    return _filas_desde_yaml(datos)


def sembrar_catalogo(db: Session) -> int:
    """Crea o actualiza las preguntas del catálogo. Devuelve cuántas procesó."""
    filas = cargar_filas()
    for fila in filas:
        pregunta = db.scalar(
            select(PreguntaCatalogo).where(PreguntaCatalogo.codigo == fila["codigo"])
        )
        if pregunta is None:
            pregunta = PreguntaCatalogo(codigo=fila["codigo"])
            db.add(pregunta)
        pregunta.torre_clave = fila["torre_clave"]
        pregunta.torre_nombre = fila["torre_nombre"]
        pregunta.categoria = fila["categoria"]
        pregunta.texto = fila["texto"]
        pregunta.estado = fila["estado"]
        pregunta.orden = fila["orden"]
    db.commit()
    return len(filas)


def main() -> None:
    with SessionLocal() as db:
        total = sembrar_catalogo(db)
    print(f"Sembradas {total} preguntas del catálogo.")


if __name__ == "__main__":
    main()
