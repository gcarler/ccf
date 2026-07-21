# Contratos API — Vida Espiritual

## 1. Alcance

Este documento cubre el router `backend/api/spiritual_life.py`, montado en `/api/spiritual-life`.

Reglas base:

- Frontend plataforma usa `apiFetch('/spiritual-life/...')`.
- `spiritual_life` es un módulo autenticado y tenant-scoped por `sede_id`.
- Los hitos espirituales (`SpiritualMilestone`) son registros oficiales de la iglesia sobre una persona.

Referencia RBAC:

- `docs/VIDA_ESPIRITUAL_RBAC_MATRIX.md`

---

## 2. Estado actual de los endpoints

| Método | Ruta | Guard real | Estado |
|---|---|---|---|
| `GET` | `/spiritual-life/milestones/{persona_id}` | `get_current_user` | ✅ Implementado |
| `POST` | `/spiritual-life/milestones` | `require_admin` | ⚠️ Guard incorrecto |

## 3. Endpoints planeados ( backlog )

| Método | Ruta | Guard esperado | Descripción |
|---|---|---|---|
| `GET` | `/spiritual-life/milestones` | `spiritual_life:read` | Listar milestones de la sede del actor |
| `GET` | `/spiritual-life/milestones/{milestone_id}` | `spiritual_life:read` | Detalle de un milestone |
| `PATCH` | `/spiritual-life/milestones/{milestone_id}` | `spiritual_life:edit` | Actualizar milestone |
| `DELETE` | `/spiritual-life/milestones/{milestone_id}` | `spiritual_life:edit` | Soft delete de milestone |
| `GET` | `/spiritual-life/timeline` | `spiritual_life:read` | Timeline propio del actor |
| `GET` | `/spiritual-life/certificates` | `spiritual_life:read` | Alias o proxy a `/academy/me/certificates` |

## 4. CRUD de milestones

### 4.1 Crear milestone

`POST /spiritual-life/milestones`

**Request body (`MilestoneCreate`):**

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `persona_id` | UUID | Sí | Persona a la que se le registra el hito |
| `type` | str | Sí | Tipo de hito (ver catálogo canónico) |
| `event_date` | date | Sí | Fecha del evento |
| `minister_id` | UUID | No | Pastor/ministro que registró el hito |

**Response:** `Milestone`

**Notas:**
- El guard actual es `require_admin` (`system:config`). Debe cambiarse a `spiritual_life:manage`.
- Se debe validar que `persona_id` pertenezca a la sede del actor (Axioma 3).
- Se debe validar que `type` sea uno de los valores canónicos.

### 4.2 Listar milestones de una persona

`GET /spiritual-life/milestones/{persona_id}`

**Parámetros:**

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `persona_id` | UUID (path) | Sí | UUID de la persona |

**Response:** `List[Milestone]`

**Notas:**
- Ordenado por `event_date desc`.
- Excluye registros con `deleted_at IS NOT NULL`.
- Valida que la persona pertenezca a la sede del actor (devuelve 403 si no).

### 4.3 Actualizar milestone

`PATCH /spiritual-life/milestones/{milestone_id}`

**Request body:**

| Campo | Tipo | Requerido | Notas |
|---|---|---|---|
| `type` | str | No | Tipo de hito |
| `event_date` | date | No | Fecha del evento |
| `minister_id` | UUID | No | Pastor/ministro |
| `notes` | str | No | Notas adicionales |

**Response:** `Milestone`

**Notas:**
- Guard esperado: `spiritual_life:edit`.
- Solo se permite editar milestones de la misma sede.

### 4.4 Eliminar milestone

`DELETE /spiritual-life/milestones/{milestone_id}`

**Response:** `204 No Content`

**Notas:**
- Soft delete (set `deleted_at = now()`).
- Guard esperado: `spiritual_life:edit`.

---

## 5. Catálogo canónico de tipos de hitos

Se propone normalizar el campo `type` a los siguientes valores:

| Valor | Label |
|---|---|
| `Decision_Fe` | Decisión de Fe |
| `Bautismo_Aguas` | Bautismo en Aguas |
| `Bautismo_Espiritu` | Bautismo del Espíritu |
| `Persona_Oficial` | Participación Oficial |
| `Liderazgo` | Llamado al Liderazgo |

**Nota:** actualmente el campo es un string libre. La normalización es parte del backlog `SPIRITUAL-API-003`.

---

## 6. Integraciones

### 6.1 Timeline pastoral

`backend/crud/crm_/timeline.py` ya incluye `SpiritualMilestone` en la línea de tiempo de una persona.

### 6.2 Health score

`backend/crud/crm_/health.py` usa los milestones para calcular el puntaje de salud pastoral:

- 10 puntos por milestone, hasta un máximo de 30 puntos.
- Se suma 1 punto adicional si la persona está bautizada (`Persona.is_baptized`).

### 6.3 Certificados

La página de certificados del frontend (`/plataforma/spiritual-life/certificates`) consume `/academy/me/certificates`. No hay endpoint propio de Vida Espiritual para certificados.

---

## 7. Seguridad y tenant

- Axioma 3: un actor solo puede ver/crear/editar milestones de personas de su misma sede.
- Superadmin (`user_sede = None`): ve todo.
- Soft delete universal.
- El guard de creación debe migrar de `require_admin` a `spiritual_life:manage`.
