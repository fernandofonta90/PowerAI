# Makefile raíz de PowerAI — orquesta tareas comunes de api/ y web/.
.DEFAULT_GOAL := help
.PHONY: help up down logs lint lint-api lint-web test test-api test-web \
        format migrate seed install install-api install-web

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Levanta el entorno dev (Postgres, Redis, Azurite)
	docker compose up -d

down: ## Detiene el entorno dev
	docker compose down

logs: ## Sigue los logs del entorno dev
	docker compose logs -f

install: install-api install-web ## Instala dependencias de api y web

install-api: ## Instala dependencias de la API (uv)
	cd api && uv sync

install-web: ## Instala dependencias del frontend (npm)
	cd web && npm install

lint: lint-api lint-web ## Lint de api y web

lint-api: ## Ruff + mypy sobre la API
	cd api && uv run ruff check . && uv run ruff format --check . && uv run mypy app

lint-web: ## ESLint + chequeo de tipos sobre el frontend
	cd web && npm run lint && npm run typecheck

format: ## Formatea la API con ruff
	cd api && uv run ruff format . && uv run ruff check --fix .

test: test-api test-web ## Tests de api y web

test-api: ## pytest sobre la API
	cd api && uv run pytest

test-web: ## Vitest sobre el frontend
	cd web && npm run test

migrate: ## Aplica migraciones Alembic desde cero hasta head
	cd api && uv run alembic upgrade head

seed: ## Siembra usuarios y plantillas de desarrollo
	cd api && uv run python -m app.scripts.seed_dev

worker: ## Levanta el worker Celery de ingesta vía compose (profile worker)
	docker compose --profile worker up -d worker

worker-local: ## Corre el worker Celery localmente (sin docker)
	cd api && uv run celery -A app.worker.celery_app worker --loglevel=info
