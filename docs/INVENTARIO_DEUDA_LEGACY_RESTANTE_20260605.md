# Inventario de Deuda Legacy Restante

**Fecha:** 2026-06-05
**Estado:** Inventario posterior a saneamiento frontend/Admin/Academy

---

## 1. Cerrado En Esta Tanda

- `quality_gate.py` ya no se cuelga y pasa con entorno local:
  `ENV=test DATABASE_URL=sqlite:///./ccf_dev.db QUALITY_GATE_STEP_TIMEOUT=90 QUALITY_GATE_FRONTEND_TIMEOUT=240 python3 scripts/auditing/quality_gate.py`.
- Frontend de plataforma ya no consume:
  - `/api/auth/users`;
  - `/api/auth/user-list`;
  - `/api/academy/users/{user_id}/...`.
- `UserSelect` consume `/api/admin/users` y trabaja con UUID string.
- Projects frontend fue alineado a IDs UUID string para proyectos, tareas, owner y assignee.
- Academy tiene contratos nuevos:
  - `/api/academy/me/enrollments`;
  - `/api/academy/me/progress`;
  - `/api/academy/personas`;
  - `/api/academy/personas/{persona_id}/enrollments`;
  - `/api/academy/personas/{persona_id}/progress`.
- Academy legacy ahora resuelve `persona_id` desde `users.id` y hace dual-write runtime en:
  - `enrollments.persona_id`;
  - `lesson_progress.persona_id`;
  - `academy_activity_logs.persona_id`;
  - `formal_actas.closed_by_persona_id`.
- Academy tiene migracion Alembic de backfill UUID:
  - `alembic/versions/20260605_academy_persona_backfill.py`.

---

## 2. Legacy Backend Que Permanece Por Compatibilidad

### Auth v1 / Identity

Archivos:

- `backend/api/auth.py`
- `backend/crud/identity.py`
- `backend/models_identity.py`

Razon:

- Son compatibilidad de autenticacion v1 (`users.id`, tokens, preferencias, medallas).
- No se eliminan hasta retirar auth v1 completo.

Lote:

- Retiro final auth v1 despues de confirmar cero consumidores.

### Academy legacy

Archivos:

- `backend/models_academy.py`
- `backend/crud/academy.py`
- `backend/api/academy.py`

Columnas:

- `enrollments.user_id`
- `lesson_progress.user_id`
- `academy_activity_logs.user_id`
- `formal_actas.closed_by_user_id`

Estado:

- Ya existen columnas UUID paralelas en los modelos principales:
  - `enrollments.persona_id`;
  - `lesson_progress.persona_id`;
  - `academy_activity_logs.persona_id`;
  - `formal_actas.closed_by_persona_id`.
- El runtime ya hace dual-write cuando existe `personas.user_id`.
- Existe migracion fisica de backfill desde `personas.user_id`.
- Falta ejecutar/validar la migracion en staging/produccion y luego dejar de escribir enteros tras un release sin consumidores legacy.

Lote:

- Academy retiro final de escritura legacy tras backfill validado.

### CRM legacy con UUID paralelo

Archivo:

- `backend/models_crm.py`

Columnas legacy:

- `counseling_tickets.pastor_user_id` -> reemplazo `pastor_id`.
- `consolidation_tasks.assignee_user_id` -> reemplazo `assignee_id`.
- `communication_logs.leader_user_id` -> reemplazo `leader_id`.

Estado:

- Ya existe columna UUID paralela.
- El runtime ya hace dual-write cuando recibe identidad legacy:
  - `counseling_tickets.pastor_id`;
  - `consolidation_tasks.assignee_id`;
  - `communication_logs.leader_id`.
- Existe migracion fisica de backfill:
  - `alembic/versions/20260605_crm_persona_backfill.py`.
- Quedan campos `*_user_id` como compatibilidad de lectura durante un release.

Lote:

- CRM retiro final de escritura/lectura legacy tras backfill validado.

### CMS autoria/auditoria

Archivo:

- `backend/models_cms.py`

Columnas:

- `created_by`
- `updated_by`
- `actor_user_id`
- `author_id`

Estado:

- Varias tablas ya tienen `created_by_persona_id` / `updated_by_persona_id`.
- El runtime CMS central ya hace dual-write en media, themes, pages, page versions, publish logs y testimonials.
- Existe migracion fisica de backfill:
  - `alembic/versions/20260605_cms_persona_backfill.py`.
- Las superficies frontend de CMS testimonios ya usan `author_persona_id` como identidad principal.
- Schemas todavia exponen algunos campos enteros como compatibilidad.

Lote:

- CMS retiro final de autoria legacy tras backfill validado.

### Agents/Governance

Archivos:

- `backend/models_agents.py`
- `backend/models_governance.py`
- `backend/services/conversation_memory.py`

Estado:

- `AdminAuditLog` ya resuelve `actor_persona_id` cuando recibe `actor_user_id`.
- Agents tiene columnas UUID paralelas para autoria/transicion:
  - `agents.created_by_persona_id`;
  - `agents.updated_by_persona_id`;
  - `agent_roles.created_by_persona_id`;
  - `agent_journey.triggered_by_persona_id`.
- Conversation memory tiene `agent_conversations.persona_id`.
- Existe migracion fisica de backfill:
  - `alembic/versions/20260605_agents_governance_persona_backfill.py`.
- La superficie frontend de auditoria admin ya usa `actor_persona_id` como identidad principal.

Lote:

- Retiro final de columnas actor/owner legacy tras backfill validado.

---

## 3. PK Enteras Restantes

No toda PK entera es deuda.

Permitidas temporalmente:

- catalogos internos;
- tablas de relacion no expuestas por URL;
- tablas legacy protegidas mientras exista consumidor.

Prioridad de saneamiento:

1. Donaciones: agregar `public_id UUID` antes de tocar PK fisica.
2. Tickets/soporte: agregar `public_id UUID`.
3. Comentarios/adjuntos/activity logs expuestos por API: evaluar `public_id UUID`.
4. Academy forum/progress: migrar despues de `persona_id`.
5. CMS publicable: evaluar por sitio/preview/API externa.

---

## 4. Proxima Migracion Segura

Las migraciones fisicas de identidad/persona para Academy, CRM, CMS y Agents/Governance ya existen.

Recomendacion:

1. Ejecutar migraciones en staging/produccion y validar cero huerfanos.
2. Mantener columnas legacy `users.id` durante un release sin consumidores legacy.
3. Retirar escrituras legacy por dominio.
4. Luego retirar columnas legacy con migraciones de downgrade definido.

No eliminar columnas enteras hasta tener:

- backup;
- Alembic upgrade/downgrade;
- validacion cero huerfanos;
- smoke de Academy/CRM;
- un release sin consumidores legacy.
