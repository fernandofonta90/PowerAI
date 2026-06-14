# ADR-0005: Experto configurable por torre, gobernado por evals

**Estado:** Aceptada · **Fecha:** 2026-06-14

## Contexto
El comportamiento del agente analítico (identidad, tono, formato de respuesta, fuentes que consulta) estaba hardcodeado en su system prompt, afinado para OTC. Al sumar torres, cada una necesita su propio "Experto" con voz y alcance propios, configurable por el negocio sin tocar código. Pero dar poder de configuración sobre un agente que responde con cifras financieras es riesgoso: una mala edición podría degradar la calidad o, peor, debilitar las salvaguardas anti-alucinación.

## Decisión
El comportamiento se eleva a una entidad `ExpertoTorre` por torre (identidad, instrucciones de formato, fuentes permitidas, estado, versión). El agente construye su prompt desde la config ACTIVA de la torre del usuario. Dos reglas vinculantes:

1. **Separación configurable vs estructural.** El admin de la torre edita solo: identidad/tono, instrucciones de formato y fuentes permitidas (de entre las vistas del catálogo de su torre). NO son configurables y viven en el motor/agente, no en la tabla: el RLS torre×país, el text-to-SQL gobernado sobre vistas curadas (ADR-0003) y la honestidad ante métricas no soportadas. El núcleo estructural se inyecta SIEMPRE en el prompt, entre la identidad y el formato; ninguna edición puede sustituirlo. La seguridad no se configura desde un formulario.

2. **Activación gobernada por evals.** "Guardar" no publica. Una configuración se guarda como borrador y solo se activa si, ejecutada contra el banco de preguntas doradas de su torre, alcanza el umbral del nivel agente (≥95%, ADR/M7). Si no pasa, no se activa y se reporta qué falló. La config activa anterior se archiva (rollback posible). Es el rigor de los evals del M7 aplicado a la configuración. Las fuentes permitidas acotan, además, qué vistas puede tocar el agente: una capa EXTRA sobre el RLS, nunca su reemplazo.

## Consecuencias
- (+) Cada torre tiene un experto con identidad propia sin desplegar código; refuerza la tesis anti-alucinación (un experto solo usa las fuentes asignadas y responde como se definió).
- (+) La configuración con poder queda con barandales: ninguna config llega a producción sin pasar sus evals; las salvaguardas estructurales son inmunes a la edición.
- (+) Versionado con rollback y auditoría del comportamiento vigente.
- (−) Solo se puede activar la config de una torre que tenga banco de evals; activar una torre nueva exige primero construir su banco (barandal deliberado).
- (−) La validación por evals consume tiempo/LLM al activar (no en cada respuesta): aceptable por ser una acción administrativa esporádica.
