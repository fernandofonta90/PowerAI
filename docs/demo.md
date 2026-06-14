# Guía de demo — PowerAI (Fase 1, chat analítico OTC)

Cómo levantar PowerAI en esta máquina y un guion de 5 pasos que luce el producto,
incluyendo el RBAC negando datos al cambiar de usuario.

> **Puertos en esta máquina:** 5432/6379/3000/3001 están ocupados por otros
> proyectos, así que la demo usa Postgres en **5434**, Redis en **6380** y el
> frontend en **3100**. En una máquina limpia puedes usar los puertos estándar.

## 1. Infraestructura (limpia)

```bash
cd powerai-repo
# Estado limpio (la siembra de demo no es idempotente sobre el storage):
docker compose down -v
POWERAI_POSTGRES_PORT=5434 POWERAI_REDIS_PORT=6380 docker compose up -d
```

## 2. Migraciones + datos de demo

```bash
cd api
export POWERAI_DATABASE_URL="postgresql+psycopg://powerai:powerai_dev@localhost:5434/powerai"
uv sync
uv run alembic upgrade head
uv run python -m app.scripts.seed_demo   # usuarios, plantillas, vistas y cartera OTC MX/CO
```

## 3. API (proveedor de IA fake — sin Azure)

```bash
cd api
export POWERAI_DATABASE_URL="postgresql+psycopg://powerai:powerai_dev@localhost:5434/powerai"
export POWERAI_REDIS_URL="redis://localhost:6380/0"
export POWERAI_LLM_PROVIDER=fake
export POWERAI_CORS_ORIGINS="http://localhost:3100"
uv run uvicorn app.main:app --port 8000
```

## 4. Frontend

```bash
cd web
npm install
POWERAI_API_URL=http://localhost:8000 npx next dev -p 3100
```

Abre **http://localhost:3100**.

## 5. Guion de demo (5 pasos)

1. **Identidad.** En el header (banda violeta), usa el selector *dev* y elige
   **Cargador MX**. El badge muestra `OTC · MX`: la torre y país del usuario
   siempre a la vista.
2. **Pregunta al centro.** En el home, haz clic en el chip
   **“¿Qué cliente tiene la mayor deuda vencida abierta?”** (las sugerencias salen
   del banco de preguntas doradas).
3. **Respuesta con fuentes.** En el chat verás: la respuesta del asistente (avatar
   sparkle), una **tabla** con los clientes de México (GLOBEX 3 500.00, ACME
   1 750.00, INITECH 300.00; montos a la derecha, decimales exactos), el **bloque
   de citación** al pie (archivo `otc_ar_abiertas_MX.csv`, versión, responsable,
   frescura **Al día**) y, a la derecha, **Fuentes activas — Filtrado: MX**. El SQL
   queda registrado en la bitácora de auditoría.
4. **Cambia de usuario.** En el selector *dev*, elige **Analista CO**. Pulsa
   **Nueva conversación** y vuelve a hacer clic en el mismo chip.
5. **RBAC en vivo.** Ahora la tabla muestra clientes de **Colombia** (CONACO,
   ANDESCO) y **jamás** los de México. El rail dice **Filtrado: CO**. Los datos
   fuera del alcance del usuario no existen en su sesión — la seguridad a nivel de
   fila la garantiza el motor por construcción, no un filtro de la interfaz.

> Detalle extra: con **Cargador MX** (rol uploader) la tarjeta “Fuentes de mi
> torre” del home muestra la acción **Cargar**; con **Analista CO** (rol consulta)
> esa acción desaparece.

## E2E automatizado (opcional)

Con la API (paso 3) y los datos de demo (pasos 1–2) arriba:

```bash
cd web
npx playwright install chromium   # una vez
POWERAI_WEB_URL=http://localhost:3100 npx playwright test
```

Cubre el flujo feliz (chip → respuesta con citación) y el RBAC (al cambiar a CO,
los datos de MX dejan de ser visibles).
