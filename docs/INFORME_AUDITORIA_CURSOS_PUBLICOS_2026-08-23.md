# Informe de auditoría forense — Cursos públicos

**Fecha:** 2026-08-23  
**Alcance:** `/cursos`, `/cursos/[id]`, API pública de cursos, inscripción pública y contratos Academy relacionados.  
**Metodología:** Octógono Forense CCF: Frontend, Backend, Base de Datos, Integración, Seguridad, Trazabilidad, Resiliencia y Rendimiento.

## Dictamen ejecutivo

**VICTORY REJECTED — el catálogo público no está listo para declararse conforme.**

Se encontraron fallos de severidad alta en el contrato de visibilidad pública, la protección de cursos avanzados, la inscripción anónima y la correspondencia entre la respuesta API y el frontend.

## Tabla de estados

| Dimensión | Estado | Severidad | Resumen |
|---|---:|---:|---|
| Frontend | 🔴 | Alta | El frontend espera `description`, pero la API pública entrega `desc`; además, el error de API se presenta como catálogo vacío. |
| Backend | 🔴 | Crítica | Detalle e inscripción reutilizan una búsqueda que no filtra `access_level`. |
| Base de datos | 🟡 | Media | Existen índices relevantes, pero el catálogo público no aplica aislamiento por `sede_id`. |
| Integración | 🔴 | Alta | El contrato API–TypeScript no está alineado: falta `slug` explícito y hay nombres de campos distintos. |
| Seguridad | 🔴 | Alta | Un curso `advanced` puede consultarse o recibir inscripciones con slug, código o UUID; la inscripción pública no tiene rate limit específico. |
| Trazabilidad | 🟡 | Media | La ruta pública crea o reactiva perfiles e inscripciones sin una estrategia suficiente de antiabuso y seguimiento técnico. |
| Resiliencia | 🔴 | Alta | No existe un estado de error recuperable en el listado público. |
| Rendimiento | 🟡 | Media | El conteo de lecciones está agrupado, pero el listado usa `.all()` sin paginación. |

## Hallazgos detallados

### CURSOS-001 — El detalle público expone cursos no destinados a captación

**Severidad:** Crítica  
**Dimensiones:** Backend, Seguridad, Integración

`public_list_courses()` filtra correctamente `access_level` a `open` y `persona`, pero `_find_public_course()` solo valida slug/código/UUID, publicación y borrado lógico.

Evidencia:

- [backend/api/public.py:242-248](/root/ccf/backend/api/public.py:242) filtra el listado.
- [backend/api/public.py:273-292](/root/ccf/backend/api/public.py:273) no filtra `access_level`.
- [backend/api/public.py:295-302](/root/ccf/backend/api/public.py:295) usa esa búsqueda para el detalle.
- [backend/api/public.py:315-324](/root/ccf/backend/api/public.py:315) reutiliza la misma búsqueda para inscribir.

**Riesgo:** un curso `advanced` puede aparecer si alguien conoce su identificador y puede recibir una inscripción pública.

**Corrección requerida:** crear una búsqueda pública explícita que exija `access_level IN ('open', 'persona')` y reutilizarla en detalle e inscripción.

### CURSOS-002 — Contrato de campos desalineado entre API y frontend

**Severidad:** Alta  
**Dimensión:** Integración

La respuesta `PublicCursoResponse` entrega `desc`, `imageUrl`, `instructor` e `id`, mientras el listado TypeScript utiliza parcialmente `description`, `imageUrl`, `instructor` y un `slug` opcional que la API no devuelve.

Evidencia:

- [backend/api/public.py:199-224](/root/ccf/backend/api/public.py:199) define el contrato público.
- [backend/api/public.py:209-220](/root/ccf/backend/api/public.py:209) serializa la descripción como `desc`.
- [frontend/src/app/(public)/cursos/page.tsx:13-20](</root/ccf/frontend/src/app/(public)/cursos/page.tsx:13>) define el tipo extendido.
- [frontend/src/app/(public)/cursos/page.tsx:149](</root/ccf/frontend/src/app/(public)/cursos/page.tsx:149>) renderiza `featured.description`.
- [frontend/src/app/(public)/cursos/page.tsx:176](</root/ccf/frontend/src/app/(public)/cursos/page.tsx:176>) usa `course.description` en las tarjetas.

**Riesgo:** las tarjetas pueden mostrar el título como sustituto de la descripción y el estado de navegación puede depender accidentalmente de que `id` sea un slug.

**Corrección requerida:** escoger un contrato canónico. Recomendación: devolver `slug`, `description`, `image_url` e `instructor_name` con nombres consistentes, o adaptar explícitamente el frontend a la respuesta pública actual mediante un mapper probado.

### CURSOS-003 — El listado no diferencia error de API y catálogo vacío

**Severidad:** Alta  
**Dimensiones:** Frontend, Resiliencia

Ante un error de red o backend, la página vacía `courses` y muestra el estado de catálogo vacío.

Evidencia:

- [frontend/src/app/(public)/cursos/page.tsx:54-68](</root/ccf/frontend/src/app/(public)/cursos/page.tsx:54>) captura el error y establece `courses` como arreglo vacío.
- [frontend/src/app/(public)/cursos/page.tsx:183-187](</root/ccf/frontend/src/app/(public)/cursos/page.tsx:183>) presenta el estado vacío.

**Riesgo:** el visitante cree que no existen cursos cuando en realidad la plataforma está fallando.

**Corrección requerida:** separar `loading`, `error` y `empty`, incluir mensaje de error y botón de reintento.

### CURSOS-004 — Inscripción pública sin control antiabuso específico

**Severidad:** Alta  
**Dimensiones:** Seguridad, Trazabilidad, Resiliencia

La ruta pública de inscripción acepta todos los campos como opcionales y no tiene un limitador específico en el decorador del endpoint.

Evidencia:

- [backend/api/public.py:305-312](/root/ccf/backend/api/public.py:305) declara campos opcionales.
- [backend/api/public.py:315-352](/root/ccf/backend/api/public.py:315) crea o reactiva persona e inscripción.
- En contraste, otras rutas públicas del mismo módulo sí usan `rate_limiter`.

**Riesgo:** creación de registros basura, reactivaciones masivas y contaminación de métricas de Academy.

**Corrección requerida:** exigir nombre y al menos un canal de contacto válido, aplicar rate limit por IP/identidad y registrar request/campaign de forma trazable.

### CURSOS-005 — Catálogo global sin criterio explícito de sede o sitio

**Severidad:** Media  
**Dimensiones:** Base de Datos, Seguridad, Arquitectura

`public_list_courses()` consulta todos los cursos publicados con nivel de acceso público sin filtrar `sede_id` ni recibir `site_key`.

Evidencia:

- [backend/api/public.py:228-250](/root/ccf/backend/api/public.py:228) consulta directamente `Course`.
- [backend/models_academy_core.py:25-29](/root/ccf/backend/models_academy_core.py:25) define `sede_id` como relación opcional.

**Riesgo:** una futura sede puede exponer cursos de otra sede en `/cursos`.

**Corrección requerida:** definir formalmente si el catálogo es global. Si no lo es, recibir `site_key` o resolver el sitio canónico y aplicar `sede_id`; si sí lo es, documentar la excepción como catálogo global.

### CURSOS-006 — Listado sin paginación

**Severidad:** Media  
**Dimensión:** Rendimiento

El endpoint usa `.all()` para cargar todos los cursos publicados.

Evidencia:

- [backend/api/public.py:242-250](/root/ccf/backend/api/public.py:242).

**Riesgo:** crecimiento lineal de memoria y tiempo de respuesta.

**Corrección requerida:** agregar `skip/limit` o paginación basada en cursor y mantener el conteo de lecciones agrupado.

### CURSOS-007 — Drawer de inscripción sin semántica completa de accesibilidad

**Severidad:** Media  
**Dimensiones:** Frontend, Accesibilidad, Resiliencia

El flujo visual es un panel lateral, pero se maneja con el estado `showEnrollModal`, no declara `role="dialog"`, `aria-modal`, etiqueta accesible ni gestión de foco.

Evidencia:

- [frontend/src/app/(public)/cursos/[id]/page.tsx:29-38](</root/ccf/frontend/src/app/(public)/cursos/[id]/page.tsx:29>).
- [frontend/src/app/(public)/cursos/[id]/page.tsx:297-319](</root/ccf/frontend/src/app/(public)/cursos/[id]/page.tsx:297>).

**Corrección requerida:** convertirlo en drawer accesible con foco inicial, retorno de foco, cierre con Escape, `aria-labelledby` y bloqueo controlado del scroll.

## Validaciones ejecutadas

- `./venv/bin/python -m pytest tests/test_public_100pct_coverage.py -q -o addopts=''` → **9 passed**.
- ESLint sobre las páginas públicas de cursos → **pasó**.
- `npx tsc --noEmit` → **pasó**.
- Contrato de rama revisado → **pasó**.
- La verificación HTTP directa del dominio público no pudo completarse en esta sesión porque el DNS no resolvió `ministerioselfaro.org`.

## Orden recomendado de corrección

1. Bloquear `advanced` y cualquier nivel no público en detalle e inscripción.
2. Alinear el contrato API–TypeScript y agregar pruebas de contrato.
3. Añadir rate limit, validación mínima y trazabilidad a la inscripción pública.
4. Separar estados `error` y `empty` en `/cursos`.
5. Resolver formalmente el alcance por sede/sitio.
6. Añadir paginación y completar la accesibilidad del drawer.
7. Repetir el Octógono Forense y ejecutar un Victory Audit independiente.

## Estado de cambios

Este informe es únicamente de auditoría. No se modificó código de la aplicación como resultado de esta revisión. El informe quedó registrado en el commit `1222ddc8`; todavía no se ha hecho push.
