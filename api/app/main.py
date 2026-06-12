"""Punto de entrada de la API FastAPI de PowerAI."""

from fastapi import FastAPI

from app import __version__
from app.routers import auth, cargas, consulta, health, plantillas


def create_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""
    app = FastAPI(
        title="PowerAI API",
        description="Plataforma de inteligencia analítica del SSC Finanzas LATAM.",
        version=__version__,
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(plantillas.router)
    app.include_router(cargas.router)
    app.include_router(consulta.router)
    return app


app = create_app()
