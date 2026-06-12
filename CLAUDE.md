# Smart_Example — Sistema de Facturación Empresarial

## Descripción del proyecto

Smart_Example es un sistema empresarial de facturación electrónica para México y Centroamérica, modelado a partir del sistema SMART. Reemplaza/extiende un sistema legacy en Java con una arquitectura moderna, mantenible y multipaís.

**Estado actual:** Proyecto en fase de scaffolding inicial.

## Stack tecnológico

### Backend
- **Lenguaje:** Java 21 LTS
- **Framework:** Spring Boot 3.x
- **Build:** Maven
- **ORM:** Spring Data JPA + Hibernate
- **Mapeo DTO ↔ Entidad:** MapStruct
- **Boilerplate:** Lombok
- **Migraciones de BD:** Flyway
- **Validación:** Bean Validation (Jakarta)
- **API:** REST con OpenAPI 3 (springdoc-openapi)
- **Testing:** JUnit 5 + Mockito + Testcontainers

### Frontend
- **Framework:** Vue 3 con `<script setup>` y Composition API (NUNCA Options API)
- **UI:** Vuetify 3
- **Build:** Vite
- **Lenguaje:** TypeScript estricto
- **Cliente HTTP:** Axios
- **Estado:** Pinia
- **Router:** Vue Router 4
- **Testing:** Vitest + Vue Test Utils

### Base de datos
- **PostgreSQL 16** (NUNCA MySQL en este proyecto)
- Tipos a usar: `NUMERIC(precision,scale)` para todo monetario, `XML` para CFDI, `JSONB` para configuración flexible, `TIMESTAMPTZ` para fechas con zona horaria.

### Infraestructura
- **Contenedores:** Docker + Docker Compose para desarrollo local
- **Versión de Node:** 20 LTS
- **Versión de Java:** 21 LTS

## Estructura del monorepo

```
Smart_Example/
├── CLAUDE.md                 # Este archivo
├── README.md
├── docker-compose.yml        # PostgreSQL local
├── .gitignore
├── apps/
│   ├── backend/              # Spring Boot
│   │   ├── pom.xml
│   │   └── src/
│   │       ├── main/java/com/smart/example/
│   │       │   ├── SmartExampleApplication.java
│   │       │   ├── config/             # Beans, seguridad, CORS
│   │       │   ├── shared/             # Excepciones, base classes, utils
│   │       │   ├── mantenimiento/      # Módulo 1
│   │       │   │   ├── monedas/        # Submódulo (vertical slice)
│   │       │   │   │   ├── domain/     # Entidad, value objects, reglas
│   │       │   │   │   ├── application/# Servicios, casos de uso
│   │       │   │   │   ├── infrastructure/ # Repositorio JPA, mappers
│   │       │   │   │   └── web/        # Controller, DTOs, validación
│   │       │   │   ├── clientes/
│   │       │   │   ├── esquemas/
│   │       │   │   └── ...
│   │       │   ├── tablas_facturacion/ # Módulo 2
│   │       │   ├── calculo_porcentajes/# Módulo 3
│   │       │   ├── facturacion/        # Módulo 4
│   │       │   │   └── electronica/    # Capa multipaís
│   │       │   │       ├── port/       # FacturacionElectronicaPort (interfaz)
│   │       │   │       ├── mexico/     # CfdiMexicoAdapter
│   │       │   │       ├── guatemala/  # FelGuatemalaAdapter (futuro)
│   │       │   │       └── ...
│   │       │   ├── consulta/           # Módulo 5
│   │       │   ├── impresion/          # Módulo 6
│   │       │   ├── notas_credito/      # Módulo 7
│   │       │   ├── integrador/         # Módulo 8
│   │       │   └── cancelacion/        # Módulo 9
│   │       └── resources/
│   │           ├── application.yml
│   │           ├── application-dev.yml
│   │           └── db/migration/       # Flyway: V1__init.sql, V2__monedas.sql, ...
│   └── frontend/             # Vue 3 + Vuetify
│       ├── package.json
│       ├── vite.config.ts
│       ├── tsconfig.json
│       └── src/
│           ├── main.ts
│           ├── App.vue
│           ├── router/
│           ├── stores/             # Pinia stores
│           ├── services/           # Clientes HTTP por módulo
│           ├── types/              # Tipos TypeScript (DTOs)
│           ├── views/
│           │   ├── mantenimiento/
│           │   │   ├── monedas/
│           │   │   │   ├── MonedasListView.vue
│           │   │   │   └── MonedaFormDialog.vue
│           │   │   └── ...
│           │   └── ...
│           └── components/         # Componentes reutilizables
└── docs/
    ├── arquitectura.md
    ├── modulos.md              # Los 9 módulos y 55 submódulos
    └── facturacion_electronica.md
```

## Arquitectura

### Backend: arquitectura hexagonal por módulo

Cada submódulo sigue el patrón **ports & adapters** con 4 capas:

1. **domain/** — Entidades, value objects, reglas de negocio puras. **No depende de Spring, JPA, ni nada externo.** Java puro.
2. **application/** — Servicios y casos de uso. Orquesta el dominio. Define interfaces (puertos) hacia infraestructura.
3. **infrastructure/** — Implementaciones técnicas: repositorios JPA, llamadas a APIs externas, integraciones.
4. **web/** — Controllers REST, DTOs, validación de entrada, manejo de excepciones HTTP.

**Regla clave:** las dependencias siempre apuntan hacia adentro. `web` y `infrastructure` dependen de `application`, que depende de `domain`. Nunca al revés.

### Frontend: organización por dominio

- `views/<modulo>/<submodulo>/` — Vistas de cada submódulo.
- `services/<modulo>/<submodulo>Service.ts` — Cliente HTTP del submódulo.
- `types/<modulo>/<submodulo>.ts` — DTOs e interfaces TypeScript.
- `stores/<modulo>/<submodulo>Store.ts` — Pinia store (solo cuando hay estado compartido entre vistas).

### Facturación electrónica multipaís

**Regla inmutable:** El dominio de facturación **nunca** conoce a CFDI, FEL, ni ningún régimen específico. Todo pasa por el puerto:

```java
public interface FacturacionElectronicaPort {
    ResultadoTimbrado timbrar(FacturaDomain factura);
    ResultadoCancelacion cancelar(String uuid, MotivoCancelacion motivo);
    boolean validarIdentificadorFiscal(String rfc, Pais pais);
}
```

Cada país tiene su adapter en `facturacion/electronica/<pais>/`. La selección del adapter se hace por `Pais` del cliente/orden.

## Convenciones de código

### Java (backend)
- **Package base:** `com.smart.example`
- **Naming:** clases en `PascalCase`, métodos y variables en `camelCase`, constantes en `UPPER_SNAKE_CASE`.
- **Entidades JPA:** sufijo `Entity` (ej. `MonedaEntity`) en `infrastructure/`. Las del dominio sin sufijo (ej. `Moneda`).
- **DTOs:** sufijos `Request`, `Response`, `Dto` según contexto. En `web/dto/`.
- **Servicios:** sufijo `Service`. En `application/`.
- **Repositorios JPA:** sufijo `Repository`, interfaz que extiende `JpaRepository`. En `infrastructure/`.
- **Casos de uso complejos:** sufijo `UseCase` (ej. `TimbrarFacturaUseCase`).
- **Excepciones de negocio:** extender `BusinessException` en `shared/exception/`.
- **NUNCA usar `double` o `float` para dinero.** SIEMPRE `BigDecimal`.
- **Todas las fechas son `OffsetDateTime` o `LocalDate`.** Nunca `Date` (legacy).
- **Lombok permitido:** `@Getter`, `@Setter`, `@Builder`, `@RequiredArgsConstructor`. Evitar `@Data` (genera `equals/hashCode` peligrosos en entidades).

### TypeScript / Vue (frontend)
- **TypeScript estricto.** `strict: true` en `tsconfig.json`. Prohibido `any` salvo justificación documentada.
- **Componentes Vue:** un solo `<script setup lang="ts">` por archivo.
- **Composables:** prefijo `use` (ej. `useMonedas()`), en `composables/`.
- **Nombres de archivos Vue:** `PascalCase.vue`.
- **Props con tipos explícitos:** `defineProps<{ ... }>()`, no la sintaxis con runtime.
- **Emits tipados:** `defineEmits<{ ... }>()`.
- **Async/await siempre,** no `.then()`.

### SQL / Migraciones Flyway
- **Nombres:** `V<num>__<descripcion_snake_case>.sql` (ej. `V2__crear_tabla_monedas.sql`).
- **Tablas en `snake_case` plural** (ej. `monedas`, `clientes`, `facturas`).
- **Columnas en `snake_case`** (ej. `fecha_creacion`, `monto_total`).
- **Toda tabla tiene:** `id BIGSERIAL PRIMARY KEY`, `fecha_creacion TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `fecha_actualizacion TIMESTAMPTZ`, `usuario_creacion VARCHAR(100)`, `usuario_actualizacion VARCHAR(100)`.
- **Soft delete cuando aplica:** columna `activo BOOLEAN NOT NULL DEFAULT TRUE`.
- **Toda FK con `ON DELETE` explícito.**
- **NO drop ni rename destructivos en migraciones.** Siempre aditivos. Si necesitas eliminar, usa una nueva migración que marque deprecado.

## API REST — convenciones

- **Base path:** `/api/v1/`
- **Recursos en plural:** `/api/v1/monedas`, `/api/v1/clientes`
- **Verbos HTTP estándar:** GET (listar/obtener), POST (crear), PUT (reemplazar), PATCH (actualizar parcial), DELETE (eliminar o desactivar).
- **Paginación:** parámetros `?page=0&size=20&sort=campo,asc`. Respuesta envuelta en `Page<T>`.
- **Filtros:** query params con nombres explícitos (`?codigo=USD&activo=true`).
- **Errores:** formato uniforme con `timestamp`, `status`, `error`, `message`, `path`, `validationErrors[]`.
- **Códigos HTTP correctos:** 200 OK, 201 Created (con header `Location`), 204 No Content, 400 Bad Request, 404 Not Found, 409 Conflict, 422 Unprocessable Entity.

## Glosario del dominio

Términos del negocio que aparecen en módulos y submódulos:

- **CFDI:** Comprobante Fiscal Digital por Internet (México). XML firmado y timbrado por un PAC.
- **PAC:** Proveedor Autorizado de Certificación (México).
- **SAT:** Servicio de Administración Tributaria (México).
- **Addenda:** Información adicional XML que ciertos clientes (Walmart, Liverpool, etc.) requieren dentro del CFDI.
- **FEL:** Factura Electrónica en Línea (Guatemala).
- **Iguala:** Contrato de servicios profesionales con tarifa fija mensual (típicamente legales/contables/staffing). Genera facturación recurrente.
- **Factor Iguala:** Multiplicador aplicado al cálculo de iguala.
- **Riesgos de Trabajo:** Concepto de nómina relacionado al seguro de riesgos laborales.
- **Conceptos de Nómina:** Componentes facturables que vienen del sistema de payroll (sueldo, prestaciones, comisiones).
- **Esquema de Facturación:** Plantilla/configuración de cómo se factura a un cliente específico.
- **Orden:** Orden de servicio. Unidad central de facturación.
- **Serie de Facturación:** Numeración consecutiva de facturas (ej. Serie A, Serie B).
- **Bóveda:** Repositorio documental donde se archivan CFDIs emitidos (legalmente obligatorio en MX, 5 años mínimo).
- **Freelancer:** Profesional independiente facturado vía honorarios.

## Comandos comunes

### Backend
```bash
cd apps/backend
./mvnw spring-boot:run                  # Iniciar en modo dev
./mvnw test                             # Correr tests
./mvnw clean package                    # Build
./mvnw flyway:migrate                   # Aplicar migraciones manualmente
```

### Frontend
```bash
cd apps/frontend
npm install                             # Instalar dependencias
npm run dev                             # Servidor de desarrollo
npm run build                           # Build de producción
npm run test                            # Tests
npm run lint                            # ESLint
npm run type-check                      # Validación TypeScript
```

### Infraestructura
```bash
docker compose up -d postgres           # Levantar PostgreSQL local
docker compose down                     # Detener todo
docker compose logs -f postgres         # Ver logs de BD
```

## Reglas explícitas para Claude Code

1. **Antes de generar código de un submódulo nuevo, leer este `CLAUDE.md` completo.**
2. **Siempre seguir la arquitectura hexagonal en backend.** No tomar atajos poniendo lógica de negocio en controllers o repositorios.
3. **Nunca usar `double`/`float` para montos.** Es un error inmediato.
4. **Nunca acoplar el dominio de facturación a CFDI/SAT.** Todo pasa por `FacturacionElectronicaPort`.
5. **Migraciones Flyway aditivas.** Nunca `DROP` ni `RENAME` destructivos.
6. **Tests:** todo servicio con lógica de negocio debe tener test unitario. Controllers con `@WebMvcTest`. Repositorios con `@DataJpaTest` o Testcontainers.
7. **Antes de crear un componente Vue, verificar si ya existe uno reutilizable en `components/`.**
8. **Validación doble:** Bean Validation en backend (`@Valid`) Y validación de formulario en frontend (Vuetify rules). No confiar solo en una.
9. **Si una decisión arquitectónica no está clara en este archivo, preguntar antes de improvisar.**
10. **Al terminar un submódulo, actualizar la sección "Estado del proyecto" abajo.**

## Estado del proyecto

### Submódulos completados
- *(ninguno aún)*

### Submódulo en construcción
- *(definir tras scaffolding)*

### Módulos pendientes
- [ ] 1. Mantenimiento (6 submódulos)
- [ ] 2. Tablas de Facturación (10 submódulos)
- [ ] 3. Cálculo de Porcentajes de Factura (6 submódulos)
- [ ] 4. Facturación (11 submódulos)
- [ ] 5. Consulta (3 submódulos)
- [ ] 6. Impresión y reenvíos a Bóveda (3 submódulos)
- [ ] 7. Notas de Crédito (4 submódulos)
- [ ] 8. Integrador de Factura (11 submódulos)
- [ ] 9. Cancelación CFDIs (1 submódulo)
