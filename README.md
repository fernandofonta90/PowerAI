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
- **Fase actual:** Diseño — pendiente validación con liderazgo del SSC y Global Technology
- **Fase 1 (MVP):** Torre OTC, 8–10 semanas

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
├── api/                      # (Fase 1) Backend FastAPI
├── web/                      # (Fase 1) Frontend Next.js
└── infra/                    # (Fase 1) IaC Azure (Bicep/Terraform)
```

---

*Clasificación: uso interno ManpowerGroup.*
