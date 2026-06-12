# ADR-0004: Dashboards como especificación declarativa generada por IA

**Estado:** Aceptada · **Fecha:** 2026-06-12

## Contexto
Los usuarios requieren dashboards generados por IA que puedan guardarse y reutilizarse (GEN-01, IA-T01). Generar código (React/HTML) al vuelo es frágil, inseguro y difícil de versionar. Generar archivos .pbix programáticamente no es viable de forma robusta.

## Decisión
El modelo genera una especificación JSON declarativa: lista de visuales (tipo, ejes, formato) más la consulta SQL del catálogo que alimenta cada visual. El frontend renderiza la spec con una librería de charts. Guardar un dashboard = persistir {spec, queries, filtros} en PostgreSQL. Al abrirlo, las queries se re-ejecutan: el dashboard se actualiza con cada nueva carga.

## Consecuencias
- (+) Dashboards vivos, versionables, auditables y compartibles por torre.
- (+) Superficie de ataque mínima: el modelo nunca produce código ejecutable.
- (+) Interoperabilidad: los datasets Parquet quedan expuestos para quien quiera conectar Power BI encima.
- (−) El vocabulario de visuales está acotado a lo que la spec soporta; se amplía por versión de schema.
