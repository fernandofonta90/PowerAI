"""Configuración de la aplicación, cargada desde variables de entorno.

Los secretos JAMÁS se versionan: en dev provienen de `.env`, en producción de
Azure Key Vault. Mantén `.env.example` actualizado con cada variable nueva.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes globales de la API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="POWERAI_",
        extra="ignore",
    )

    # Entorno de ejecución.
    entorno: Literal["dev", "test", "prod"] = "dev"

    # Proveedor de autenticación. En dev/test usamos mock; en prod, Entra ID.
    auth_provider: Literal["mock", "entra"] = "mock"

    # Conexión a PostgreSQL (base transaccional). Driver psycopg v3.
    database_url: str = "postgresql+psycopg://powerai:powerai_dev@localhost:5432/powerai"

    # Broker de Celery (Redis). Reservado para ingesta/alertas en milestones posteriores.
    redis_url: str = "redis://localhost:6379/0"

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "prod"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada (singleton por proceso)."""
    return Settings()
