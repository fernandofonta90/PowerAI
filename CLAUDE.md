# CLAUDE.md — PowerAI

## Qué es este proyecto

PowerAI es la plataforma de inteligencia analítica del SSC Finanzas LATAM de ManpowerGroup (15 países, torres OTC, PTP, RTR, QCI, CARE, HTR). Permite a usuarios de negocio: (1) cargar reportes periódicos por torre, (2) hacer preguntas en lenguaje natural sobre esos datos (chat analítico), (3) generar dashboards con IA que se guardan y se actualizan con cada nueva carga, y (4) recibir alertas de desviaciones en Microsoft Teams.

**Antes de implementar cualquier cosa, lee:**
- `docs/arquitectura.md` — documento de arquitectura completo
- `docs/adr/` — las 4 decisiones de arquitectura son vinculantes, no sugerencias
- `docs/casos-de-uso.md` — los casos funcionales que se están resolviendo

## Metodología de trabajo

- **Claude Web actúa como arquitecto/asesor; Claude Code (tú) implementa.** Las decisiones de arquitectura ya están tomadas en los ADRs. Si una implementación requiere desviarse de un ADR, NO lo hagas silenciosamente: detente, explica el conflicto y propón un nuevo ADR.
- Trabajo incremental por milestones con criterios de aceptación explícitos. Cada milestone termina con tests en verde antes de pasar al siguiente.
- Commits convencionales en español: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`. Mensajes descriptivos con cuerpo cuando el cambio lo amerite.
- Nunca marques una tarea como completada sin tests que lo demuestren.

## Stack (vinculante — ver ADR-0001 y ADR-0002)

| Capa | Tecnología | Notas |
|---|---|---|
| Backend | Python 3.12 + FastAPI | En `api/`. Pydantic v2 para schemas. |
| Async | Celery + Redis | Ingesta y jobs de alertas, nunca en el request. |
| Base transaccional | PostgreSQL 16 + pgvector | Metadata, RBAC, catálogo, dashboards, auditoría. SQLAlchemy 2.x + Alembic. |
| Motor analítico | DuckDB sobre Parquet | Las consultas analíticas NUNCA van a PostgreSQL. |
| Object storage | Azure Blob (prod) / Azurite (dev local) | Archivos originales versionados + datasets Parquet. |
| Frontend | Next.js 14+ (App Router) + Tailwind | En `web/`. TypeScript estricto. |
| IA | Azure OpenAI vía capa adapter | Ver "Capa de IA" abajo. |
| Identidad | Entra ID (prod) / mock auth (dev) | El RBAC se diseña desde el día 1, no se parcha después. |
| Infra | Bicep en `infra/` | Azure Container Apps. |

## Reglas de arquitectura no negociables

1. **Text-to-SQL solo contra el catálogo semántico** (ADR-0003). El LLM nunca ve ni consulta tablas crudas. Genera SQL contra vistas curadas registradas en el catálogo. La seguridad a nivel de fila (torre × país) la aplica el motor de consulta inyectando filtros, NUNCA se confía en que el modelo los incluya.
2. **Dashboards = spec JSON declarativa** (ADR-0004). El LLM genera specs, jamás código ejecutable. El frontend renderiza la spec. Versionar el schema de la spec desde v1.
3. **Toda respuesta cita sus fuentes**: archivo(s), fecha de carga, responsable de carga, y el SQL ejecutado queda en la bitácora de auditoría.
4. **Conciliaciones híbridas**: el matching es determinístico (reglas + fuzzy matching); el LLM solo explica partidas no conciliadas. Cierre siempre con validación humana registrada.
5. **Capa adapter de IA**: interfaz `LLMProvider` con implementaciones intercambiables. Dev local puede usar un provider local; producción usa Azure OpenAI. La lógica de negocio nunca importa SDKs de un proveedor directamente.
6. **Cada carga de archivo es inmutable**: se versiona, nunca se sobrescribe. El Parquet derivado referencia la versión del archivo origen.

## Seguridad y datos

- **NUNCA commitear datos del SSC**: ni xlsx, ni csv, ni parquet, ni fixtures con datos reales (el `.gitignore` ya los excluye — no lo debilites). Los tests usan datos sintéticos generados.
- Secretos solo por variables de entorno (`.env` local, Azure Key Vault en prod). Mantén `.env.example` actualizado con cada variable nueva, sin valores reales.
- Toda ruta de la API valida permisos torre × país. No existen endpoints "internos sin auth".
- Logs de auditoría: pregunta, respuesta, SQL ejecutado, fuentes usadas, usuario, timestamp. Es requisito de auditoría interna, no opcional.

## Convenciones de código

- **Python**: ruff (lint + format), mypy estricto en `api/`. Nombres de dominio en español cuando reflejan el negocio (`torre`, `carga`, `plantilla_reporte`), código técnico en inglés. Docstrings en español.
- **TypeScript**: ESLint + Prettier. Componentes en `web/components/`, server actions sobre fetch manual cuando aplique.
- **Tests**: pytest en `api/tests/` (unit + integration con testcontainers para Postgres), Vitest + Playwright en `web/`. Cobertura objetivo: 85%+ en la API.
- **Migraciones**: toda alteración de schema vía Alembic, nunca SQL manual.

## Fase 1 — MVP OTC (alcance actual)

Implementar en este orden, cada milestone con sus tests:

- **M1 — Fundación**: monorepo operativo, docker-compose dev (Postgres, Redis, Azurite), FastAPI con health check, Next.js con layout base, mock auth con roles torre × país, CI básico (lint + tests).
- **M2 — Plantillas y carga**: entidad `PlantillaReporte` (esquema esperado, mapeo de columnas, validaciones), endpoint de carga con validación, normalización a Parquet en storage, catálogo de archivos con versión/país/periodo/responsable. Plantillas iniciales: los 3 reportes del Aging OTC (AR abiertas, pagos unapplied, revenue reconciliation).
- **M3 — Catálogo semántico y motor de consulta**: registro de vistas DuckDB sobre los Parquet, definiciones de negocio, row-level security por torre × país inyectada por el motor.
- **M4 — Chat analítico**: agente con tool-calling sobre el catálogo (capa adapter), respuestas con citación de fuentes, panel de fuentes activas con frescura, bitácora de auditoría completa.
- **M5 — Calidad**: banco de preguntas doradas de OTC (derivadas de CU-00 a CU-07) como suite de evals automatizada que corre en CI.

Fuera de alcance de Fase 1 (no implementar todavía): dashboards, alertas a Teams, conciliaciones, conectores directos a Oracle/SharePoint, módulo de voz.

## Comandos esperados (mantener actualizados al implementarlos)

```bash
# Levantar entorno dev completo
docker compose up -d
# API
cd api && uvicorn app.main:app --reload
# Tests API
cd api && pytest
# Frontend
cd web && npm run dev
# Lint todo
make lint
```

## Definición de terminado (DoD) por milestone

- Tests unitarios e integración en verde, cobertura sostenida.
- Migraciones aplicables desde cero (`alembic upgrade head` en BD limpia).
- Sin secretos ni datos reales en el repo.
- `docs/` actualizado si la implementación afectó decisiones o flujos.
- Commit(s) convencionales con mensaje descriptivo.
