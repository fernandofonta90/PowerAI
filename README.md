# PowerAI

**Plataforma de Inteligencia Analítica del SSC Finanzas LATAM**
ManpowerGroup LATAM — Tecnología y Transformación Digital

PowerAI es una plataforma interna donde cada torre del Shared Service Center (OTC, PTP, RTR, QCI, CARE, HTR) carga sus reportes periódicos o se conecta a sus fuentes, y cualquier usuario autorizado puede:

- Conversar con la información en **lenguaje natural** (chat analítico)
- Generar **dashboards con IA**, guardarlos y reutilizarlos (se actualizan con cada nueva carga)
- Recibir **alertas automáticas** de desviaciones en Microsoft Teams
- Ver en todo momento **qué archivos y fuentes** sustentan cada respuesta, con su fecha de actualización

## Documentación

| Documento | Descripción |
|---|---|
| [docs/arquitectura.md](docs/arquitectura.md) | Documento de arquitectura y business case (v0.1) |
| [docs/casos-de-uso.md](docs/casos-de-uso.md) | Resumen del levantamiento de casos de uso del SSC |
| [docs/adr/](docs/adr/) | Architecture Decision Records |

## Stack (resumen)

| Capa | Tecnología |
|---|---|
| Frontend | Next.js (React) + Tailwind |
| Backend | Python + FastAPI |
| Async | Celery + Azure Cache for Redis |
| Base transaccional | Azure Database for PostgreSQL (+ pgvector) |
| Motor analítico | DuckDB sobre Parquet |
| Storage | Azure Blob Storage |
| IA | Azure OpenAI (capa adapter multi-modelo) |
| Identidad | Microsoft Entra ID (SSO) |
| Despliegue | Azure Container Apps |

## Estado

- **Versión de la documentación:** 0.1 (borrador para revisión)
- **Fase 1 (MVP):** Torre OTC, 8–10 semanas
- **Milestone actual:** M1 — Fundación (monorepo, entorno dev, FastAPI con health
  check, Next.js con layout base, mock auth torre × país, CI). ✅

## Desarrollo local

Requisitos: Docker, Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 20+.

```bash
# 1. Infraestructura dev (Postgres, Redis, Azurite)
cp .env.example .env          # opcional: ajusta puertos si chocan con otros servicios
docker compose up -d

# 2. API
cd api && cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_dev
uv run uvicorn app.main:app --reload   # http://localhost:8000

# 3. Frontend (en otra terminal)
cd web && npm install
npm run dev                            # http://localhost:3000
```

Atajos: `make up`, `make lint`, `make test` (ver `make help`). Detalle de la API
en [api/README.md](api/README.md).

## Estructura del repositorio

```
powerai/
├── README.md
├── docs/
│   ├── arquitectura.md       # Documento principal de arquitectura
│   ├── casos-de-uso.md       # Levantamiento de casos por torre
│   ├── adr/                  # Decisiones de arquitectura
│   │   ├── 0001-stack-azure-nativo.md
│   │   ├── 0002-duckdb-parquet-motor-analitico.md
│   │   ├── 0003-text-to-sql-catalogo-semantico.md
│   │   └── 0004-dashboards-como-spec-declarativa.md
│   └── assets/
│       └── arquitectura_powerai.png
├── docker-compose.yml        # entorno dev: Postgres, Redis, Azurite
├── Makefile                  # atajos: up, lint, test, migrate, seed
├── .github/workflows/ci.yml  # CI: lint + tests de api y web
├── api/                      # Backend FastAPI (app, migraciones, tests)
├── web/                      # Frontend Next.js (App Router + Tailwind)
└── infra/                    # IaC Azure (Bicep) — esqueleto Fase 1
```

---

*Clasificación: uso interno ManpowerGroup.*
