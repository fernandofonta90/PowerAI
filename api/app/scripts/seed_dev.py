"""Siembra usuarios de desarrollo para el mock auth.

Los datos son SINTÉTICOS (no provienen del SSC). Idempotente: actualiza los
grants de cada usuario por email en cada corrida. Ejecutar tras las migraciones:

    uv run python -m app.scripts.seed_dev
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.domain.enums import PAIS_TODOS, Rol, Torre
from app.models.usuario import AsignacionPermiso, Usuario

# (email, nombre, [(torre, pais, rol), ...]) — usuarios ficticios de prueba.
USUARIOS_DEV: list[tuple[str, str, list[tuple[Torre, str, Rol]]]] = [
    (
        "admin.otc@powerai.dev",
        "Admin OTC (todos los países)",
        [(Torre.OTC, PAIS_TODOS, Rol.ADMIN)],
    ),
    (
        "uploader.mx@powerai.dev",
        "Cargador OTC México",
        [(Torre.OTC, "MX", Rol.UPLOADER)],
    ),
    (
        "consulta.co@powerai.dev",
        "Analista OTC Colombia",
        [(Torre.OTC, "CO", Rol.CONSULTA)],
    ),
    (
        "multi.torre@powerai.dev",
        "Usuario multi-torre",
        [(Torre.OTC, "MX", Rol.CONSULTA), (Torre.PTP, "AR", Rol.CONSULTA)],
    ),
]


def sembrar(db: Session) -> int:
    """Crea o actualiza los usuarios de desarrollo. Devuelve cuántos procesó."""
    for email, nombre, grants in USUARIOS_DEV:
        usuario = db.scalar(select(Usuario).where(Usuario.email == email))
        if usuario is None:
            usuario = Usuario(email=email, nombre=nombre, activo=True)
            db.add(usuario)
            db.flush()
        else:
            usuario.nombre = nombre
            usuario.activo = True
            usuario.asignaciones.clear()
            db.flush()

        for torre, pais, rol in grants:
            usuario.asignaciones.append(AsignacionPermiso(torre=torre, pais=pais, rol=rol))
    db.commit()
    return len(USUARIOS_DEV)


def main() -> None:
    from app.scripts.seed_catalogo import sembrar_catalogo
    from app.scripts.seed_experto import sembrar_experto
    from app.scripts.seed_plantillas import sembrar_plantillas
    from app.scripts.seed_vistas import sembrar_vistas

    with SessionLocal() as db:
        usuarios = sembrar(db)
        plantillas = sembrar_plantillas(db)
        vistas = sembrar_vistas(db)
        preguntas = sembrar_catalogo(db)
        expertos = sembrar_experto(db)
    print(
        f"Sembrados {usuarios} usuarios (mock auth), {plantillas} plantillas OTC, "
        f"{vistas} vistas del catálogo, {preguntas} preguntas del catálogo y "
        f"{expertos} experto(s) de torre."
    )


if __name__ == "__main__":
    main()
