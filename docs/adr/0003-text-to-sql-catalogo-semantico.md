# ADR-0003: Text-to-SQL sobre catálogo semántico gobernado (no RAG para datos estructurados)

**Estado:** Aceptada · **Fecha:** 2026-06-12

## Contexto
El patrón dominante de los casos de uso son preguntas analíticas (top N, promedios, vencimientos, comparativos). El RAG clásico (embeddings + chunks) responde mal estas preguntas: no agrega, no suma, no agrupa. El text-to-SQL sin gobierno alucina nombres de columnas y métricas.

## Decisión
El agente de IA genera SQL únicamente contra un catálogo semántico: vistas curadas con nombres de negocio, descripciones de columnas y métricas validadas por cada torre. La seguridad a nivel de fila (torre × país) la aplica el motor de consulta, nunca el modelo. El RAG con pgvector se reserva para documentos no estructurados (contratos AP-10, políticas, plantillas GEN-04).

## Consecuencias
- (+) Reducción drástica de respuestas incorrectas; cada respuesta cita el SQL ejecutado y las fuentes.
- (+) El onboarding de una torre nueva = definir sus vistas y métricas (proceso repetible, Fase 3).
- (−) Requiere trabajo inicial de modelado con cada torre; es el costo de la confiabilidad.
