"""Acceso a la base transaccional PostgreSQL (SQLAlchemy 2.x).

Solo metadata transaccional: usuarios, RBAC, catálogo, dashboards, auditoría.
Las consultas analíticas NUNCA pasan por aquí; van a DuckDB (ver ADR-0002).

El engine se construye de forma perezosa (en el primer uso), no al importar, para
que tome la configuración vigente —clave en tests, donde la URL apunta a un
PostgreSQL efímero que se conoce después de importar los módulos.
"""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Engine singleton, creado perezosamente con la configuración vigente."""
    return create_engine(get_settings().database_url, pool_pre_ping=True, future=True)


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def SessionLocal() -> Session:
    """Crea una nueva sesión (fábrica perezosa). Uso: ``with SessionLocal() as db``."""
    return get_sessionmaker()()


def get_db() -> Iterator[Session]:
    """Dependencia FastAPI: entrega una sesión por request y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
