# Banco de preguntas doradas — Evaluación de calidad (M5)

Red de seguridad de PowerAI: un banco de preguntas con **respuesta correcta
verificada** que protege la confianza de los usuarios ante cada cambio de modelo,
prompt o catálogo.

## Estructura

```
evals/
├── preguntas/otc.yaml     # el banco (datos versionados)
└── README.md
api/app/evals/
├── dataset.py             # dataset sintético de referencia (resultados por construcción)
├── banco.py               # carga y valida el banco
└── runner.py              # runner: niveles motor y agente (CLI + funciones)
```

Cada pregunta del YAML tiene: `id`, `cu` (caso de uso origen), `pregunta` en
lenguaje natural, `variantes` de fraseo, `usuario` (define el alcance RBAC),
`respondible`, y —si es respondible— `sql_canonico` y `asercion` (valores
esperados exactos).

Las respuestas son correctas **por construcción** del dataset de referencia
(`api/app/evals/dataset.py`), no por un cálculo posterior. El usuario por defecto
es solo-MX: la cartera de CO del dataset nunca debe aparecer (prueba de RLS dentro
del propio banco).

## Dos niveles de evaluación

### Nivel motor (determinístico — corre en CI, **umbral 100%**)

Ejecuta el `sql_canonico` de cada pregunta por el motor M3 y compara el resultado
contra la aserción. No hay probabilidad, solo correctitud: cualquier fallo rompe
el build. Es el job obligatorio `evals` de CI (también cubierto por `pytest`).

```bash
cd api && uv run pytest tests/test_evals.py
```

### Nivel agente (gated por credenciales de Azure — **no corre en CI**, umbral ≥95%)

La `pregunta` en lenguaje natural y todas sus `variantes` entran por el agente M4
completo; su resultado se compara contra la misma aserción (y, para las preguntas
no respondibles, se exige honestidad: sin fuentes ni datos inventados). Por debajo
del 95% el runner sale con código de error y reporta qué preguntas fallaron.

Paso **manual pre-release** (requiere Azure OpenAI configurado en `api/.env` y el
entorno dev levantado con migraciones y seed aplicados):

```bash
cd api
# 1) Configura en api/.env: POWERAI_LLM_PROVIDER=azure_openai y las POWERAI_AZURE_OPENAI_*
# 2) Diagnóstico de conexión (falla con mensaje claro si falta algo):
uv run python -m app.scripts.check_llm
# 3) Eval del agente real contra el banco completo:
uv run python -m app.evals.runner --nivel agente
```

El reporte muestra la tasa de acierto sobre las 26 respondibles, el comportamiento
en las 3 no respondibles (debe mantener la honestidad) y, por cada fallo, el **SQL
generado** por el agente frente al **SQL esperado** — para diagnosticar si el ajuste
debe ir al prompt del agente o a las descripciones de las vistas del catálogo (el
motor y la RLS no se tocan). Sale con código ≠ 0 si la tasa < 95%.

(El runner también acepta `--nivel motor` para correrlo contra una BD real.)

## Añadir preguntas

1. Diseña el caso sobre el dataset de referencia (o amplíalo en `dataset.py` de
   forma que el resultado siga siendo conocido por construcción).
2. Agrega la entrada al YAML con su `sql_canonico` y, para fijar la `asercion`
   exacta, corre el nivel motor: si tu valor esperado no coincide, el test te dirá
   el valor real (la serialización de decimales es string, p. ej. `"5550.00"`).
3. Verde el nivel motor = aserción verificada.
