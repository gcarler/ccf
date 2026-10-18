# INFORME FORENSE — Auditoría Transversal de Axiomas 1/3, Soft-Delete, Drawers y Plan de Saneamiento de CMS Builder (CCF)

**Ticket:** TKT-PLATFORM-CROSS-MODULE-AXIOMS-AUDIT-01 · **Auditor:** freebuff · **Revisor:** agy
**Fecha:** 2026-10-18 · **Worktree:** /root/ccf-freebuff (HEAD inicial `aa867f06`) · **Alcance:** solo-lectura + informe
**Módulos auditados:** CRM, Contabilidad/Finanzas (finance_suite), Academia, Eventos, Pastoral + CMS Builder.

---

## BLOQUE 1 — Cumplimiento de Reglas Canónicas

### 1.1 Axioma 1 (Kernel de Personas) — ✅ CUMPLIDO

- `auth_users` NO es una tabla paralela de identidad: **es la misma identidad** canónica. Evidencia `backend/models_auth.py:48`: `id = Column(UUID, ForeignKey("personas.id", ondelete="CASCADE"), primary_key=True)` — PK compartida 1:1 (enlace explícito `Usuario.id == Persona.id`, línea 74).
- Inventario de FKs humanas en los 5 módulos: **84 FKs a `personas.id`** (crm:6, academy_core:22, finance_suite:11, enterprise:15, cms:14, crud_pipeline:3, wiki:2, evangelism:1, agenda:1, conversation:1, governance:1, agents:5, kernel:3) y **solo 3 FKs a `auth_users.id`** (todas en `backend/models_crm.py`: `ChatMessage.sender_id:35`, `ChatRoom.last_sender_id:57`, `ChatRoomMember:72`) — equivalentes al kernel por el PK compartido (trásito vía `Usuario.id == Persona.id`). Sin tablas tipo `user_profiles`/`usuarios` operativas (grep = 0 en modelos operativos).
- **Dictamen:** cumple Axioma 1. Mejora opcional (P2): redirección formal de las 3 FKs de chat a `personas.id` para cerrar la lectura literal del canon.

### 1.2 Axioma 3 (Aislamiento Multi-Tenant) — ⚠️ 1 VIOLACIÓN CONFIRMADA

- Patrón correcto dominante: **343 usos** de `get_user_sede_id()` en backend/api — la sede se obtiene del actor.
- CMS sites resuelto explícitamente: `backend/api/cms_v2/sites.py:63-71` y `backend/api/cms/admin/sites.py:59-62` — el comentario "ignorando cualquier valor cross-sede del cliente" confirma que el `sede_id` del payload se sobreescribe con el del actor. ✅
- **HALLAZGO H-01 (violación):** `backend/api/academy.py:5325-5339` — endpoint `GET /academy/analytics/institutional-summary` (rol `AcademyReader`):
  - Recibe `sede_id: Optional[UUID] = Query(None)` del **cliente** (línea 5339, única Query de sede en todo academy.py).
  - Sin `sede_id` en el request, la query NO filtra por sede del actor → devuelve KPIs consolidados de **todas las sedes** (BOLA multi-tenant: un lector de la sede A ve métricas de alumni/grupos de la sede B).
  - Además no invoca `get_user_sede_id` (grep en el bloque = 0).
  - **Corrección propuesta (P0):** `actor_sede = get_user_sede_id(db, current_user.id)`; ignorar el Query param salvo que el actor tenga permiso global (`sede_id is None` solo para `sede_id IS NULL | == actor_sede`), y añadir test anti-fuga.

### 1.3 Actor UUID + Soft Deletes — ✅ CUMPLIDO

- Mutaciones exigen `current_user.id` (actor UUID canónico) — verificado como patrón dominante en rutas de los 5 módulos (`require_module_access` + actor en `crud`).
- Hard deletes: grep `db.delete|DELETE FROM|TRUNCATE` en `api/crm`, `academy.py`, `events`, `finance_suite`, `pastoral` = **0 eliminaciones físicas de entidades operativas** (los "truncate" detectados eran `safe_truncate()` de texto de correo en `crm/pastoral.py:1192`). Deletes con `deleted_at` y campos `deleted_at` en cascadas confirmados; los `ondelete="CASCADE"` de FKs (crm:35, academy_core:22, finance_suite:15) son físicos estructurales de dependencias (patrón aceptado por el canon para hijos de entidad).
- Evidencia de disciplina格外: `backend/api/academy.py:2071` documenta ACAD-MED-003 "soft delete via deleted_at, NO db.delete()".

### 1.4 Frontend (Drawers, apiFetch, tokens) — ✅ CUMPLIDO

- `fetch()` crudo en los 5 módulos: **0 ocurrencias** (grep excluyendo tests y `apiFetch|refetch|prefetch`).
- Modals centrados (`AlertDialog|<Modal|Dialog open`): **0 usos activos** en las carpetas de los 5 módulos (única coincidencia por nombre en `components/crm/PersonaDetailSidebar.tsx` sin declaración activa; no hay `AlertDialog` renderizado). Patrón Drawer/Sidebar vigente.
- Nota conservadora: la verificación es por coincidencias de patrón; una revisión visual de 5 módulos (fly-through) en despliegue activo cerraría el 100%.

---

## BLOQUE 2 — Inventario `any` del CMS Builder y Plan de Saneamiento

### 2.1 Dimensionamiento real

Total: **142 ocurrencias de `: any | as any | <any> | any[]`** en 15 archivos (el ticket estimaba ~120; números exactos por conteo):

| Archivo | any | Tipo | Clasificación |
|---|---|---|---|
| `app/plataforma/cms/builder/page.tsx` | 45 | Código prod | Almacén de tipos de Puck |
| `components/cms/builder/AutoSaveAndHeaderSave.test.tsx` | 15 | Test | Mock Props sin tipar |
| `components/cms/builder/EmpiricalChallengeM5.test.tsx` | 13 | Test | Mock Props |
| `components/cms/builder/PuckSchemaRegistration.test.tsx` | 11 | Test | Config de Puck en test |
| `app/plataforma/cms/__tests__/pages_r1_r6_verification.test.tsx` | 11 | Test | Mock Props |
| `components/cms/builder/AiFieldAdversarial.test.tsx` | 9 | Test | Mock Props |
| `components/cms/builder/GalleryCardsEmpiricalRobustness.test.tsx` | 8 | Test | Mock Props |
| `app/plataforma/cms/builder/page.test.tsx` | 7 | Test | Mock Props |
| `components/cms/builder/PuckSchemaRegistrationEdgeCases.test.tsx` | 5 | Test | Config de Puck |
| `app/plataforma/cms/ab-testing/page.tsx` | 5 | Código prod | `catch (err: any)` ×5 (líneas 201,216,232,244,267) |
| `components/cms/builder/PuckSchemaRegistrationEdgeCases` + otros tests sueltos | ~8 | Test | Mock Props |
| `components/cms/builder/MediaPicker.tsx` | 1 | Código prod | `items.filter((item: any))` (línea 93) |

### 2.2 Clasificación con interfaces propuestas (stack real: `@puckeditor/core ^0.22.4`, página importa `Puck, Config`)

**`frontend/src/types/cms-builder.ts` (nuevo archivo maestro):**

- `PuckData = Data` (re-export de `@puckeditor/core`) → reemplaza `{ content: any[] }` en page.tsx líneas 143, 149, 961, 1130, 1150 (initialData, latestDataRef, dataToSave, handlePuckChange, handleSave).
- `DbSection` (DTO canónico del back-end): `id: string; type: string; title?: string; props: Record<string, unknown>; order_index?: number; ...` → reemplaza `dbSections: any[]` (144, 154) y `(sec: any)` del map (202).
- Tipos por campo de render en los ComponentConfigs (≈25 ocurrencias de `render: ({ value, onChange }: any)` en hero/rich_text/cta/etc., líneas 246-491): usar los generics de Puck (`GenericFieldProps<T>` si la lib los exporta en 0.22) o adaptadores locales `StrFieldProps<T> = { value: string; onChange: (v: string) => void; ... }` definidos en el archivo maestro y reutilizados por cada bloque.
- Entidades de listas (`getItemSummary: (item: any)` ×5, líneas 497 (FAQ), 553 (autores), 623 (valores/labels), 696 y 822 (carouseles)): definir `FaqItem`, `AuthorItem`, `OptionItem`, y truers `CarouselItem/SlidePricing...` tipados como genéricos `{ [K in keyof T]: T[K] }` de la sección correspondiente con `ListField<TEntity>`.
- `MediaItem` para `MediaPicker.tsx:93` (`filter((item: any))`).
- Tests: mocks sin tipos → (a) builders de fixture `makeDbSection(type, overrides?): DbSection`, (b) `Partial<PuckData>` en stubs de Puck (`puckPropsCaptured: Partial<PuckProps>` en AutoSaveAndHeaderSave.test.tsx:43-45), (c) `mockResolvedValue` con el DTO real `DbSection` en lugar de `(f as any).mockResolvedValue`.
- `catch (err: any)` en ab-testing (5×): regla moderna ya adoptada en otros módulos → `catch (err: unknown)` + guard `err instanceof Error ? err.message : String(err)`.

### 2.3 Objetivo "cero any en toda la plataforma"

Tras el FIX-06 en curso (22 archivos no-CMS), el módulo CMS es el último reducto: 142 → 0 con el plan anterior. Validación de cierre: `npx tsc --noEmit`, `npx eslint --max-warnings=0`, `vitest run src/app/plataforma/cms src/components/cms`, y deploy + HTTP 200.

---

## PLAN PRIORIZADO PARA AGY2

**P0 — TKT-CMS-A (Saneamiento Builder parcial, ~1 día):**
1. Crear `frontend/src/types/cms-builder.ts` con `PuckData`, `DbSection`, `StrFieldProps<T>/FieldProps<T>`, y entidades de lista (FaqItem, AuthorItem, OptionItem, CarouselItem).
2. Migrar `builder/page.tsx` (45 any → 0) con tsc/eslint en verde; **sin** cambiar lógica de guardado ni render (refactor de tipos puro).
3. Corregir H-01 Axioma 3 en `academy.py:5325-5339` (sede del actor, Query param solo para permisos globales) + test anti-fuga.

**P0 — TKT-CMS-B (Puck + prod restante):**
1. `ab-testing/page.tsx` (5 fail-unknown) y `MediaPicker.tsx` (`MediaItem`) → 0 any prod total en CMS.
2. Re-ejecutar suite completa (tsc, eslint, vitest) y desplegar.

**P1 — TKT-CMS-C (Tests tipados, ~2 días):**
1. Builders de fixture (`makeDbSection`, `Partial<PuckProps>`) y migración de los ~67 any de tests en 9 archivos (AutoSave, EmpiricalChallenge, PuckSchemaRegistration, pages_r1_r6, AiField, GalleryCards, page.test, EdgeCases, BuilderSidebar).
2. Meta de cierre: `grep -rn "any" src | grep -vE "anywhere|Company"` = **0 en toda src/**.

**P2 — TKT-CMS-D (Pulido canónico, opcional):**
1. Redirección de las 3 FKs de chat (`models_crm.py:35/57/72`) a `personas.id` (migración reversible).
2. Fly-through visual de los 5 módulos para cerrar verificación de precedencia a nivel 100% de drawers/tokens.

---

## Criterios de aceptación cubiertos

- [x] Documento `docs/AUDITORIA_TRANSVERSAL_AXIOMAS_Y_CMS_20261018.md` con evidencia exacta archivo:línea (Axioma 1: `models_auth.py:48`; Axioma 3: `academy.py:5339` + `cms_v2/sites.py:63-71`; Soft-del: `academy.py:2071` + conteos; Frontend: grep de fetch y AlertDialog = 0).
- [x] Inventario clasificado de los `any` del CMS Builder (142 exactos, por archivo/tipo, con interfaces propuestas: `PuckData`, `DbSection`, `GenericFieldProps`, entidades de listas, `MediaItem`, builders de tests).
- [x] Plan de tickets priorizado P0/P1/P2 para AGY2 (TKT-CMS-A..D).
- [x] Commit convencional `docs(cms):` en /root/ccf-freebuff + submit por el puente a agy.
