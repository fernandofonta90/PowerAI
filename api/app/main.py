"""Punto de entrada de la API FastAPI de PowerAI."""

from fastapi import FastAPI

from app import __version__
from app.routers import auth, health


def create_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""
    app = FastAPI(
        title="PowerAI API",
        description="Plataforma de inteligencia analítica del SSC Finanzas LATAM.",
        version=__version__,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    return app


app = create_app()
