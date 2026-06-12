# Imagen de producción de PowerAI (API y worker comparten base).
#
# Base compartida: API y worker tienen el MISMO cierre de dependencias y el mismo
# código (el worker importa app.worker/app.ingesta/app.motor). Un Dockerfile con
# dos stages finales (api, worker) evita duplicar capas: solo cambia el comando.
# Construir con:  docker build --target api ./api   |   --target worker ./api
#
# Imagen slim, sin dev-dependencies, usuario no-root.

FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependencias primero (capa cacheable), sin dev y sin el proyecto.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Código y instalación final del proyecto (sin dev).
COPY . .
RUN uv sync --frozen --no-dev

# Usuario no-root.
RUN useradd --create-home --uid 10001 powerai && chown -R powerai:powerai /app
USER powerai


FROM base AS api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS worker
CMD ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info"]
