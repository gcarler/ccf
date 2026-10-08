# Auditoría del Módulo CRM — 07/10/2026

**Alcance:** `backend/api/crm/*` (pastoral, pipelines, resources, personas, relations), `backend/api/messaging.py`, `backend/api/donations.py`, `backend/api/prayer.py`, `backend/crud/crm_/*` (21 módulos, ~12.200 líneas backend) y `/plataforma/crm` (44 archivos frontend).
**Método:** Auditoría estática de código + verificación de reglas canónicas CCF + ejecución dinámica de suites de pruebas (seguridad, aislamiento, contratos, adversariales) y linters.

---

## 1. Resumen Ejecutivo

El CRM es el módulo más blindado de la plataforma (179 dependencias de seguridad verificadas, redacción de campos sensibles por rol, E2EE en consejería, aislamiento por sede consistente en ~100 puntos). Sin embargo, la auditoría detectó **1 fallo activo de suite** producto de un drift de contrato en la redacción de notas de consejería (datos ultra-sensibles) introducido por el commit `6817828d` sin actualizar el test canónico, además de una zona de tipado débil (22 endpoints con `payload: dict` sin esquema Pydantic) y deuda estructural.

| Severidad | Cantidad | Hallazgos |
|-----------|----------|-----------|
| 🔴 Crítico | 1 | Drift de contrato en redacción de notas de consejería (test fallando en main) |
| 🟠 Alto | 2 | 22 endpoints sin esquema Pydantic; monolito `pastoral.py` (2.612 líneas) |
| 🟡 Medio | 3 | Frontera difusa CRM/Finanzas en donaciones; huérfanos de sede en prayer; placeholders de redacción no unificados |

---

## 2. Verificación de Reglas Canónicas (Resultado)

### 2.1 Backend (FastAPI + SQLAlchemy)

| Regla | Resultado | Evidencia |
|-------|-----------|-----------|
| Guards de permisos | ✅ Cumple | 179 dependencias `require_*` en `backend/api/crm/`: `require_module_access("crm", read/edit)` en pastoral/personas/relations/resources, `require_pastor_or_admin` en pipelines (administración de pipelines), `require_admin` en recursos sensibles, `require_staff_or_admin` en logs de mensajería, `require_permission("profile:manage")` en autoservicio. |
| Axioma 3 (sede del actor, nunca del cliente) | ✅ Cumple | ~100 puntos de resolución de sede vía `get_user_sede_id` / `require_user_sede_id(db, current_user)` (ej. `pastoral.py:144-151` con coerción UUID documentada, `pipelines.py:29`, `_shared.py`). **0** parámetros `sede_id` del cliente en `Query`. CommunicationLog se filtra por JOIN a `Persona.sede_id` (`messaging.py:499-505`). |
| Axioma 1 (Kernel de Personas) | ✅ Cumple | Toda referencia humana usa FK a `personas.id`. Cero tablas paralelas. |
| Fechas UTC | ✅ Cumple | **0** usos de `datetime.utcnow()` naive en `api/crm/` y `crud/crm_`. |
| Borrado físico | ✅ Cumple | **0** llamadas `db.delete(` en `crud/crm_/` y `api/crm/`. Soft delete con `deleted_at = _utcnow()` en todos los deletes de la capa CRUD. |
| Soft deletes | ✅ Cumple | 21 módulos CRUD con patrón `row.deleted_at` + filtros `is_(None)` en lecturas. |
| Redacción de datos sensibles | ⚠️ Parcial | `schemas/crm/base.py`: `restrict_crm_fields` enmascara `pastoral_notes`/`spiritual_health`/`talents`/`spiritual_gifts` para roles no privilegiados (líneas 652-661); `restrict_counseling_notes` redacta notas (líneas 225-237) — pero con drift de contrato → **F-01**. |
| Cifrado de consejería | ✅ Cumple | `api/crm/counseling_crypto.py` (E2EE simétrico de notas confidenciales) con suite propia `test_crm_counseling_e2ee.py` en verde. |

### 2.2 Frontend (Next.js 15 + React 19)

| Regla | Resultado | Evidencia |
|-------|-----------|-----------|
| `apiFetch` obligatorio | ✅ Cumple | 151 llamadas vía `apiFetch`; **0** usos de `fetch()` crudo en `/plataforma/crm`. |
| Tokens semánticos | ✅ Cumple | **0** clases de color Tailwind hardcodeadas en los 44 archivos del módulo. |
| Drawers, NO modals | ✅ Cumple | **0** usos de `AlertDialog`, `window.confirm`, `alert()` (los flujos destructivos de `crm/pipeline` y `crm/messaging/automations` señalados en la auditoría del 2026-09-28 fueron migrados). |
| Rutas `/plataforma/...` | ✅ Cumple | Todas las páginas bajo `src/app/plataforma/crm/`. |
| TypeScript estricto | ✅ Cumple | **0** usos de `: any` / `as any` en código no-test del módulo. |
| Estados de UI | ✅ Cumple | `loading.tsx` y `error.tsx` dedicados a nivel de segmento. |

### 2.3 Ejecución Dinámica (evidencia cuantitativa)

| Suite | Resultado |
|-------|-----------|
| Seguridad y aislamiento: `test_crm_sede_isolation.py`, `test_crm_sede_isolation_entities.py`, `test_crm_rbac_http.py`, `test_messaging_sede_isolation.py`, `test_messaging_security_gaps.py` | ✅ Verdes |
| Cobertura extendida `test_crm_extended_coverage.py` | ✅ Verde |
| API/contratos: `test_crm_api_pastoral.py`, `test_crm_api_personas.py`, `test_crm_api_resources.py`, `test_crm_pipeline_contract.py`, `test_crm_counseling_e2ee.py`, `test_donations_api.py`, `test_messaging_api.py` | ✅ Verdes |
| Adversariales: `test_crm_challenger_adversarial.py`, `test_crm_concurrency_adversarial.py`, `test_crm_pastoral_comprehensive.py`, `test_crm_runtime_security.py` | ✅ **34 passed** |
| **Redacción de schemas `test_crm_schema_redaction.py`** | 🔴 **1 FAILED** (`test_non_privileged_role_gets_redacted_notes`) — ver F-01 |
| `npx eslint` (CRM frontend, `--max-warnings 0`) | ✅ 0 errores, 0 warnings |

**Total verificado en esta auditoría: 313 passed / 1 failed.** La suite completa del repo contiene 80+ archivos de test CRM.

---

## 3. Hallazgos Detallados

### 🔴 F-01 (CRÍTICO) Drift de contrato en redacción de notas de consejería — test fallando

**Archivos:** `backend/schemas/crm/base.py:225-237` vs `tests/test_crm_schema_redaction.py:42`

**Evidencia de ejecución:**

```
AssertionError: failed for role=lector
  assert 'Contenido co...ial protegido' == '[RESTRINGIDO - SOLO PASTORES/ADMIN]'
```

**Origen (git):** El commit `6817828d` (`feat(crm): cifrado simetrico de notas de consejeria pastoral confidencial`, 2026-10-01) modificó el placeholder de redacción en `restrict_counseling_notes`:

```diff
-            self.notes = "[RESTRINGIDO - SOLO PASTORES/ADMIN]"
+            self.notes = "Contenido confidencial protegido"
+            self.notas = "Contenido confidencial protegido"
```

…sin actualizar el test canónico `test_crm_schema_redaction.py`, que sigue esperando el placeholder original. Consecuencias:

1. **El gate `crm-tests` de CI debería estar roto** (`ci.yml:264` ejecuta `pytest tests/test_crm_*.py`), o el commit entró sin pasar CI — en cualquiera de los dos casos hay una brecha de proceso sobre el módulo de datos más sensibles de la plataforma.
2. El placeholder actual es indistinguible en forma de un contenido real (no lleva marca de restricción explícita tipo `[RESTRINGIDO]`), degradando la señal auditiva del redactor para el rol no privilegiado.

**Nota positiva:** el mecanismo de contexto sí funciona — `user_role_context` se popula por request en `core/permissions.py:590` y la redacción se aplica cuando el rol viene seteado.

**Remediación sugerida:** Decidir el placeholder canónico (recomiendo `[RESTRINGIDO - SOLO PASTORES/ADMIN]`, coherente con `restrict_crm_fields` que usa `[RESTRINGIDO]`), corregir el que esté mal, y ejecutar el gate `crm-tests` completo antes del próximo merge.

---

### 🟠 F-02 (ALTO) 22 endpoints de pipelines sin esquema Pydantic (`payload: dict = None`)

**Archivo:** `backend/api/crm/pipelines.py` (líneas 1072, 1194, 1204, 1229, 1244, 1281, 1423, y 15 más)

```python
@router.post("/automations/branching/null-vars")
def branching_null_vars(payload: dict = None, current_user: models.User = Depends(...)):
    payload = payload or {}
    variables = payload.get("variables", {})
```

**Problema:** Viola la regla de tipado estricto y el patrón del módulo (`extra="forbid"` en schemas). Cualquier campo extra pasa silenciosamente; no hay validación de tipos ni límites. Mitigante: son endpoints validadores de branching de automatizaciones, sin efectos de escritura sobre entidades, y protegidos con `require_module_access("crm", "edit")`.

**Remediación sugerida:** Crear schemas Pydantic (`BranchingVariablesRequest`, etc.) con `extra="forbid"`, siguiendo la doctrina fix-position ya aplicada en QC-04 (errorescrm.md).

---

### 🟠 F-03 (ALTO) `pastoral.py` es un monolito de 2.612 líneas con 64 funciones

**Archivo:** `backend/api/crm/pastoral.py`

Coincide con la observación histórica de `QUALITY_REVIEW.md` sobre archivos monolíticos en `backend/api/`. Concentra personas, salud espiritual, mentoría, consejería, comunidad y notificaciones en un solo router. Riesgo de mantenimiento y de merge conflicts (ya muestra fricción: los últimos commits CRM tocaron este archivo repetidamente).

**Remediación sugerida:** Split incremental en subrouters (`pastoral_personas`, `pastoral_counseling`, `pastoral_community`, …) respetando el patrón ya usado por evangelismo (`evangelism_events/`, `evangelism_grupos/`).

---

### 🟡 F-04 (MEDIO) Frontera difusa CRM/Finanzas en donaciones

**Archivos:** `backend/api/donations.py` (guard `require_module_access("finance", ...)` / `require_admin`) vs `backend/crud/crm_/donations.py`

El endpoint de donaciones vive en la raíz de `api/` con permisos de **finanzas**, mientras el CRUD de donaciones vive en el paquete **CRM**. Dos sistemas de permisos apuntando al mismo dominio funcional crean ambigüedad sobre qué rol debería acceder y facilita futuras divergencias de scoping.

**Remediación sugerida:** Definir la frontera (donaciones = Finanzas, o = CRM) y mover endpoint/CRUD al paquete correspondiente con un solo guard canónico.

---

### 🟡 F-05 (MEDIO) Posibles filas huérfanas de sede en `POST /prayer`

**Archivo:** `backend/api/prayer.py:15-28`

```python
row = crud.create_prayer_request(db, payload=request)
if sede_id and not row.sede_id:
    row.sede_id = sede_id
    db.commit()
```

Si el actor no tiene sede (`sede_id is None`, p. ej. superadmin), la fila se persiste con `sede_id NULL` y resulta **invisible para siempre** en el listado `GET /prayer` (que filtra `PrayerRequest.sede_id == sede_id`). Además se realizan dos commits por creación (flush implícito + commit + commit).

**Remediación sugerida:** Asignar `sede_id` dentro de la creación (antes del flush) y rechazar con 409 la creación sin sede si la entidad es tenant-scoped, siguiendo el patrón del resto del módulo.

---

### 🟡 F-06 (MEDIO) Placeholders de redacción no unificados

**Archivos:** `backend/schemas/crm/base.py:659-663` (`"[RESTRINGIDO]"`) vs `:230-232` (`"Contenido confidencial protegido"` vs contrato `"[RESTRINGIDO - SOLO PASTORES/ADMIN]"`)

Tres convenciones de redacción conviven. El frontend que quiera detectar "campo restringido" no tiene una señal única (`startsWith("[RESTRINGIDO")` fallaría para counseling). Unificar en una constante compartida (ej. `REDACTED = "[RESTRINGIDO...]` en un módulo común) elimina la clase de bug de F-01 de raíz.

---

## 4. Fortalezas Destacadas

1. **Defensa en profundidad RBAC:** redacción a nivel de schema (`model_validator` + `user_role_context`), guards en 179 puntos, y suites dedicadas de RBAC HTTP y aislamiento por sede.
2. **Consejería pastoral con E2EE** (`counseling_crypto.py`) — las notas confidenciales viajan cifradas incluso para la capa de aplicación, con suite de regresión propia.
3. **Aislamiento multi-tenant ejemplar:** `CommunicationLog` sin columna propia de sede se filtra correctamente por JOIN a `Persona.sede_id` (`messaging.py:499-505`); proyectos sin sede (NULL) explícitamente ocultos al scope de sede (`messaging.py:154-157`).
4. **Cultura adversarial:** suites challenger, stress, concurrency y runtime security (34 passed) sobre el módulo.
5. **CI con gate dedicado** `crm-tests` (SQLite + xdist) y linter de organización de imports (`scripts/lint-crm.sh`) — aunque F-01 demuestra que el gate está degradado o fue bypaseado.

---

## 5. Veredicto

| Dimensión | Calificación |
|-----------|--------------|
| Seguridad y RBAC | 🟢 A− (F-01) |
| Aislamiento multi-tenant (Axioma 3) | 🟢 A |
| Integridad de datos y soft deletes | 🟢 A |
| Tipado y contratos de API | 🟡 B− (F-02, F-06) |
| Arquitectura y mantenibilidad | 🟡 B− (F-03, F-04) |
| Frontend (reglas UI/HTTP/TS) | 🟢 A |
| Pruebas automatizadas | 🔴 B (1 test crítico fallando en el gate) |
| **Global** | **A− → con F-01 cerrado y gate CI restaurado, A** |

**Prioridad de remediación:**
1. **Inmediato:** cerrar F-01 (placeholder canónico + test verde + verificar estado del gate `crm-tests` en CI — si el último push pasó con este test roto, hay una brecha de proceso).
2. **Este ciclo:** F-02 y F-06 (tipado de payloads y unificación de placeholders — misma clase de riesgo).
3. **Deuda normal:** F-03, F-04, F-05.

---

*Generado por auditoría automatizada el 07/10/2026. Evidencia: ejecución real de 314 tests CRM (313 passed / 1 failed), ESLint 0/0, análisis estático con rutas y líneas exactas, y trazabilidad git del drift (commit `6817828d`).*
