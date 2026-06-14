"""Siembra todo lo necesario para la demo y el E2E del frontend.

Usuarios mock + plantillas + vistas del catálogo + el dataset sintético de
referencia (la misma cartera OTC del banco de evals, con datos MX y CO para lucir
el RBAC). Idempotente en lo sembrado por código; el dataset asume storage limpio.

    uv run python -m app.scripts.seed_demo
"""

from app.db import SessionLocal
from app.evals.dataset import construir_dataset
from app.scripts.seed_dev import sembrar as sembrar_usuarios
from app.scripts.seed_plantillas import sembrar_plantillas
from app.scripts.seed_vistas import sembrar_vistas
from app.storage import get_almacen


def main() -> None:
    with SessionLocal() as db:
        usuarios = sembrar_usuarios(db)
        plantillas = sembrar_plantillas(db)
        vistas = sembrar_vistas(db)
        construir_dataset(db, get_almacen())
    print(
        f"Demo lista: {usuarios} usuarios, {plantillas} plantillas, {vistas} vistas "
        "y el dataset de referencia (cartera OTC MX/CO)."
    )


if __name__ == "__main__":
    main()
