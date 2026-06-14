# ADR-0006: Plantillas y vistas por descubrimiento, con definición gobernada

**Estado:** Aceptada · **Fecha:** 2026-06-14

## Contexto
Hasta M10 las plantillas (esquema esperado de cada reporte) y sus vistas curadas del catálogo se sembraban desde supuestos en código. Eso no escala a 6 torres × 15 países, donde quien conoce cada reporte es el negocio, no el desarrollador. Se necesita que las plantillas y vistas sean definibles por quien carga los datos, sin que ello debilite la disciplina de entrada ni el gobierno del catálogo (ADR-0003).

## Decisión
La estructura se descubre desde la primera carga y se gobierna:

1. **Descubrimiento.** Al subir un archivo de un tipo aún inexistente en la torre, el sistema lee los encabezados (sin procesar) y los muestra. El usuario confirma el mapeo (nombre de negocio + tipo: texto/entero/decimal/fecha) e indica las llaves de país y periodo. Nace la plantilla y, automáticamente, una **vista 1:1** sobre ella que el admin nombra (nombre de negocio obligatorio) y describe (descripción y descripciones por columna, opcionales pero recomendadas; genéricas si se omiten). Esas descripciones son lo que el experto (ADR-0005) lee. Se cierra la cadena plantilla→archivo→vista→fuente del experto sin SQL manual; la vista nueva aparece en el checklist de fuentes del experto.

2. **Cargas siguientes: comparar, no redefinir.** Si los encabezados calzan con la plantilla, se previsualiza y se guarda. Si no calzan, se ofrece **mapear** las columnas del archivo a las esperadas. El mapeo acomoda esa carga puntual (se persiste en la carga y el worker lo reaplica al derivar el Parquet); **nunca** muta el molde.

3. **Definición gobernada (dos barandales inviolables).**
   - Crear plantilla/vista o editar una vista = admin **o** uploader de la torre; nunca un consultante. Cargas rutinarias con calce = cualquier uploader. Definir o cambiar el molde es un acto gobernado.
   - Cambiar la estructura del molde es **edición explícita de admin**, con aviso de impacto a las cargas existentes y futuras — un camino separado, no un efecto colateral de cargar un archivo. Al editar el molde, la vista 1:1 se re-sincroniza conservando las descripciones de negocio existentes.

## Consecuencias
- (+) El negocio define sus reportes sin tocar código; la cadena hasta el experto queda cerrada de extremo a extremo.
- (+) Los barandales preservan la calidad: la entrada sigue validada, el molde no cambia por accidente, y el catálogo sigue gobernado.
- (+) Convive con lo sembrado: las plantillas/vistas OTC iniciales siguen funcionando y los evals OTC se mantienen ≥95%.
- (−) El mapeo se persiste por carga: si el molde cambia luego, las cargas viejas conservan su mapeo histórico (correcto para inmutabilidad, pero hay que tenerlo presente al auditar).
- (−) Inferencia de tipos no automática: el usuario confirma el tipo de cada columna (decisión deliberada — más seguro que adivinar y normalizar mal montos o fechas).
