"""Health checks de la API (liveness y readiness)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.db import get_db

router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    status: Literal["ok"]
    version: str


class ReadyStatus(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "error"]


@router.get("/health", response_model=HealthStatus)
def health() -> HealthStatus:
    """Liveness: el proceso responde."""
    return HealthStatus(status="ok", version=__version__)


@router.get("/health/ready", response_model=ReadyStatus)
def ready(db: Annotated[Session, Depends(get_db)]) -> ReadyStatus:
    """Readiness: dependencias críticas (PostgreSQL) accesibles."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return ReadyStatus(status="degraded", database="error")
    return ReadyStatus(status="ok", database="ok")
