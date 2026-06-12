"""Acceso a la base transaccional PostgreSQL (SQLAlchemy 2.x).

Solo metadata transaccional: usuarios, RBAC, catálogo, dashboards, auditoría.
Las consultas analíticas NUNCA pasan por aquí; van a DuckDB (ver ADR-0002).
"""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_settings = get_settings()

engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependencia FastAPI: entrega una sesión por request y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
