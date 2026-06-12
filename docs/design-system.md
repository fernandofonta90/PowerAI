# Design System — PowerAI (v2)

> **Vinculante para todo lo que se construya en `web/`.** Si una implementación requiere desviarse, se discute y se actualiza este documento primero — no se improvisa en el código.
>
> **v2:** PowerAI adopta el design language de **AI.Q Powered by Sophie**, la familia de herramientas de IA de ManpowerGroup, para integrarse visualmente al ecosistema corporativo de IA. Referencias: pantallas de AI.Q home, SOPHIE Spark landing y Spark Chat.

## Principios de diseño

1. **Miembro de la familia AI.Q.** PowerAI habla el mismo idioma visual que Sophie (Stack, Spend, Spark): morado corporativo, sparkle como símbolo de IA, tipografía y patrones de layout consistentes. Un usuario que conoce Spark reconoce PowerAI de inmediato.
2. **La pregunta al centro.** Pantalla de bienvenida centrada con preguntas sugeridas como tarjetas (patrón Spark) e input inferior persistente. El home invita a escribir, no a navegar menús.
3. **Transparencia como layout.** Donde Spark ofrece un link "What Data Does Spark Use?", PowerAI lo lleva más lejos: las fuentes activas, su frescura y la citación de cada respuesta son elementos permanentes de la interfaz.
4. **Densidad sin ruido en los datos.** Tablas densas, números tabulares, jerarquía sobria. La calidez del estilo Sophie (banda crema, curvas) vive en los marcos; la zona de datos es limpia y funcional.
5. **El color comunica estado.** Verde/ámbar/rojo exclusivamente para semántica (frescura, severidad, vencimientos). El morado es marca e interacción; nunca estado.

## Tokens

### Paleta (familia AI.Q)

| Token | Hex | Uso |
|---|---|---|
| `brand-900` | `#352C78` | Hover de elementos morado oscuro, texto sobre fondos morado claro |
| `brand-800` | `#453A96` | Bloque izquierdo del header, footer, links de marca, sidebar activo |
| `brand-600` | `#5B51C8` | Banda derecha del header, botones primarios, botón de envío, sparkle |
| `brand-200` | `#C9C5EC` | Bordes de acento, indicadores de chat activo, texto secundario sobre morado |
| `brand-100` | `#EFEDFB` | Tiles de iconos, fondos de selección, burbuja del usuario en chat |
| `brand-50` | `#F6F5FD` | Fondos sutiles (bloque de citación de fuentes) |
| `cream-100` | `#FBF2E7` | Banda hero del home y páginas de aterrizaje (patrón Spark) |
| `surface-200` | `#ECEDF4` | Fondo del sidebar |
| `surface-100` | `#F4F5FA` | Fondo general de la aplicación |
| `neutral-900` | `#2A2A3C` | Texto de máximo contraste, títulos |
| `neutral-700` | `#3A3A50` | Texto de cuerpo |
| `neutral-500` | `#6B6B80` | Texto secundario, subtítulos |
| `neutral-400` | `#8A8AA0` | Placeholders, hints, iconos inactivos |
| `neutral-200` | `#DDDFE9` | Bordes de inputs y paneles |
| `neutral-100` | `#E2E4EE` | Bordes de tarjetas y separadores |
| `success-700` / `success-600` | `#27500A` / `#3B6D11` | Frescura al día, estados correctos |
| `warning-700` / `warning-600` | `#633806` / `#854F0B` | Frescura en advertencia, vencimientos medios |
| `danger-700` / `danger-600` | `#791F1F` / `#A32D2D` | Datos críticos: alta morosidad, cargas muy vencidas, alertas |

Reglas: texto sobre fondo de color usa el stop oscuro de la misma familia. Los semánticos (verde/ámbar/rojo) nunca se usan decorativamente. En tablas de datos, el texto principal usa `neutral-900`/`neutral-700` — el morado se reserva para interacción, no para datos.

### Marca e iconografía

- **Nombre:** POWER**AI** — prefijo peso 400/500, sufijo peso 600 (patrón tipográfico de la familia SOPHIE Stack/Spend/Spark).
- **Símbolo de IA:** sparkle de cuatro puntas (estilo Sophie/Spark), en `brand-600`. Marca el avatar del asistente, los badges de contenido generado y el icono del producto. (Sustituye al teal de v1.)
- **Iconos de interfaz:** Lucide outline. Tiles de icono: cuadrado redondeado 12px en `brand-100` con icono `brand-800` (patrón de las tarjetas de producto AI.Q).
- **Header en dos tonos:** bloque izquierdo `brand-800` con "AI.Q Powered by Sophie" (sujeto a aprobación de uso de la marca — ver nota al final), banda derecha `brand-600` con POWERAI, badge de torre/países y avatar.
- **Footer:** banda `brand-800` con patrón de puntos en `brand-200` baja opacidad, logo ManpowerGroup a la izquierda, copyright a la derecha. Durante el piloto incluye etiqueta central "PROTOTYPE"/"PILOTO" (patrón AI.Q).

### Tipografía

- **Familia:** Inter (self-hosted en `web/public/fonts/`).
- **Números:** `font-variant-numeric: tabular-nums` obligatorio en celdas numéricas, KPIs y montos. Montos a la derecha.
- **Escala:** 24px título de bienvenida · 19px títulos de página · 15px subtítulos · 13px cuerpo · 11–12px metadata. Nada por debajo de 10.5px.
- **Pesos:** 400, 500 y 600 (el 600 exclusivamente para el sufijo de marca y botones primarios).
- **Subtítulos de producto en itálica** (patrón Spark: "Agent orchestrated Labor Market Analytics" → "Inteligencia analítica del SSC Finanzas LATAM").

### Espaciado y forma

- Radios: 14px input principal de chat, 12px tarjetas y tiles, 10px tarjetas de pregunta sugerida, 99px pills y botón de envío.
- Bordes 0.5–1px en `neutral-100`/`neutral-200`. Sombras muy sutiles solo en tarjetas de pregunta sugerida y el input flotante (patrón Spark); en la zona de datos, sin sombras.
- **Curva de transición:** la banda crema del hero termina en curva convexa suave hacia la superficie (SVG path, patrón Spark landing).
- Espaciado en escala de 4. Modo claro como principal; tokens como variables CSS para habilitar dark mode después sin refactor.

## Componentes base

- **Stack:** Tailwind CSS con estos tokens en `tailwind.config.ts` + shadcn/ui (componentes copiados al repo y ajustados a tokens).
- **Tarjeta de pregunta sugerida:** blanca, borde `neutral-100`, radio 10px, texto 12–13px centrado, sombra sutil. Grid de 2–3 centrado bajo el título de bienvenida. Alimentadas por torre desde el banco de preguntas doradas. Clic = enviar la pregunta.
- **Input principal de chat:** contenedor blanco flotante radio 14px con placeholder "Pregúntame lo que quieras", fila de acciones (adjuntar, feedback), acceso a "Fuentes activas" (`brand-800`, equivalente al "Data Dictionary" de Spark) y botón circular de envío en `brand-600`.
- **Sidebar de conversaciones:** fondo `surface-200`, "Nueva conversación" y "Buscar chats" arriba, historial agrupado por antigüedad, ítem activo con borde izquierdo `brand-200`. Colapsable.
- **Tablas de datos:** filas alternas `surface-100`, encabezado 12px `neutral-500`, celdas 12–13px, montos a la derecha con tabular-nums, días vencidos coloreados por severidad (verde <30, ámbar 30–60, rojo >60 — configurable por plantilla).
- **Badge de frescura:** único y reutilizado (panel de fuentes, home, respuestas). Estados: al día (verde, check), advertencia (ámbar, triángulo), vencido (rojo). Umbral definido por la frecuencia esperada de cada plantilla.
- **Bloque de citación:** al pie de cada respuesta de IA, fondo `brand-50`, 11px: archivos fuente con versión y responsable + nota de SQL en auditoría. Nunca omitible.
- **Burbuja de chat:** usuario a la derecha en `brand-100`; asistente a la izquierda sin burbuja, con avatar sparkle `brand-600`.

## Layout de la aplicación

- **Header (dos tonos):** permanente en toda la app. Bloque izquierdo `brand-800` con PowerAI, banda derecha `brand-600` con subtítulo "SSC Finanzas LATAM", badge de torre activa, países visibles y avatar. La torre y países del usuario siempre a la vista.
- **Conversación activa:** zona central con el hilo + panel de fuentes activas como rail derecho (240px) con badges de frescura y el alcance ("Filtrado: MX · CO · AR"). Sidebar de conversaciones a la izquierda (colapsable).
- **Banda crema con curva (patrón Spark):** reservada para páginas de aterrizaje/presentación del producto, no para las pantallas operativas del día a día.

## Home (spec canónica — layout aprobado)

Estructura en dos bloques verticales sobre fondo blanco:

**1. Hero de pregunta (centrado):**
- Saludo "Buenos días, {nombre}" (17px, peso 500) con sparkle `brand-600` + línea de contexto "Pregunta sobre la información de tu torre" (12.5px, `neutral-500`).
- Campo de pregunta (máx. 480px centrado): borde `brand-200`, radio 12px, sombra sutil violeta (`rgba(69,58,150,0.08)`), sparkle `brand-600` a la izquierda, placeholder, botón circular de envío `brand-600` a la derecha. Enter o clic navega al chat con la pregunta enviada.
- Debajo, 3–4 chips de preguntas sugeridas por torre (pill, fondo `brand-50`, borde `brand-200`, texto `brand-800`, 11px), alimentadas desde el banco de preguntas doradas. Clic = enviar.

**2. Grid de contexto (3 tarjetas iguales, borde `neutral-100`, radio 12px):**
- **Fuentes de mi torre:** lista de plantillas con frescura a la derecha (verde/ámbar/rojo con icono). Acción "Cargar" en el encabezado si el usuario tiene rol uploader.
- **Mis dashboards:** label con sparkle `brand-600` (contenido generado por IA). Cada ítem: tile 24px `brand-100` con icono `brand-800` + nombre + "datos de {fecha}". Link "Ver todos →" en `brand-800`. Fase 1: estado vacío "disponible próximamente".
- **Alertas recientes:** ítems con icono de severidad (rojo/ámbar) + texto 11px. Fase 1: estado vacío equivalente.

**Regla del sparkle:** el sparkle marca presencia de IA, nunca decora. Aparece en: saludo de bienvenida, campo de pregunta, avatar del asistente, y labels de contenido generado por IA (dashboards). No aparece en: fuentes, alertas, tablas de datos ni navegación. Si todo brilla, nada brilla.

Reglas del home:
- El grid de 3 tarjetas existe desde Fase 1 aunque dos estén en estado vacío — el layout no se reacomoda al llegar Fase 2.
- Responsive: bajo 900px el grid pasa a 1 columna; el hero mantiene el campo a ancho completo.
- El home es por torre: todo su contenido respeta el RBAC torre × país del usuario autenticado.

## Accesibilidad

- Contraste AA en todo texto (verificado para los tokens listados; validar variantes nuevas).
- El color nunca es único portador de significado: cada estado lleva icono.
- Navegación completa por teclado; focus ring `brand-600`.
- `aria-label` en iconos interactivos; tablas con `<th>` correctos.

---

**Nota de gobernanza de marca:** el uso del header "AI.Q Powered by Sophie" y la incorporación formal de PowerAI a esa familia requieren validación con el equipo global propietario de la marca AI.Q/Sophie. Mientras se confirma, la alternativa segura es el mismo layout de dos tonos con "ManpowerGroup" en el bloque izquierdo y POWERAI a la derecha — visualmente consistente sin usar la marca antes de la aprobación.
