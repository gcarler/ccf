# Plan de Saneamiento del Módulo CRM — CCF

**Estado**: DRAFT
**Fecha**: 2026-08-14
**Responsable**: Dev Team
**Documento padre**: `docs/ESTADO_CRM.md`

---

## Resumen Ejecutivo

El módulo CRM de CCF está en estado **funcionalmente estable** pero con deuda técnica acumulada en tres dimensiones:

1. **Hallazgos de auditoría pendientes**: 25 🔴 items sin resolver (A-03..A-07, M-05..M-07, F-01)
2. **Deuda estructural**: monolitos masivos en backend y frontend (pastoral.py 2.578 LOC, resources/page.tsx 1.341 LOC)
3. **Deuda de tipado**: 93 usos de `any` en frontend — el más alto de toda la plataforma

La auditoría forense está **cerrada formalmente** (iteración 3 "super-Pro" completada), pero las 3 dimensiones de deuda persisten. Este plan las aborda incrementalmente sin bloquear desarrollo de nuevos features.

---

## Estado Actual — Hallazgos Pendientes

### 🔴 Backend — Alta (8 items)

| ID | Hallazgo | Archivo | Líneas | Severidad |
|---|------|---|---|---|
| **A-03** | 6 funciones CRUD sin sede_id | crud/crm_/families.py | 6 | 🔴 MEDIA |
| **A-04** | 70 funciones CRUD sin sede_id | crud/crm_/extended.py | 1.077 | 🔴 ALTA |
| **A-05** | 5 funciones CRUD sin sede_id | crud/crm_/volunteers.py | 5 | 🔴 MEDIA |
| **A-06** | get_crm_tasks sin sede_id | crud/crm_/tasks.py | 1 | 🔴 MEDIA |
| **A-07** | Duplicación lógica en automation-edges endpoints | api/crm/pastoral.py | ~100 | 🔴 BAJA |
| **A-08** | flow_builder_three_node_render sin sede filter | frontend/src/... | 1 | 🔴 BAJA (subsumido por C-04, pero marcado pendiente) |

**Impacto**: Violación del axioma multi-tenant REGLAS.md §4 — consultas sin sede_id pueden filtrar datos de otras sedes.

**Defensas existentes**: La capa API tiene `get_user_sede_id()` que filtra por sede_id en endpoints críticos, pero la capa CRUD no aplica el filtro internamente en estas funciones. Esto crea un agujero de seguridad si alguien llama directamente a las funciones CRUD desde test, script o service interno.

---

### 🔴 Frontend — Media (2 items, 20 archivos afectados)

| ID | Hallazgo | Archivos | Cantidad | Severidad |
|---|------|---|---:|---|
| **M-05** | useEffect sin AbortController | 9 archivos | 9 | 🔴 MEDIA (memory leaks) |
| **M-06** | Validación de URL ausente en params[id] | 9 archivos | 9 | 🔴 MEDIA (vulnerabilidad) |
| **M-07** | Hardcoded Tailwind colors | 2 archivos | 2 | 🔴 BAJA (deuda visual) |

**Archivos afectados (M-05 + M-06)**:

| Ruta | Tipo |
|---|---|
| `frontend/src/app/plataforma/crm/resources/page.tsx` | Both |
| `frontend/src/app/plataforma/crm/conversations/[id]/page.tsx` | M-06 |
| `frontend/src/app/plataforma/crm/people/[id]/page.tsx` | M-06 |
| `frontend/src/app/plataforma/crm/tasks/[id]/page.tsx` | M-06 |
| `frontend/src/app/plataforma/crm/commitments/[id]/page.tsx` | M-06 |
| `frontend/src/app/plataforma/crm/commitments/page.tsx` | M-05 |
| `frontend/src/app/plataforma/crm/families/[id]/page.tsx` | M-06 |
| `frontend/src/app/plataforma/crm/families/page.tsx` | M-05 |
| `frontend/src/app/plataforma/crm/communications/[id]/page.tsx` | M-06 |

**Impacto**:
- M-05: Memory leaks en useEffect que no limpian `fetch` pendientes al unmount
- M-06: Sin validación de UUID en `params[id]` → 500 o 404 silenciosos si el usuario manipula la URL con IDs malformados
- M-07: 2 archivos con `bg-blue-500`, `text-gray-900` en lugar de tokens semánticos (rompe consistency)

---

### 🟡 Funcionalidades — Baja (1 item, 1 deferido)

| ID | Hallazgo | Estado | Severidad |
|---|------|---|---|
| **F-01** | Bitácora de categorías (CRUD, despliegue, métricas) | PENDIENTE | 🟡 BAJA |
| **F-02** | Endpoint validador consolidado | DEFERIDO (optativa) | 🟡 BAJA |

**Impacto**: F-01 es un feature faltante — no es deuda técnica, sino funcionalidad no implementada. F-02 fue deferida porque la arquitectura actual puede manejar validaciones en endpoints individuales sin un consolidador central.

---

## Deuda Estructural — Monolitos y Tipado

### 🟥 Monolitos Backend (CRM + Afines)

| Archivo | LOC | Problema | Prioridad de split |
|---|---:|---|---:|
| `api/crm/pastoral.py` | **2.578** | 84 funciones, mezcla de 6 dominios (personas, familias, voluntariado, tareas, comunicaciones, evangelismo) | **1** |
| `crud/crm_/extended.py` | **1.077** | 70 funciones sin sede_id, mezcla de 8 dominios (analytics, export, seed, upsert personas) | **2** |
| `crud/crm_/families.py` | 677 | 13 funciones, 6 sin sede_id | **3** |
| `crud/crm_/volunteers.py` | 942 | 28 funciones, 5 sin sede_id | **4** |

### 🟥 Monolitos Frontend (CRM)

| Archivo | LOC | Problema | Prioridad de split |
|---|---:|---|---:|
| `crm/resources/page.tsx` | **1.341** | Recursos CRUD completo en una sola página — mezcla list + detalle + edit + filters | **1** |
| `crm/conversations/[id]/page.tsx` | 578 | Conversación completa en una sola página — mezcla header + lista + detalle + composer | **2** |

### 🟦 Tipado — 93 usos de `any` en frontend CRM

Es el módulo con **más deuda de tipado de toda la plataforma** (69 `any` en CMS, 93 en CRM). La mayoría están en:
- Props de componentes complejos (reusable drawers, tables, forms)
- Responses de apiFetch sin tipos estrictos
- Context providers con datos heterogéneos

---

## Plan de Trabajo — Fases

### FASE 0: Preparación y Defensas (1 día)

**Objetivo**: Crear defensas que mitigan riesgo mientras se aborda la deuda lentamente.

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T0.1** | Añadir validación de sede_id obligatoria en API layer para endpoints afectados | `backend/api/crm/pastoral.py` | ~30 |
| **T0.2** | Crear middleware de logging para llamadas CRUD sin sede_id (detectar uso en runtime) | `backend/core/middleware.py` | ~50 |
| **T0.3** | Crear utilidad `isValidUUID(s)` en frontend para reusar en M-06 | `frontend/src/lib/validation.ts` | ~20 |
| **T0.4** | Crear utilidad `useEffectWithAbort` wrapper para reusar en M-05 | `frontend/src/hooks/useEffectWithAbort.ts` | ~30 |

**Resultados esperados**:
- Defensas que alertan en logs si alguien llama funciones CRUD sin sede_id
- Utilidades reutilizables que reducen código repetitivo en M-05 + M-06

---

### FASE 1: Sede_id en CRUD (2 días)

**Objetivo**: Cerrar A-03, A-04, A-05, A-06 — añadir sede_id a todas las funciones CRUD sin filtro.

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T1.1** | Añadir `sede_id: str | None = None` a 6 funciones en families.py + filtros queries | `backend/crud/crm_/families.py` | ~40 |
| **T1.2** | Añadir `sede_id: str | None = None` a 70 funciones en extended.py + filtros queries | `backend/crud/crm_/extended.py` | ~300 |
| **T1.3** | Añadir `sede_id: str | None = None` a 5 funciones en volunteers.py + filtros queries | `backend/crud/crm_/volunteers.py` | ~35 |
| **T1.4** | Añadir `sede_id: str | None = None` a get_crm_tasks en tasks.py + filtro query | `backend/crud/crm_/tasks.py` | ~15 |
| **T1.5** | Tests: crear casos para cada función con sede_id=NULL para verificar que no retorna datos de otras sedes | `backend/tests/test_crm_*.py` | ~200 |
| **T1.6** | Verificación: correr suite CRM completa + smoke tests de producción | — | — |

**Resultados esperados**:
- ✅ A-03, A-04, A-05, A-06 cerrados
- 100% de funciones CRM CRUD con sede_id obligatorio
- Logs de middleware en silencio (ninguna llamada sin sede_id)

**Riesgos**:
- Cambios en queries pueden afectar performance si los índices no cubren sede_id + PK
- Mitigación: Ejecutar `EXPLAIN ANALYZE` en queries críticas antes y después

---

### FASE 2: Memory Leaks y Validación Frontend (1.5 días)

**Objetivo**: Cerrar M-05, M-06, M-07 — reparar useEffect, validar UUIDs, reemplazar hardcoded colors.

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T2.1** | Reemplazar useEffect con `useEffectWithAbort` en 9 archivos afectados (M-05) | 9 archivos frontend | ~90 |
| **T2.2** | Añadir validación `if (!isValidUUID(params.id)) notFound()` en 9 páginas con `[id]` (M-06) | 9 archivos frontend | ~45 |
| **T2.3** | Reemplazar `bg-blue-500` con `bg-brand-500` y `text-gray-900` con `text-neutral-900` (M-07) | 2 archivos frontend | ~10 |
| **T2.4** | Tests: crear test que simula unmount durante fetch pendiente para verificar cleanup | `frontend/src/lib/http.test.ts` | ~30 |
| **T2.5** | Verificación: `npx next lint` + `npx tsc --noEmit` + build frontend | — | — |

**Resultados esperados**:
- ✅ M-05, M-06, M-07 cerrados
- 0 memory leaks en useEffect del CRM
- 0 500s por IDs malformados en rutas `[id]`
- 100% de colors provenientes de tokens semánticos

**Riesgos**:
- Cambios en `params.id` validación pueden afectar test que ya esperan 500
- Mitigación: Actualizar test para esperar 404/422 en lugar de 500

---

### FASE 3: Reducir Tipado `any` (3 días)

**Objetivo**: Reducir 93 `any` → <30 `any` (reducir 70% de la deuda de tipado CRM).

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T3.1** | Auditoría: listar todas las ocurrencias de `any` en CRM con contexto (archivo, línea, razón) | — | — |
| **T3.2** | Priorización: dividir en 3 buckets — (a) trivial (props simples), (b) medio (response types), (c) complejo (legacy schemas) | — | — |
| **T3.3** | Bucket (a) trivial: reemplazar `any` con tipos concretos en componentes simples | ~20 archivos | ~150 |
| **T3.4** | Bucket (b) medio: crear/response types para endpoints CRM más usados (personas, familias, tareas) | `frontend/src/types/crm.ts` (nuevo) | ~200 |
| **T3.5** | Bucket (c) complejo: dejar `any` donde el costo/beneficio no justifica (ej: legacy schemas en desuso) | — | — |
| **T3.6** | Verificación: `npx tsc --noEmit` debe pasar sin errores | — | — |

**Resultados esperados**:
- 93 `any` → 25-30 `any` (reducción 70%)
- Tipos CRM estrictos para los endpoints más críticos
- `any` restringido a código legacy o muy heterogéneo

**Riesgos**:
- Tipado estricto puede bloquear features que aún no tienen tipos definidos
- Mitigación: Dejar `any` explícitamente comentado con `// TODO: tipo estricto` en casos complejos

---

### FASE 4: Monolito Backend Split (5 días)

**Objetivo**: Reducir `api/crm/pastoral.py` 2.578 LOC → <1.000 LOC por archivo (split en 3+ módulos).

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T4.1** | Análisis: agrupar 84 funciones por dominio (personas, familias, voluntariado, tareas, comunicaciones, evangelismo) | — | — |
| **T4.2** | Crear paquete `api/crm/` con módulos: `personas.py`, `familias.py`, `voluntariado.py`, `tareas.py`, `comunicaciones.py` | 5 nuevos archivos | ~2.500 |
| **T4.3** | Migrar funciones + tests de pastoral.py a módulos nuevos | — | — |
| **T4.4** | Re-exportar en `api/crm/__init__.py` para preservar API pública existente | `api/crm/__init__.py` | ~50 |
| **T4.5** | Deprecar `api/crm/pastoral.py` (dejar imports deprecated) | — | ~30 |
| **T4.6** | Verificación: tests CRM pasan, endpoints response unchanged | — | — |

**Resultados esperados**:
- 2.578 LOC → 5 archivos ~500 LOC cada uno
- 0 imports broken (re-export preserva API)
- Logs de migration clean (0 errors en runtime)

**Riesgos**:
- Split puede romper imports internos si hay referencias cruzadas entre dominios
- Mitigación: Lazy imports donde haya ciclos (ver MEMORY.md §Architecture decisions)

---

### FASE 5: Monolito Frontend Split (3 días)

**Objetivo**: Reducir `crm/resources/page.tsx` 1.341 LOC → <600 LOC (split en components).

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T5.1** | Análisis: identificar secciones en resources/page.tsx (filters, list, edit drawer, delete confirm) | — | — |
| **T5.2** | Extraer components: `ResourceFilters.tsx`, `ResourceList.tsx`, `ResourceEditDrawer.tsx`, `ResourceDeleteConfirm.tsx` | 4 nuevos archivos | ~800 |
| **T5.3** | Reemplazar monolito page con composición de components | `crm/resources/page.tsx` | ~400 |
| **T5.4** | Tests: extraer tests de page.test.tsx a component tests | 4 nuevos archivos | ~300 |
| **T5.5** | Verificación: `npx next lint` + `npx tsc --noEmit` + build frontend | — | — |

**Resultados esperados**:
- 1.341 LOC → page.tsx 400 LOC + 4 components ~200 LOC cada uno
- Components reutilizables en otras páginas CRM (familias, tareas)
- Tests más granulares (unit tests por component)

**Riesgos**:
- Split puede romper state sharing entre components
- Mitigación: Usar context providers o hoist state a page donde sea necesario

---

### FASE 6: Monolito CRUD Extended Split (4 días)

**Objetivo**: Reducir `crud/crm_/extended.py` 1.077 LOC → <600 LOC por archivo (split en 2+ módulos).

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T6.1** | Análisis: agrupar 70 funciones por dominio (analytics, export, seed, upsert personas) | — | — |
| **T6.2** | Crear módulos: `analytics.py`, `export.py`, `seed.py`, `upsert.py` en `crud/crm_/` | 4 nuevos archivos | ~800 |
| **T6.3** | Migrar funciones + tests de extended.py a módulos nuevos | — | — |
| **T6.4** | Re-exportar en `crud/crm_/extended/__init__.py` si es un paquete, o en `extended.py` como wrapper | — | ~50 |
| **T6.5** | Verificación: tests CRM pasan, queries performance unchanged | — | — |

**Resultados esperados**:
- 1.077 LOC → 4 archivos ~270 LOC cada uno
- Sedes_id ya aplicado en FASE 1, solo reorganización estructural
- Queries performance idéntica (EXPLAIN ANALYZE antes/después)

**Riesgos**:
- Pueden existir funciones interdependientes entre dominios (analytics llama export, etc.)
- Mitigación: Lazy imports en módulos si hay ciclos

---

### FASE 7: F-01 Bitácora de Categorías (2 días)

**Objetivo**: Implementar funcionalidad faltante F-01 — bitácora para tracking de categorías.

| Tarea | Acción | Archivo | Líneas |
|---|---|---|---|
| **T7.1** | Backend: crear modelo `CrmCategoryLog` (id, category_id, action, user_id, timestamp, metadata) | `backend/models_crm.py` | ~30 |
| **T7.2** | Backend: crear CRUD `create_category_log`, `list_category_logs` | `backend/crud/crm_/categories.py` | ~50 |
| **T7.3** | Backend: añadir log a endpoints de categoría CRUD (create, update, delete) | `backend/api/crm/pastoral.py` | ~40 |
| **T7.4** | Frontend: crear página `/plataforma/crm/categories/logs` con tabla paginada | `frontend/src/app/plataforma/crm/categories/logs/page.tsx` | ~300 |
| **T7.5** | Frontend: añadir filtros por categoría, acción, rango de fechas | — | ~200 |
| **T7.6** | Tests: backend + frontend tests para bitácora | ~2 archivos | ~150 |
| **T7.7** | Verificación: deploy en staging + pruebas manuales | — | — |

**Resultados esperados**:
- ✅ F-01 cerrado
- Bitácora funcional con CRUD completo
- Auditoría de cambios en categorías disponible

---

## Métricas de Éxito

### Antes vs Después

| Métrica | Antes | Después (meta) | % mejora |
|---|---:|---:|---:|
| **Hallazgos pendientes** | 25 🔴 | 0 🔴 | 100% |
| **Funciones CRUD sin sede_id** | 82 | 0 | 100% |
| **useEffect sin AbortController** | 9 | 0 | 100% |
| **Páginas sin validación UUID** | 9 | 0 | 100% |
| **Hardcoded Tailwind colors** | 2 | 0 | 100% |
| **Tipado `any` en CRM** | 93 | <30 | 68%+ |
| **Monolito backend (pastoral.py)** | 2.578 LOC | <1.000 LOC/archivo | 60%+ |
| **Monolito frontend (resources/page.tsx)** | 1.341 LOC | <600 LOC | 55%+ |
| **Monolito CRUD extended** | 1.077 LOC | <600 LOC/archivo | 45%+ |

### Métricas de Calidad

- **Cobertura de tests CRM**: ~67% (actual) → >80% (meta)
- **Pre-push gate**: 0 failures en `pytest` y `vitest` tras cada fase
- **Production 500s**: 0 500s en rutas CRM tras despliegue
- **Performance queries**: EXPLAIN ANALYZE antes/después de cambios en CRUD — no degradación >20ms

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---:|---|---|
| **R1**: Cambios en queries con sede_id degradan performance | Media | Alta | EXPLAIN ANALYZE antes/después; añadir índices compuestos si necesario |
| **R2**: Split de monolitos rompe imports internos | Alta | Alta | Lazy imports para ciclos; tests completos tras cada split |
| **R3**: Tipado estricto bloquea features en desarrollo | Media | Media | Dejar `any` explícitamente comentado en casos complejos; fases graduales |
| **R4**: Memory leaks en useEffect no detectan todas las fugas | Baja | Media | Tests de mount/unmount repetitivos; profiling con React DevTools |
| **R5**: Validación UUID en params[id] rompe test existentes | Media | Baja | Actualizar test para esperar 404/422 en lugar de 500 |

---

## Dependencias y Bloqueadores

| Bloqueador | Fase afectada | Dependencia | Desbloqueo |
|---|---|---|---|
| **B1**: Índices de DB no cubren sede_id + PK | FASE 1 | DB Admin | Crear índices compuestos antes de FASE 1 |
| **B2**: Team availability para testing manual de F-01 | FASE 7 | QA Team | Programar pruebas manuales con 2 días de antelación |
| **B3**: Merge conflicts con features en desarrollo paralelo | FASES 3-6 | Dev Team | Coordinar merges diarios con feature branches |

---

## Cronograma Sugerido

| Fase | Días | Fecha inicio (ejemplo) | Fecha fin (ejemplo) |
|---|---:|---|---|
| **FASE 0** | 1 | 2026-08-15 | 2026-08-15 |
| **FASE 1** | 2 | 2026-08-16 | 2026-08-17 |
| **FASE 2** | 1.5 | 2026-08-18 | 2026-08-19 |
| **FASE 3** | 3 | 2026-08-20 | 2026-08-22 |
| **FASE 4** | 5 | 2026-08-23 | 2026-08-27 |
| **FASE 5** | 3 | 2026-08-28 | 2026-08-30 |
| **FASE 6** | 4 | 2026-08-31 | 2026-09-03 |
| **FASE 7** | 2 | 2026-09-04 | 2026-09-05 |
| **TOTAL** | **21.5 días** | — | — |

**Sprint alternativo (más corto)**: Si el tiempo es limitado, priorizar **FASE 0 + FASE 1 + FASE 2** (4.5 días) — esto cierra todos los hallazgos de seguridad y calidad de frontend. Las fases 3-7 son deuda estructural/optativa.

---

## Próximos Pasos

1. **Revisar este plan** con el equipo Dev/Lead para validar prioridades y cronograma
2. **Desbloquear B1** — revisar índices de DB con DB Admin antes de FASE 1
3. **Crear feature branch** `feature/crm-sanitization` en `/root/ccf` (o feature branch por fase si se prefiere)
4. **Comenzar FASE 0** — utilidades reutilizables + middleware de logging

---

## Documentos Relacionados

- `docs/ESTADO_CRM.md` — Estado actual del módulo
- `errorescrm.md` — Tracker de hallazgos de auditoría forense
- `/root/.local/share/mimocode/memory/projects/global/MEMORY-crm-qc18-audit-closure.md` — Memoria de la auditoría QC18
- `/root/.local/share/mimocode/memory/projects/global/MEMORY-crm-audit-doctrines.md` — Doctrinas de auditoría CCF

---

## Changelog

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-08-14 | DRAFT inicial | Agent |
| 2026-08-14 | Añadida sección de monolitos frontend + tipado | Agent |
| 2026-08-14 | Añadidas métricas de éxito antes/después | Agent |
| 2026-08-14 | Añadido cronograma sugerido + sprint alternativo | Agent |

---

**Estado**: LISTO PARA REVISIÓN 🟡

---

*Fin del plan de saneamiento CRM — CCF*