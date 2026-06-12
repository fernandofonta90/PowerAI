"""Aplicación Celery de PowerAI (ingesta y, más adelante, alertas).

En tests/CI corre en modo eager (síncrono, sin broker) según la configuración.
"""

from celery import Celery

from app.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "powerai",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
)
celery_app.conf.task_always_eager = _settings.celery_eager
celery_app.conf.task_eager_propagates = True

# Importa las tareas para registrarlas en la app (tras crear celery_app).
from app.ingesta import tareas  # noqa: E402,F401
