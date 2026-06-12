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
uv run python -m app.scripts.seed_dev   # usuarios mock de desarrollo
uv run uvicorn app.main:app --reload
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
