# API — PowerAI

Backend **FastAPI** (Python 3.12) del SSC Finanzas LATAM. Gestiona metadata
transaccional, RBAC torre × país y, en milestones siguientes, la ingesta de
reportes y el chat analítico.

## Requisitos

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- Entorno dev levantado: `docker compose up -d` (desde la raíz)

## Puesta en marcha

```bash
cd api
cp .env.example .env          # ajusta POWERAI_DATABASE_URL si cambiaste puertos
uv sync                       # instala dependencias
uv run alembic upgrade head   # crea el esquema desde cero
uv run python -m app.scripts.seed_dev   # usuarios mock + plantillas OTC
uv run uvicorn app.main:app --reload
# En otra terminal, el worker de ingesta (normalización a Parquet):
uv run celery -A app.worker.celery_app worker --loglevel=info
```

## Comandos

```bash
uv run pytest                       # tests (unit + integración con testcontainers)
uv run ruff check . && uv run ruff format --check .
uv run mypy app                     # tipos estrictos
uv run alembic revision --autogenerate -m "mensaje"   # nueva migración
```

## Autenticación en desarrollo (mock)

El proveedor `mock` resuelve la identidad desde el header `X-Mock-User` (email)
contra la tabla `usuario`. Usuarios sembrados por `seed_dev`:

| Email | Acceso |
|---|---|
| `admin.otc@powerai.dev` | OTC, todos los países (admin) |
| `uploader.mx@powerai.dev` | OTC / MX (uploader) |
| `consulta.co@powerai.dev` | OTC / CO (consulta) |
| `multi.torre@powerai.dev` | OTC/MX y PTP/AR (consulta) |

```bash
curl localhost:8000/me -H "X-Mock-User: admin.otc@powerai.dev"
curl "localhost:8000/otc/aging?pais=MX" -H "X-Mock-User: uploader.mx@powerai.dev"
```

## Carga y catálogo (M2)

Plantillas OTC sembradas: `otc_ar_abiertas`, `otc_pagos_unapplied`,
`otc_revenue_recon`. El flujo de carga valida el esquema de forma síncrona
(país y periodo declarados se verifican contra el contenido) y encola la
normalización a Parquet en el worker Celery.

```bash
# Subir un reporte (rol uploader/admin de la torre y país)
curl -X POST localhost:8000/cargas \
  -H "X-Mock-User: uploader.mx@powerai.dev" \
  -F "plantilla_codigo=otc_ar_abiertas" -F "pais=MX" -F "periodo=2026-07" \
  -F "archivo=@aging.csv;type=text/csv"

# Estado de la carga (recibida → procesando → disponible/fallida)
curl localhost:8000/cargas/<id> -H "X-Mock-User: uploader.mx@powerai.dev"

# Catálogo (filtrado por RBAC torre × país) y frescura
curl localhost:8000/catalogo -H "X-Mock-User: admin.otc@powerai.dev"
curl "localhost:8000/catalogo/frescura?torre=OTC" -H "X-Mock-User: admin.otc@powerai.dev"
curl localhost:8000/plantillas -H "X-Mock-User: admin.otc@powerai.dev"
```

Genera un CSV de muestra sintético con `app.scripts.muestras.generar_csv`.

## Estructura

```
app/
├── main.py            # creación de la app FastAPI
├── config.py          # settings desde entorno (POWERAI_*)
├── db.py              # engine/sesión SQLAlchemy
├── domain/enums.py    # Torre, Pais, Rol (dimensiones de RBAC)
├── models/            # ORM: Usuario, AsignacionPermiso
├── auth/              # proveedores, schemas y deps de autorización
├── routers/           # health, auth (/me, ruta protegida de ejemplo)
└── scripts/seed_dev.py
migrations/            # Alembic
tests/                 # pytest (unit + integración)
```
