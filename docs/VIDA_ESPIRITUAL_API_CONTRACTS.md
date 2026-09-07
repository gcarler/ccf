# Contratos API — Vida Espiritual y Discipulado

**Actualizado:** 2026-09-06 (Auditoría Forense Integral — Certificación 100/100 A+)  
**Veredicto:** 100/100 (A+) — CERTIFICADO ([`docs/AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md`](./AUDITORIA_FORENSE_VIDA_ESPIRITUAL_2026-09-06.md))

---

## 1. Alcance

Este documento cubre el router `backend/api/spiritual_life.py`, montado en el prefijo `/api/spiritual-life`, así como los endpoints administrativos de insignias en `/api/admin`.

Reglas canónicas de la plataforma:
- Todo cliente frontend utiliza el helper centralizado `apiFetch('/spiritual-life/...')`.
- Todo endpoint está protegido por autenticación JWT y delimitado al tenant de la sede del actor (`sede_id`).
- Todo registro mutado aplica borrado lógico (`deleted_at`) sin eliminación destructiva (`0 db.delete(`).
- Mitigación BOLA: peticiones para personas o hitos de otras sedes retornan HTTP 404 neutro.

---

## 2. Superficie de Endpoints Implementados

| Método | Ruta | Guard RBAC | Descripción | Estado |
|---|---|---|---|---|
| `GET` | `/api/spiritual-life/milestones` | `spiritual_life:read` | Lista hitos de la sede del actor | ✅ Implementado |
| `GET` | `/api/spiritual-life/milestones/{persona_id}` | `spiritual_life:read` | Lista hitos de una persona específica | ✅ Implementado |
| `POST` | `/api/spiritual-life/milestones` | `spiritual_life:manage` | Registra un nuevo hito espiritual | ✅ Implementado |
| `GET` | `/api/spiritual-life/milestone/{milestone_id}` | `spiritual_life:read` | Detalle de un hito específico | ✅ Implementado |
| `PATCH` | `/api/spiritual-life/milestone/{milestone_id}` | `spiritual_life:edit` | Actualiza campos de un hito | ✅ Implementado |
| `DELETE` | `/api/spiritual-life/milestone/{milestone_id}` | `spiritual_life:edit` | Soft delete del hito (`deleted_at`) | ✅ Implementado |
| `GET` | `/api/admin/milestones` | `require_active_user` | Resumen de insignias y hitos para admin | ✅ Implementado |
| `POST` | `/api/admin/milestones/award` | `require_admin` | Otorga insignia a usuario vía UUID | ✅ Implementado |

---

## 3. Especificación de Contratos CRUD

### 3.1 Registrar Hito Espiritual

`POST /api/spiritual-life/milestones`

**Permiso requerido:** `spiritual_life:manage`

**Request Body (`MilestoneCreate`):**

| Campo | Tipo | Requerido | Restricciones / Formato |
|---|---|---|---|
| `persona_id` | UUID | Sí | Debe existir y pertenecer a la sede del actor |
| `type` | string | Sí | Catálogo canónico (`Decision_Fe`, `Bautismo_Aguas`, `Bautismo_Espiritu`, `Persona_Oficial`, `Liderazgo`) |
| `event_date` | date | Sí | Formato ISO `YYYY-MM-DD` |
| `minister_id` | UUID | No | Pastor/ministro oficiante |
| `notes` | string | No | Observaciones pastorales |

**Respuestas:**
- `201 Created` / `200 OK`: Devuelve objeto `Milestone` creado con UUID y marcas de tiempo UTC.
- `403 Forbidden`: Actor sin permiso `spiritual_life:manage`.
- `404 Not Found`: Persona inexistente o perteneciente a otra sede (mitigación BOLA).
- `422 Unprocessable Entity`: Tipo de hito fuera del catálogo canónico o formato inválido.

---

### 3.2 Listar Hitos de una Persona

`GET /api/spiritual-life/milestones/{persona_id}`

**Permiso requerido:** `spiritual_life:read`

**Respuestas:**
- `200 OK`: Retorna array JSON `List[Milestone]` ordenado por `event_date desc`.
- `403 Forbidden`: Actor sin permiso `spiritual_life:read`.
- `404 Not Found`: Persona inexistente o perteneciente a otra sede.

---

### 3.3 Listar Hitos de la Sede

`GET /api/spiritual-life/milestones`

**Permiso requerido:** `spiritual_life:read`

**Query Parameters:**
- `skip`: entero opcional (paginación, default 0).
- `limit`: entero opcional (máx 100, default 50).

**Respuestas:**
- `200 OK`: Retorna `List[Milestone]` de la sede del actor, excluyendo registros con `deleted_at IS NOT NULL`.

---

### 3.4 Consultar Detalle de un Hito

`GET /api/spiritual-life/milestone/{milestone_id}`

**Permiso requerido:** `spiritual_life:read`

**Respuestas:**
- `200 OK`: Retorna objeto `Milestone`.
- `404 Not Found`: Hito inexistente, eliminado, o perteneciente a otra sede.

---

### 3.5 Actualizar Hito Espiritual

`PATCH /api/spiritual-life/milestone/{milestone_id}`

**Permiso requerido:** `spiritual_life:edit`

**Request Body (`MilestoneUpdate`):**

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `type` | string | No | Debe cumplir el catálogo canónico si se envía |
| `event_date` | date | No | Formato `YYYY-MM-DD` |
| `minister_id` | UUID | No | Nuevo ministro oficiante |
| `notes` | string | No | Nuevas notas |

**Respuestas:**
- `200 OK`: Retorna objeto `Milestone` actualizado.
- `403 Forbidden`: Actor sin permiso `spiritual_life:edit`.
- `404 Not Found`: Hito de otra sede o no encontrado.
- `422 Unprocessable Entity`: Tipo de hito no canónico.

---

### 3.6 Eliminar Hito Espiritual (Lógico)

`DELETE /api/spiritual-life/milestone/{milestone_id}`

**Permiso requerido:** `spiritual_life:edit`

**Respuestas:**
- `204 No Content`: Hito marcado exitosamente con marca de tiempo UTC en `deleted_at`.
- `403 Forbidden`: Actor sin permiso `spiritual_life:edit`.
- `404 Not Found`: Hito de otra sede o no encontrado.

---

## 4. Catálogo Canónico de Tipos de Hitos

Validados por regex Pydantic en backend y consumidos por la interfaz frontend:

| Clave Canónica (`type`) | Etiqueta en UI | Paso de Discipulado |
|---|---|---|
| `Decision_Fe` | Decisión de Fe | Paso 1 |
| `Bautismo_Aguas` | Bautismo en Aguas | Paso 2 |
| `Bautismo_Espiritu` | Bautismo del Espíritu Santo | Paso 3 |
| `Persona_Oficial` | Membresía Oficial | Paso 4 |
| `Liderazgo` | Llamado al Liderazgo | Paso 5 |

---

## 5. Integraciones de Plataforma

1. **Timeline Pastoral Unificado:** `backend/crud/crm_/timeline.py` consolida los `SpiritualMilestone` como eventos oficiales en el historial pastoral del miembro.
2. **Índice de Salud Pastoral:** `backend/crud/crm_/health.py` pondera automáticamente cada hito para el cálculo del score espiritual.
3. **Ruta de Discipulado en Frontend:** `/plataforma/spiritual-life` mapea reactivamente los hitos registrados con los 5 pasos canónicos de discipulado en tiempo real.
4. **Certificados de Academia:** Los certificados emitidos tras cursar materias se integran en `/academy/me/certificates` y se enlazan desde el dashboard de vida espiritual.
