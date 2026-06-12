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

    # Broker y backend de resultados de Celery (Redis).
    redis_url: str = "redis://localhost:6379/0"

    # En tests/CI, Celery corre en modo eager (tareas síncronas, sin worker).
    celery_eager: bool = False

    # Conexión a Azure Blob Storage. Por defecto, el endpoint de Azurite (dev).
    # En prod proviene de Key Vault. NUNCA un valor real en el repo.
    blob_connection_string: str = (
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
        "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
        "K1SZFPTOtr/KBHBeksoGMGw==;"
        "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )

    @property
    def es_produccion(self) -> bool:
        return self.entorno == "prod"


@lru_cache
def get_settings() -> Settings:
    """Devuelve la configuración cacheada (singleton por proceso)."""
    return Settings()
