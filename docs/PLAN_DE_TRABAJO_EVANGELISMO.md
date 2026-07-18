# Plan de Trabajo — Evangelismo

> **Origen:** auditoría forense del 2026-07-17
> **Documento base:** [AUDITORIA_FORENSE_EVANGELISMO_2026-07-17.md](/root/ccf/docs/AUDITORIA_FORENSE_EVANGELISMO_2026-07-17.md)
> **Propósito:** convertir hallazgos en un orden de ejecución realista para una nueva sesión de trabajo.

## Plan maestro hacia certificación 100%

Este bloque reemplaza la ejecución ad hoc. Cada cambio futuro debe pertenecer a
una fase, tener una prueba de salida y dejar el módulo más simple de mantener.
No se declara “100%” hasta completar la fase 6.

| Fase | Objetivo | Estado | Salida obligatoria |
|---|---|---|---|
| 0. Línea base | Congelar contratos, inventario y gates reproducibles. | Cerrada | Plan, matriz RBAC, contratos y QA sin contradicciones. |
| 1. Seguridad de dominio | Garantizar sede, soft delete, UUID y RBAC canónico en todas las superficies. | Cerrada | Matriz backend por rol y dos sedes; cero accesos cruzados. |
| 2. Contratos y servicios | Una fuente de verdad por recurso, schema y resolver; aliases compatibles. | Cerrada | DTOs/Pydantic y helpers compartidos sin consultas de alcance duplicadas. |
| 3. Frontend por capacidades | Pantallas compuestas de hooks/paneles tipados; UI no solicita ni muestra acciones no autorizadas. | Cerrada | Sin `any` en bordes API críticos, AbortController y E2E por capacidad. |
| 4. Flujos de negocio | Estrategia → grupo → sesión → asistencia → seguimiento → CRM; eventos y scanner completos. | Cerrada | Pruebas de flujo reales, idempotencia y errores de negocio controlados. |
| 5. Calidad operativa | Gates deterministas, observabilidad y regresiones de contratos. | Cerrada | Backend amplio, typecheck, E2E profundo y pruebas de rol/sede en verde. |
| 6. Certificación | Validación integrada, documentación final, commit limpio y despliegue reversible. | Cerrada | Evidencia fechada, commit atómico y handoff reversible; módulo certificado internamente. |

### Ejecución autónoma — 2026-07-18

- Fase 0 cerrada: el estado, los contratos, la matriz RBAC y el checklist ya
  declaran la certificación como pendiente de evidencia, no como un hecho.
- Fase 1 cerrada: regresiones por capacidad y dos sedes cubren Eventos,
  Estrategias, Grupos, Sesiones, Scanner y Analytics; los hallazgos `008` a
  `010` quedaron corregidos.
- Fase 2 cerrada: `get_visible_strategy()`, `get_visible_group()` y
  `get_visible_session()` concentran alcance de sede y soft delete en los
  recursos críticos; aliases existentes permanecen compatibles.
- Fase 3 cerrada: no quedan `any` explícitos en las pantallas/componentes de
  Evangelismo; Eventos, Grupos, Multiplicación y el reporte de sesión usan
  contratos tipados y cancelación de requests en sus fronteras críticas.
- Fases 4 y 5 cerradas: las regresiones de flujo, backend profundo/expandido,
  typecheck y E2E administrado se ejecutaron sobre el árbol consolidado.
- Fase 6 cerrada: validación final de backend profundo, typecheck, Playwright
  profundo y `git diff --check`; el cierre se entrega como commit atómico de
  Evangelismo. El despliegue productivo sigue su pipeline normal y reversible.

### Secuencia de trabajo

1. **Cerrar fase 0:** reconciliar `ESTADO_EVANGELISMO.md` con este plan; eliminar el texto que certifica 100% de forma anticipada.
2. **Cerrar fase 1:** completar matriz por rol (`read`, `edit`, `manage`, contextual) para estrategias, grupos, sesiones, asistencia, eventos, scanner, reportes y analytics; incluir dos sedes.
3. **Ejecutar fase 2 por vertical:** primero Eventos, luego Estrategias/Grupos, después Sesiones/Asistencia. En cada vertical: modelo → schema → CRUD/servicio → router → contrato → test.
4. **Ejecutar fase 3 por pantalla:** extraer hooks y paneles de Estrategias, Eventos y detalle de Grupo; no cambiar UX/rutas al mismo tiempo que contratos backend.
5. **Cerrar fase 4:** pruebas end-to-end contra API real para los flujos completos y casos de error/idempotencia.
6. **Cerrar fases 5 y 6:** ejecutar gates completos, actualizar documentación sólo con evidencia, revisar diff/commit y desplegar con rollback definido.

### Reglas de control

- Una fase no avanza con fallos conocidos, contratos ambiguos o documentación contradictoria.
- Cada hallazgo se convierte en una regresión antes de considerarse cerrado.
- Cambios de backend, UI y datos se hacen por vertical de dominio, no como refactors masivos mezclados.
- El estado global será **Parcial** hasta que la fase 6 esté cerrada.

## 1. Principios de ejecución

- No tocar varias capas a ciegas en la misma fase.
- Cada fase debe cerrar una contradicción estructural, no solo un síntoma.
- No actualizar `ESTADO_EVANGELISMO.md` como “cerrado” hasta que la fase correspondiente quede verificada.
- Si una fase cambia permisos o contratos, actualizar:
  - `docs/EVANGELISMO_RBAC_MATRIX.md`
  - `docs/EVANGELISMO_API_CONTRACTS.md`
  - `docs/EVANGELISMO_QA_CHECKLIST.md`

## Auditoría de completitud y consistencia — 2026-07-18

**Dictamen:** el módulo tiene una cobertura funcional amplia y sus gates base
están disponibles, pero **no debe certificarse como 100%** hasta resolver los
hallazgos P0 y P1 siguientes. La auditoría revisó contratos, guards, alcance de
sede, soft delete, pantallas de plataforma y suites de Evangelismo. No se
modificó código funcional durante esta auditoría.

### Hallazgos registrados para ejecución

| ID | Prioridad | Hallazgo y evidencia | Trabajo de cierre | Criterio de aceptación |
|---|---|---|---|---|
| `EVM-AUD-001` | P0 | **Aislamiento de sede incompleto en eventos.** `PUT /events/{id}/audience` y `POST /events/{id}/assignments` consultan por ID sin validar sede ni evento activo. `GET /events/{id}/analytics` y el export tampoco restringen sede; `/events/analytics/global` agrega datos sin filtro de sede. | Crear un resolver único de evento activo y de la sede del usuario; aplicarlo a lectura, export, analytics y mutaciones. Mantener `404`/`403` conforme al contrato actual y no romper aliases. | Pruebas con dos sedes demuestran que no se puede leer, exportar, analizar ni mutar un evento de otra sede; analytics global solo contiene la sede solicitante. |
| `EVM-AUD-002` | P0 | **RBAC granular contradice el acceso contextual legacy de eventos.** Tras pasar `require_evangelism_read`, `require_event_access()` solo reconoce roles nominales (`admin`, `pastor`, `coordinador`) o asignación. Un usuario con permiso granular `evangelism:read` puede listar eventos, pero queda bloqueado en detalle, asistencia y sesión. El historial de asistencia repite la allowlist de roles. | Definir la regla final: `evangelism:read` habilita las superficies de lectura de la propia sede; la asignación solo amplía el flujo contextual. Reemplazar allowlists por capacidad canónica y conservar las excepciones explícitas. | Matriz backend admin/coordinador/lector/editor/gestor y usuario asignado: cada endpoint devuelve el resultado previsto sin 403 falsos ni acceso adicional. Actualizar matriz RBAC y contratos. |
| `EVM-AUD-003` | P1 | **La UI de Eventos asume gestión aunque la ruta admite lectura.** `events/page.tsx` hace un `Promise.all` que siempre solicita `/events/dashboard-stats` (manage) y `/crm/personas`; un 403 vacía también el listado permitido. La página de detalle siempre muestra `SessionTab`, que expone mutaciones y carga personas sin comprobar capacidad. | Separar cargas por capacidad con `hasModuleAccess`; preservar lista/analítica para lectura, ocultar o desactivar creación, agenda, visitantes y selección de personas cuando no correspondan. Usar errores independientes y cancelación de requests. | E2E con lector granular muestra lista, detalle y analítica; no hace solicitudes `manage` ni CRM no autorizadas. Gestor conserva todos los flujos. |
| `EVM-AUD-004` | P1 | **Check-in de visitante no es idempotente por asistencia.** `fast_checkin_visitor()` considera duplicado que la persona exista por correo/teléfono y retorna éxito sin crear `EventAttendance`; así una persona conocida que aún no asistió no queda marcada. La prueba actual solo cubre repetir el mismo alta. Además, varios subendpoints consultan `CrmEvent` sin excluir soft-deleted. | Separar «persona existente» de «asistencia existente» y aplicar la unicidad por `event_id + session_date + persona_id`. Reusar el resolver de evento activo de `EVM-AUD-001`. | Persona existente sin asistencia obtiene una asistencia; reintento de la misma sesión es idempotente; evento eliminado/cancelado no admite check-in ni agenda. |
| `EVM-AUD-005` | P1 | **QA no prueba las fronteras que protegen el módulo.** La cobertura de eventos usa el fixture admin y el E2E de eventos se ejecuta como admin con permisos `manage`; no hay casos de dos sedes, rol granular ni lector UI. | Añadir fixtures de dos sedes y matriz RBAC; convertir cada hallazgo P0/P1 en regresión backend y E2E. Mantener el gate canónico como punto de entrada. | Las suites fallan si reaparece fuga de sede, allowlist legacy, 403 falso o UI que llama un endpoint no permitido. |
| `EVM-AUD-006` | P2 | **Deuda estructural de UI localizada.** `strategies/[id]/page.tsx`, `events/page.tsx`, analytics de estrategia y detalles de grupo siguen concentrando estado, requests y numerosos `any`; el fetch principal de Eventos tampoco cancela al desmontar. | Descomponer por capacidades/paneles, tipar contratos de Eventos y consolidar hooks con `AbortController`. No cambiar rutas ni diseño durante esta fase. | Typecheck/lint y E2E profundos pasan; cada panel conserva un contrato tipado y no genera solicitudes tras desmontaje. |
| `EVM-AUD-007` | P2 | **Drift documental de permisos.** `EVANGELISMO_RBAC_MATRIX.md` y `EVANGELISMO_API_CONTRACTS.md` describen el check-in rápido como `require_active_user`, mientras el código exige `require_evangelism_edit`; también sobredeclaran la homogeneidad de eventos. | Actualizar la documentación únicamente después de fijar `EVM-AUD-001` y `EVM-AUD-002`, para reflejar el contrato final y no el estado intermedio. | Matriz, contratos, checklist y código describen el mismo guard, alcance de sede y comportamiento de soft delete. |
| `EVM-AUD-008` | P0 | **Alcance de sede incompleto fuera de Eventos.** El listado de estrategias aceptaba un `sede_id` arbitrario y el scanner generaba/validaba tokens de cualquier persona por UUID, sin verificar la sede del usuario. | Forzar la sede autenticada en colecciones y resolver personas del scanner en el tenant antes de generar o validar tokens. | Dos sedes: una estrategia y una persona ajenas no aparecen, no pueden filtrarse por query ni producir/validar tokens. |
| `EVM-AUD-009` | P0 | **Analytics de estrategia no validaba el recurso contra la sede.** Las rutas validaban existencia global y el análisis integral cargaba grupos sin filtro de sede; `velocity` agregaba historial global en vez de los participantes de la estrategia. | Centralizar la resolución de estrategia activa por sede; filtrar grupos y transiciones por la estrategia visible. | Toda variante de analytics de una estrategia ajena responde `404`; `velocity` solo agrega participantes de los grupos de la estrategia. |
| `EVM-AUD-010` | P0 | **Alta de grupos tenía un fallback de tenant inseguro.** Sin sede, tomaba la primera sede de la base; además no verificaba que estrategia ni personas vinculadas pertenecieran a la sede del gestor. | Exigir sede autenticada y validar estrategia/personas vinculadas dentro del tenant antes de crear. | Un gestor no puede crear un grupo usando estrategia o personas de otra sede, y un usuario sin sede recibe rechazo explícito. |
| `EVM-AUD-011` | P0 | **Rutas contextuales de grupo cargaban por UUID antes de validar sede.** Un rol contextual con bypass podía alcanzar detalle o asistencia de otro tenant si conocía el UUID. | Resolver grupo/sesión con sede y soft delete antes de aplicar ownership contextual. | Un coordinador de otra sede recibe `404` en detalle y asistencia, aun cuando su rol tiene bypass contextual. |

### Orden de ejecución de la sesión dedicada

1. Resolver `EVM-AUD-001` y `EVM-AUD-002` en backend, con pruebas de sede y RBAC antes de cambiar UI.
2. Resolver `EVM-AUD-004` y completar sus regresiones de eventos activos/idempotencia.
3. Resolver `EVM-AUD-003` con las capacidades ya estabilizadas por backend.
4. Cerrar `EVM-AUD-005` y ejecutar los gates backend/frontend.
5. Actualizar documentación (`EVM-AUD-007`); dejar `EVM-AUD-006` como fase de mantenimiento separada si no bloquea la certificación.

### Ejecución inicial — 2026-07-18

- `EVM-AUD-001`: backend corregido mediante un resolver único de evento activo y sede; aplicado a detalle, audiencia, agenda, analytics, export y analytics global.
- `EVM-AUD-002`: las comprobaciones de alcance de evento ya no contradicen los guards canónicos con allowlists de roles legacy; se agregó regresión de lector granular en la misma sede.
- `EVM-AUD-004`: el check-in ahora es idempotente por asistencia, permite a una persona existente registrar su primera asistencia y persiste la asistencia antes del puente CRM opcional.
- `EVM-AUD-003`: cerrado. La lista y el detalle separan lectura de operación; el E2E de lector confirma que no se solicitan estadísticas de gestión, personas CRM ni controles de sesión.
- `EVM-AUD-005`: cobertura ampliada con lector granular y dos sedes para las fronteras de eventos.
- `EVM-AUD-008`: cerrado en esta iteración. Estrategias fija la sede autenticada (también frente a `?sede_id=` ajeno) y Scanner resuelve la persona dentro de la sede antes de generar o validar un token; la regresión cubre el rechazo cruzado.
- `EVM-AUD-009`: cerrado en esta iteración. Analytics usa un resolver de estrategia activa por sede, `full` filtra grupos por tenant y `velocity` restringe sus transiciones a los participantes de la estrategia; las variantes principales se prueban contra una estrategia de otra sede.
- `EVM-AUD-010`: cerrado en esta iteración. La creación de grupos ya no tiene fallback a otra sede y valida la estrategia y todas las personas enlazadas antes de persistir; la matriz verifica el rechazo cruzado.
- `EVM-AUD-011`: cerrado en esta iteración. Los resolvers compartidos de grupo y sesión aplican sede y soft delete antes de la validación contextual; la regresión cubre el bypass de coordinador entre sedes.
- Validación ejecutada: regresiones específicas de eventos (`8 passed`), suite amplia de Evangelismo, typecheck frontend y E2E profundo de Evangelismo (Playwright `passed`).
- Validación de esta iteración: matriz RBAC/sede y scanner (`15 passed`, sin cobertura global), `scripts/test_evangelism_quality.py --backend-deep` y `git diff --check` en verde.

## 2. Orden de ataque recomendado

### Fase A — Definir el modelo real de acceso del módulo

Objetivo:

- decidir y documentar qué superficies deben gobernarse por:
  - `evangelism:read`
  - `evangelism:edit`
  - `evangelism:manage`
  - acceso contextual
  - `require_active_user`

Trabajo:

1. inventariar rutas de eventos que hoy usan `require_active_user`
2. decidir cuáles son intencionalmente contextuales
3. decidir si `GET /events/` es `read` real o `manage` encubierto
4. fijar la matriz final por superficie

Salida esperada:

- decisión explícita de arquitectura sobre RBAC de eventos
- checklist clara para backend y frontend

Bloqueadores resueltos:

- evita seguir corrigiendo UI con una semántica de permisos indefinida

### Fase B — Corregir incoherencias backend de permisos

Objetivo:

- eliminar contradicciones entre dependencia declarada y chequeo real

Trabajo mínimo:

1. corregir `backend/api/evangelism_events/events_main.py`
   - `GET /events/`
   - mensaje y lógica de permiso
2. revisar si otras rutas de eventos mezclan guard canónico + filtro manual de rol
3. validar que la semántica final coincida con Fase A

Salida esperada:

- backend sin rutas que anuncien `read` y ejecuten `manage`

### Fase C — Alinear frontend con `evangelism:*` y con el modelo real del backend

Objetivo:

- sacar al frontend del modelo legacy “pastoral o administrativo”

Trabajo:

1. refactorizar `EvangelismShell`
2. refactorizar `EvangelismClient`
3. revisar gating en:
   - `strategies/[id]/page.tsx`
   - `groups/page.tsx`
   - `groups/[id]/page.tsx`
   - otras vistas con listas cerradas de roles
4. basar visibilidad y fetches en:
   - `hasModuleAccess(...)`
   - capacidades reales de la superficie
   - ownership/contexto cuando aplique

Salida esperada:

- usuarios con permisos granulares válidos no quedan falsamente bloqueados
- `coordinador` deja de depender de hacks de UI

### Fase D — Blindar QA de permisos por rol

Objetivo:

- que la migración RBAC deje de depender de pruebas con `admin`

Trabajo:

1. agregar matriz de tests backend por rol:
   - admin
   - coordinador
   - lector granular
   - editor granular
   - gestor granular
2. cubrir especialmente:
   - estrategias
   - eventos
   - grupos
   - scanner
   - asistencia contextual
3. agregar o extender e2e mínimo para un rol no-admin

Salida esperada:

- regresiones RBAC detectables automáticamente

### Fase E — Reparar el gate canónico frontend profundo

Objetivo:

- recuperar confiabilidad operativa del QA frontend del módulo

Trabajo:

1. aislar por qué `playwright.config.ts` + `run-managed-playwright.mjs` dependen de `next dev -H 0.0.0.0`
2. determinar si el fallo `EPERM` es:
   - del entorno
   - del host bind
   - del webServer config
3. dejar un camino reproducible para:
   - `npm run test:e2e:evangelism`
   - `npm run test:e2e:evangelism:deep`
   - `scripts/test_evangelism_quality.py --frontend-deep`

Salida esperada:

- gate frontend profundo funcional o causa raíz documentada con workaround oficial

### Fase F — Endurecer la suite de analytics y coverage auxiliar

Objetivo:

- que la cobertura auxiliar deje de aceptar fallos internos como señal válida

Trabajo:

1. corregir `_ok(status)` en `tests/test_evangelism_analytics_coverage.py`
2. revisar otras suites “coverage” que toleren demasiado
3. separar claramente:
   - tests de cobertura de líneas
   - tests de contrato/estabilidad

Salida esperada:

- una suite que falla cuando analytics devuelve `500`

Estado: **cerrada el 2026-07-18**. La allowlist de
`tests/test_evangelism_analytics_coverage.py` excluye `500` y cuenta con una
regresion explicita que verifica ese comportamiento (`34 passed`).

### Fase G — Continuar la descomposición estructural del frontend

Objetivo:

- bajar el riesgo sistémico de las pantallas grandes del módulo

Superficies prioritarias:

1. `strategies/[id]/page.tsx`
2. `events/page.tsx`
3. `groups/[id]/page.tsx`

Trabajo:

1. seguir extrayendo hooks y paneles
2. reducir `any`
3. añadir `AbortController` y cleanup donde falte
4. consolidar tipos compartidos

Salida esperada:

- menos superficie de regresión
- mejor mantenibilidad
- contratos UI más fuertes

## 3. Backlog priorizado

### P0 — Crítico

- Reconciliar RBAC real del módulo entre backend, frontend y docs

### P1 — Alto

- Corregir `GET /events/`
- Alinear gating frontend con `evangelism:*`
- Restaurar gate `--frontend-deep`

### P2 — Medio

- Cobertura de permisos por rol no-admin
- Endurecer suites de analytics
- Seguir descomposición de pantallas grandes

## 4. Definición de cierre por fase

Una fase se considera cerrada solo si:

1. el cambio de código existe
2. la suite relevante pasa
3. la documentación contractual quedó alineada
4. el hallazgo correspondiente deja de reproducirse

## 5. Comandos sugeridos para la próxima sesión

Diagnóstico rápido:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --backend-deep
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
```

Lectura obligatoria:

```bash
cat docs/AUDITORIA_FORENSE_EVANGELISMO_2026-07-17.md
cat docs/PLAN_DE_TRABAJO_EVANGELISMO.md
cat docs/ESTADO_EVANGELISMO.md
cat docs/EVANGELISMO_RBAC_MATRIX.md
cat docs/EVANGELISMO_API_CONTRACTS.md
```
