"""Siembra el Experto OTC como primer registro ACTIVO (M10).

Extrae el comportamiento hoy hardcodeado del agente a un registro ExpertoTorre
activo, sin cambiar el comportamiento: identidad/formato vienen de las constantes
de ``app.ia.experto`` y las fuentes permitidas son las 3 vistas del catálogo OTC.
Idempotente: actualiza el experto activo de OTC si ya existe.

    uv run python -m app.scripts.seed_experto
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.enums import EstadoExperto, Torre
from app.ia.experto import FORMATO_OTC, IDENTIDAD_OTC, NOMBRE_OTC
from app.models.experto import ExpertoTorre
from app.models.vista import VistaCatalogo


def sembrar_experto(db: Session) -> int:
    """Crea/actualiza el experto OTC activo. Devuelve cuántos procesó (1)."""
    vistas_otc = list(db.scalars(select(VistaCatalogo).where(VistaCatalogo.torre == Torre.OTC)))
    if not vistas_otc:
        raise RuntimeError("No hay vistas OTC; siembra las vistas del catálogo primero.")

    experto = db.scalars(
        select(ExpertoTorre).where(
            ExpertoTorre.torre == Torre.OTC, ExpertoTorre.estado == EstadoExperto.ACTIVO
        )
    ).first()
    if experto is None:
        experto = ExpertoTorre(torre=Torre.OTC, version=1, estado=EstadoExperto.ACTIVO)
        db.add(experto)
    experto.nombre = NOMBRE_OTC
    experto.identidad = IDENTIDAD_OTC
    experto.instrucciones_formato = FORMATO_OTC
    experto.fuentes = vistas_otc
    db.commit()
    return 1


def main() -> None:
    with SessionLocal() as db:
        total = sembrar_experto(db)
    print(f"Sembrado el experto OTC activo ({total}).")


if __name__ == "__main__":
    main()
