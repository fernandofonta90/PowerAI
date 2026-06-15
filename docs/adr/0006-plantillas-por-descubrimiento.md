# ADR-0006: Plantillas y vistas por descubrimiento, con definición gobernada

**Estado:** Aceptada · **Fecha:** 2026-06-14

## Contexto
Hasta M10 las plantillas (esquema esperado de cada reporte) y sus vistas curadas del catálogo se sembraban desde supuestos en código. Eso no escala a 6 torres × 15 países, donde quien conoce cada reporte es el negocio, no el desarrollador. Se necesita que las plantillas y vistas sean definibles por quien carga los datos, sin que ello debilite la disciplina de entrada ni el gobierno del catálogo (ADR-0003).

## Decisión
La estructura se descubre desde la primera carga y se gobierna:

1. **Descubrimiento.** Al subir un archivo de un tipo aún inexistente en la torre, el sistema lee los encabezados (sin procesar) y los muestra. El usuario confirma el mapeo (nombre de negocio + tipo: texto/entero/decimal/fecha) e indica las llaves de país y periodo. Nace la plantilla y, automáticamente, una **vista 1:1** sobre ella que el admin nombra (nombre de negocio obligatorio) y describe (descripción y descripciones por columna, opcionales pero recomendadas; genéricas si se omiten). Esas descripciones son lo que el experto (ADR-0005) lee. Se cierra la cadena plantilla→archivo→vista→fuente del experto sin SQL manual; la vista nueva aparece en el checklist de fuentes del experto.

2. **Cargas siguientes: comparar, no redefinir.** Si los encabezados calzan con la plantilla, se previsualiza y se guarda. Si no calzan, se ofrece **mapear** las columnas del archivo a las esperadas. El mapeo acomoda esa carga puntual (se persiste en la carga y el worker lo reaplica al derivar el Parquet); **nunca** muta el molde.

3. **Definición gobernada (dos barandales inviolables).**
   - **Crear** plantilla + su vista 1:1 = admin **o** uploader de la torre (es parte del flujo de carga); nunca un consultante. Cargas rutinarias con calce = cualquier uploader.
   - **Editar lo establecido = solo admin.** Cambiar la estructura del molde y editar la vista (su nombre de negocio y las descripciones de columna que el experto lee para decidir qué consultar) son igual de sensibles: ambos requieren rol admin de la torre. La edición del molde lleva aviso de impacto a las cargas existentes y futuras — un camino separado, no un efecto colateral de cargar un archivo. Al editar el molde, la vista 1:1 se re-sincroniza conservando las descripciones de negocio existentes.

## Consecuencias
- (+) El negocio define sus reportes sin tocar código; la cadena hasta el experto queda cerrada de extremo a extremo.
- (+) Los barandales preservan la calidad: la entrada sigue validada, el molde no cambia por accidente, y el catálogo sigue gobernado.
- (+) Convive con lo sembrado: las plantillas/vistas OTC iniciales siguen funcionando y los evals OTC se mantienen ≥95%.
- (−) El mapeo se persiste por carga: si el molde cambia luego, las cargas viejas conservan su mapeo histórico (correcto para inmutabilidad, pero hay que tenerlo presente al auditar).

## Adenda (M12)
- **Inferencia de tipos:** al inspeccionar se analiza una muestra y se **sugiere** el tipo de cada columna (fecha/decimal/entero/texto; los identificadores numéricos van a texto). Sigue siendo el humano quien confirma: la inferencia pre-selecciona, no impone.
- **Periodo opcional:** muchos reportes no traen columna de periodo. `columna_periodo` pasa a opcional; si no hay columna, el periodo se declara al cargar y aplica a todo el archivo, manteniendo el versionado (una carga = un periodo). El país no cambia: sigue como hasta ahora (no se generaliza la partición; p. ej. PTP no segmenta por país).

## Adenda (M16) — columnas opcionales + fechas tolerantes
- **Columnas opcionales por defecto:** al crear una plantilla, las columnas son opcionales (las celdas vacías entran como NULL, no rechazan). La **excepción** son las llaves: si país/periodo se eligen como columna, esa columna es requerida (la llave que particiona no puede faltar). La UI de creación trae un toggle "requerida" por columna, desmarcado por defecto; antes marcaba todo obligatorio y los reportes reales (con columnas vacías) eran rechazados.
- **Fechas ambiguas degradan a texto, no rechazan:** si una columna marcada "fecha" trae valores que la heurística (M15) no puede resolver (ambiguos o mezclados), la carga **degrada esa columna a texto y avisa**, en vez de rechazar. No corrompe (no adivina el orden) y el usuario puede editar el tipo luego. La vista 1:1 es agnóstica del tipo, así que no se regenera.

## Adenda (M15) — país opcional + fechas de reportes reales
- **País opcional por columna:** como el periodo (M12), la columna de país pasa a opcional. Si no se elige columna, el país declarado al cargar se registra como metadato de toda la carga y **no** se verifica contra el contenido (encaja con torres que no segmentan por país, p. ej. PTP, donde el país es implícito en "PE001"/"Manpower Perú"). La UI por defecto NO autoselecciona columna de país (antes tomaba la primera y causaba un rechazo espurio). El RBAC no cambia: un país declarado fluye limpio para usuarios con países='*'.
- **Fechas por formato detectado por columna** (heurística, en `app/ingesta/fechas.py`): todas ISO → `iso`; con separador `/`/`-` y año de 4 dígitos: si algún PRIMER campo > 12 → `dmy` (DD/MM); si algún SEGUNDO campo > 12 → `mdy` (MM/DD); ambas señales → conflicto (ambiguo); ninguna (todos ≤ 12) → genuinamente ambiguo; mezcla de formas → ambiguo. Una columna ambigua **no se adivina**: se reporta como error claro y, en inferencia, se sugiere texto, en vez de corromper la fecha.

## Adenda (M14) — auto-slug de encabezados
Los reportes reales traen encabezados con mayúsculas, acentos, espacios y símbolos ("Número Documento", "Importe S/", "RUC"), que no son identificadores SQL válidos. En vez de exigir que el archivo venga en snake_case, el sistema **genera automáticamente el nombre técnico** (slug) de cada columna desde su encabezado y **conserva el encabezado original como etiqueta de negocio** (`ColumnaSpec.etiqueta`). El `nombre` (slug) es interno (DuckDB/Parquet/vistas); la `etiqueta` es lo que el usuario ve y por lo que se valida y mapea la carga. Las colisiones de slug se desambiguan con sufijo numérico y se avisan. Las plantillas/vistas en snake_case sembradas no cambian (su etiqueta == nombre).
