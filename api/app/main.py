"""Punto de entrada de la API FastAPI de PowerAI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import get_settings
from app.routers import (
    auth,
    cargas,
    chat,
    consulta,
    dashboards,
    health,
    plantillas,
    torres,
)


def create_app() -> FastAPI:
    """Crea y configura la instancia de FastAPI."""
    app = FastAPI(
        title="PowerAI API",
        description="Plataforma de inteligencia analítica del SSC Finanzas LATAM.",
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().lista_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(plantillas.router)
    app.include_router(cargas.router)
    app.include_router(consulta.router)
    app.include_router(chat.router)
    app.include_router(torres.router)
    app.include_router(dashboards.router)
    return app


app = create_app()
