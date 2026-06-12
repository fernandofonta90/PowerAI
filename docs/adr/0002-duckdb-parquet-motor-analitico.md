# ADR-0002: DuckDB sobre Parquet como motor analítico

**Estado:** Aceptada · **Fecha:** 2026-06-12

## Contexto
La mayoría de los casos de uso son consultas analíticas (agregaciones, rankings, distribuciones) sobre reportes periódicos de tamaño moderado (decenas de miles a pocos millones de filas por carga). Un warehouse dedicado (Synapse, Databricks, Snowflake) agregaría costo fijo y complejidad operativa desproporcionados.

## Decisión
Los archivos cargados se normalizan a Parquet en Azure Blob. DuckDB (embebido en el backend FastAPI) ejecuta las consultas SQL directamente sobre los Parquet. PostgreSQL queda solo para metadata transaccional.

## Alternativas consideradas
- **Azure Synapse / Fabric:** sobredimensionado para el volumen; costo fijo alto.
- **Solo PostgreSQL:** viable al inicio, pero las consultas analíticas sobre tablas anchas degradan; Parquet columnar es superior para este patrón.

## Consecuencias
- (+) Costo marginal cercano a cero; rendimiento columnar excelente para el volumen del SSC.
- (+) El versionado de datasets es trivial: cada carga es un Parquet inmutable.
- (−) Si el volumen creciera 100x, se evaluaría motor distribuido; la frontera Parquet hace la migración directa (Fabric/Databricks leen los mismos archivos).
