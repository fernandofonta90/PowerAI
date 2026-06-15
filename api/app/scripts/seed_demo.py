"""Siembra todo lo necesario para la demo y el E2E del frontend.

Usuarios mock + plantillas + vistas del catálogo + el dataset sintético de
referencia (la misma cartera OTC del banco de evals, con datos MX y CO para lucir
el RBAC). Idempotente en lo sembrado por código; el dataset asume storage limpio.

    uv run python -m app.scripts.seed_demo
"""

from app.db import SessionLocal
from app.evals.dataset import construir_dataset
from app.scripts.seed_catalogo import sembrar_catalogo
from app.scripts.seed_dev import sembrar as sembrar_usuarios
from app.scripts.seed_experto import sembrar_experto
from app.scripts.seed_plantillas import sembrar_plantillas
from app.scripts.seed_ptp import sembrar_ptp
from app.scripts.seed_vistas import sembrar_vistas
from app.storage import get_almacen


def main() -> None:
    with SessionLocal() as db:
        almacen = get_almacen()
        usuarios = sembrar_usuarios(db)
        plantillas = sembrar_plantillas(db)
        vistas = sembrar_vistas(db)
        preguntas = sembrar_catalogo(db)
        expertos = sembrar_experto(db)
        construir_dataset(db, almacen)
        # PTP persistente (plantilla + vista + carga real PE/2025-11). Reproduce lo
        # creado por UI para que sobreviva a un reset de BD; omite la carga con aviso
        # si el archivo de datos no está presente (no rompe el resto del seed).
        sembrar_ptp(db, almacen)
    print(
        f"Demo lista: {usuarios} usuarios, {plantillas} plantillas OTC, {vistas} vistas OTC, "
        f"{preguntas} preguntas del catálogo, {expertos} experto(s), el dataset de "
        "referencia (cartera OTC MX/CO) y la torre PTP (Pagos a proveedores PTP)."
    )


if __name__ == "__main__":
    main()
