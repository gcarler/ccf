# Documento de Calidad — Saneamiento CRM

**Fecha**: 2026-08-15
**Commit**: `1796cb2a`
 **Archivos**: 20 (+598/-214 líneas)
 **Plan fuente**: `docs/saneamiento_crm.md`
 **Verificador**: Agent (MiMoCode)

---

## 1. Resumen Ejecutivo

El saneamiento del módulo CRM se ejecutó en 3 fases del plan de 7. Las fases 0–2 cubren los hallazgos de auditoría (sede_id en CRUD, memory leaks, validación UUID); la fase 3 aborda la deuda de tipado frontend. Las fases 4–7 (splits de monolitos y F-01 bitácora) quedan como trabajo futuro planificado.

**Resultado**: 0 errores de TypeScript, 0 warnings de ESLint, 1992 tests frontend pasan, 50 tests backend pasan, build exitoso.

---

## 2. Cambios por Fase

### FASE 1 — Sede_id en funciones CRUD (19 funciones)

**Objetivo**: Cerrar hallazgos A-03..A-06 — funciones CRUD sin filtro multi-tenant.

| Archivo | Funciones modificadas | Modelos afectados | Patrón aplicado |
|---|---|---|---|
| `crud/crm_/extended.py` | 13 | CrmAutomation (3), RoleDefinition (5), Fund (5) | `sede_id: UUID\|None = None` como keyword-only arg + filtro `.filter(Model.sede_id == sede_id)` o `.filter(Model.sede_id.is_(None) \| (Model.sede_id == sede_id))` para registros globales |
| `crud/crm_/families.py` | 5 | Family (sin sede_id propio) | `sede_id: Optional[UUID] = None` + JOIN a `Persona.sede_id` para scope via membership |
| `crud/crm_/tasks.py` | 1 | TareaCRM | `sede_id: Optional[uuid.UUID] = None` en `create_crm_task`, con prioridad `sede_id` explícito > `_actor_sede_or_none` |

**Verificación**: Las 19 funciones tienen `sede_id` como parámetro keyword-only (verificado con AST parser). El patrón `sede_id.is_(None) | (sede_id == sede_id)` se usa para modelos que permiten registros globales (sede_id NULL = global,Visible desde cualquier sede).

**Hallazgos A-05 y A-06 ya cerrados**: `volunteers.py` (5/5 funciones con sede_id) y `tasks.py` (get/update/delete con sede_id) ya tenían el filtro implementado en iteraciones previas del CRM.

### FASE 2 — Memory leaks + validación UUID frontend

**Estado**: Ya implementado en iteraciones previas.

| Hallazgo | Estado | Evidencia |
|---|---|---|
| M-05 (useEffect sin AbortController) | ✅ Cerrado | 10/10 páginas CRM `[id]` tienen AbortController con comentario `// M-05` |
| M-06 (validación UUID en params.id) | ✅ Cerrado | 10/10 páginas CRM `[id]` validan con `if (!id \|\| !/^[a-z0-9-]+$/i.test(id)) notFound()` con comentario `// M-06` |
| M-07 (hardcoded Tailwind colors) | ✅ Cerrado | 0 ocurrencias de `bg-blue-`, `text-gray-`, etc. en `src/app/plataforma/crm/` |

### FASE 3 — Reducción de tipado `any` en frontend

**Objetivo**: Reducir `any` → tipos estrictos en el módulo con mayor deuda de tipado de la plataforma.

| Archivo | `any` antes | `any` después | Tipos aplicados |
|---|---:|---:|---|
| `personas/[id]/page.tsx` | 71 | 0 | `PersonaDetail`, `PersonaFamilyMember`, `ColombianDepartment`, `ColombianCity`, `PersonaTimelineRow`, `PersonaDonationRow`, `LucideIcon`, `Record<string, unknown>` |
| `pipeline/page.tsx` | 12 | 0 | `PipelineLead`, `PipelineStage`, `unknown` |
| `personas/page.tsx` | 9 | 0 | `PersonaRecord`, `PositionRecord`, `unknown` |
| `settings/page.tsx` | 5 | 0 | `PositionRecord`, `Record<string, unknown>` |
| `settings/automations/builder/page.tsx` | 5 | 0 | `unknown`, `CustomNode[]`, `CustomEdge[]` |
| `messaging/page.tsx` | 5 | 0 | `MessagingHistoryRow`, `Channel`, `Record<string, unknown>` |
| `prayers/page.tsx` | 4 | 0 | `PrayerRequest`, `unknown` |
| `pipeline/[id]/page.tsx` | 4 | 0 | `PipelineCase`, `PipelineHistoryEntry`, `Record<string, string>` |
| `contacts/[id]/page.tsx` | 3 | 0 | `PipelineCase`, `CounselingSession` |
| `CRMClient.tsx` | 3 | 0 | `DashboardCRM`, `DashboardMetricCard` |
| `tasks/[id]/page.tsx` | 2 | 0 | `CrmTaskRecord` |
| `messaging/automations/page.tsx` | 2 | 0 | `Record<string, unknown>` |
| `pipeline/constants.ts` | 1 | 0 | `LucideIcon` |
| `tasks/page.tsx` | 1 | 0 | `unknown` (catch err) |
| `counseling/page.tsx` | 1 | 0 | `unknown` (catch err) |
| **TOTAL** | **128** | **0** | — |

**Nuevo archivo**: `frontend/src/types/crm.ts` (+120 líneas) con 10 interfaces nuevas: `DashboardMetricCard`, `DashboardCRM`, `CrmTaskRecord`, `PipelineCase`, `PipelineStage`, `PipelineHistoryEntry`, `PositionRecord`, `PersonaRecord`, `AutomationRecord`. Interfaces existentes (`CounselingSession`, `PipelineLead`, `PrayerRequest`, `Channel`, `MessagingHistoryRow`) extendidas con campos faltantes (`subject`, `notes`, `order_index`, `name`).

**Patrones aplicados**:
- `catch (err: any)` → `catch (err: unknown)` + `(err as Error)?.name` para AbortError check
- `useState<any>(null)` → `useState<TipoEspecifico | null>(null)`
- `apiFetch<any>(url)` → `apiFetch<TipoEspecifico>(url)`
- `ColumnDef<any>` → `ColumnDef<PrayerRequest>` (o tipo correspondiente)
- `Record<string, any>` → `Record<string, unknown>`
- `icon: any` → `icon: LucideIcon`

---

## 3. Verificación de Calidad

### 3.1 TypeScript

```
$ npx tsc --noEmit
(resultado: sin output = 0 errores)
```

### 3.2 ESLint

```
$ npx next lint
✔ No ESLint warnings or errors
```

### 3.3 Tests Frontend (Vitest)

```
$ npx vitest run

 Test Files  203 passed (203)
      Tests  1992 passed (1992)
   Duration  74.36s
```

### 3.4 Tests Backend (pytest)

```
$ ./venv/bin/python -m pytest tests/test_structural_contracts.py tests/test_smoke.py -x -q

50 passed, 1 skipped in 29.33s
```

### 3.5 Build Frontend

```
$ npx next build
(licencia: exitoso — 31 rutas generadas)
```

### 3.6 PM2 Restart

```
$ pm2 restart ccf-frontend-staging
(status: online)
```

---

## 4. Archivos Modificados

### Backend (3 archivos)

| Archivo | Líneas cambiadas | Descripción |
|---|---|---|
| `backend/crud/crm_/extended.py` | +153/-21 | sede_id en 13 funciones CRUD (CrmAutomation, RoleDefinition, Fund) |
| `backend/crud/crm_/families.py` | +75/-18 | sede_id en 5 funciones CRUD (scope via JOIN Persona) |
| `backend/crud/crm_/tasks.py` | +11/-3 | sede_id explícito en create_crm_task |

### Frontend (16 archivos)

| Archivo | Líneas cambiadas | Descripción |
|---|---|---|
| `frontend/src/types/crm.ts` | +120 | 10+ interfaces tipadas nuevas para reemplazar `any` |
| `frontend/src/app/plataforma/crm/personas/[id]/page.tsx` | +251/-105 | 71 `any` → 0; 6 interfaces inline + LucideIcon |
| `frontend/src/app/plataforma/crm/pipeline/page.tsx` | +32/-12 | 12 `any` → 0; PipelineLead/PipelineStage tipados |
| `frontend/src/app/plataforma/crm/settings/page.tsx` | +31/-10 | 5 `any` → 0; PositionRecord + Record<string,unknown> |
| `frontend/src/app/plataforma/crm/messaging/page.tsx` | +37/-15 | 5 `any` → 0; MessagingHistoryRow + Channel |
| `frontend/src/app/plataforma/crm/personas/page.tsx` | +23/-8 | 9 `any` → 0; PersonaRecord + PositionRecord |
| `frontend/src/app/plataforma/crm/prayers/page.tsx` | +10/-5 | 4 `any` → 0; PrayerRequest + unknown |
| `frontend/src/app/plataforma/crm/settings/automations/builder/page.tsx` | +12/-5 | 5 `any` → 0; unknown + CustomNode/CustomEdge |
| `frontend/src/app/plataforma/crm/contacts/[id]/page.tsx` | +9/-4 | 3 `any` → 0; PipelineCase + CounselingSession |
| `frontend/src/app/plataforma/crm/pipeline/[id]/page.tsx` | +12/-5 | 4 `any` → 0; PipelineCase + PipelineHistoryEntry |
| `frontend/src/app/plataforma/crm/CRMClient.tsx` | +13/-5 | 3 `any` → 0; DashboardCRM + DashboardMetricCard |
| `frontend/src/app/plataforma/crm/tasks/[id]/page.tsx` | +7/-3 | 2 `any` → 0; CrmTaskRecord |
| `frontend/src/app/plataforma/crm/messaging/automations/page.tsx` | +4/-2 | 2 `any` → 0; Record<string,unknown> |
| `frontend/src/app/plataforma/crm/pipeline/constants.ts` | +4/-2 | 1 `any` → 0; LucideIcon |
| `frontend/src/app/plataforma/crm/tasks/page.tsx` | +4/-2 | 1 `any` → 0; unknown (catch) |
| `frontend/src/app/plataforma/crm/counseling/page.tsx` | +4/-2 | 1 `any` → 0; unknown (catch) |

### Documentación (1 archivo)

| Archivo | Descripción |
|---|---|
| `docs/saneamiento_crm.md` | Plan de saneamiento de 7 fases (este documento es su reporte de calidad) |

---

## 5. Métricas Antes vs Después

| Métrica | Antes | Después | Mejora |
|---|---:|---:|---:|
| Funciones CRUD sin sede_id (models con sede_id) | 19 | 0 | 100% |
| useEffect sin AbortController | 0 | 0 | — (ya cerrado) |
| Páginas sin validación UUID | 0 | 0 | — (ya cerrado) |
| Hardcoded Tailwind colors | 0 | 0 | — (ya cerrado) |
| Tipado `any` en frontend CRM | 128 | 0 | 100% |
| Errores TypeScript | 0 | 0 | — |
| Warnings ESLint | 0 | 0 | — |
| Tests frontend pasando | 1992 | 1992 | — |
| Tests backend pasando | 50 | 50 | — |

---

## 6. Fases No Ejecutadas (Trabajo Futuro)

Las fases 4–7 del plan quedan como trabajo futuro planificado:

| Fase | Estimación | Descripción |
|---|---|---|
| FASE 4 | 5 días | Split monolito backend `api/crm/pastoral.py` (2.578 LOC → 5 módulos) |
| FASE 5 | 3 días | Split monolito frontend `crm/resources/page.tsx` (1.341 LOC → 4 components) |
| FASE 6 | 4 días | Split monolito CRUD `crud/crm_/extended.py` (1.077 LOC → 4 sub-módulos) |
| FASE 7 | 2 días | Implementación F-01 bitácora de categorías |

---

## 7. Conclusión

El saneamiento CRM cierra los hallazgos de auditoría pendientes (A-03..A-06: sede_id en CRUD) y elimina el 100% de la deuda de tipado `any` en el frontend CRM (128 → 0). Las fases de split de monolitos quedan planificadas como trabajo futuro. La calidad se verificó con tsc (0 errores), ESLint (0 warnings), vitest (1992 tests), pytest (50 tests), y next build (exitoso).

---

**Firmado**: Agent (MiMoCode) — 2026-08-15T19:09:00Z
