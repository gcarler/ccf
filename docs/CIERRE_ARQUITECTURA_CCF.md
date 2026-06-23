# Cierre Arquitectonico CCF

**Fecha:** 2026-06-05
**Estado:** Documento de cierre y control de deuda
**Base:** `docs/ARQUITECTURA_IMPECABLE_CCF.md`

---

## 1. Estado Real

La plataforma ya cumple el estado operativo exigido para despliegue:

- `quality_gate.py` pasa en el contexto local de calidad:
  `ENV=test DATABASE_URL=sqlite:///./ccf_dev.db QUALITY_GATE_STEP_TIMEOUT=90 QUALITY_GATE_FRONTEND_TIMEOUT=240 python3 scripts/auditing/quality_gate.py`.
- `npm run typecheck` pasa.
- `tests/test_auth.py` pasa.
- El frontend auditado no conserva `confirm()` / `window.confirm` ni `apiFetch("/api/...")` incorrectos en las superficies revisadas.
- El frontend de plataforma ya no consume `/api/auth/users`, `/api/auth/user-list` ni `/api/academy/users/{user_id}/...`.
- Las rutas de Evangelismo, CRM, Proyectos, Academia y Auth siguen levantando con contratos funcionales.

Esto no significa que no exista deuda. Significa que la deuda restante esta inventariada y ya no bloquea el funcionamiento normal.

---

## 2. Deuda Arquitectonica Restante

La deuda restante esta concentrada en cuatro grupos:

### 2.1 Identidad compat con `users.id`

Persisten FKs compat a `users.id` en modelos que aun conviven con UUID:

- `backend/models_crm.py`
- `backend/models_cms.py`
- `backend/models_academy.py`
- `backend/models_identity.py`
- `backend/models_agents.py`
- `backend/models_governance.py`

Lectura operativa:

- `users.id` sigue siendo compatibilidad de autenticacion.
- No debe crecer como identidad ministerial nueva.
- Toda entidad nueva que represente personas debe apuntar a `personas.id`.

### 2.2 Contratos compat de auth y admin

Siguen vivos contratos que usan `user_id:int`:

- `/api/auth/users/{user_id}`
- `/api/academy/users/{user_id}/enrollments`
- `/api/academy/users/{user_id}/progress`

Saldo cerrado en 2026-06-05:

- la superficie administrativa de usuarios (`/plataforma/admin/users` y detalle) ya consume `/api/admin/users/{user_id}` con `user_id` UUID;
- la superficie administrativa de miembros (`/plataforma/admin/members`) ya lista y actualiza roles via `/api/admin/users`;
- `/api/admin/users/{user_id}` soporta `GET`, `PATCH` y baja por desactivacion (`DELETE` 204);
- `/api/admin/users/{user_id}/permissions` ya resuelve UUID auth y queda como contrato admin vigente, no como deuda `user_id:int`.
- `frontend/src/components/ui/UserSelect.tsx` consume `/api/admin/users` y opera con UUID string.
- Academy frontend consume `/api/academy/me/...` y `/api/academy/personas...`; no quedan consumidores frontend de `/api/academy/users/{user_id}/...`.
- Academy compat tiene dual-write runtime y migracion Alembic de backfill UUID en `20260605_academy_persona_backfill`.
- CRM compat tiene dual-write runtime y migracion Alembic de backfill UUID en `20260605_crm_persona_backfill`.
- CMS autoria/auditoria central tiene dual-write runtime y migracion Alembic de backfill UUID en `20260605_cms_persona_backfill`.
- Agents/Governance tiene columnas UUID paralelas y migracion Alembic de backfill UUID en `20260605_agents_governance_persona_backfill`.
- Las superficies frontend de CMS testimonios y auditoria admin ya usan `author_persona_id` / `actor_persona_id` como identidad principal, con enteros compat solo como fallback visible.

Esto es deuda conocida, no bug activo. Se conserva por compatibilidad hasta completar la migracion por lotes.

### 2.3 Superficies de CMS y auditoria

Hay columnas compat de auditoria y autoria que aun usan `users.id`:

- `created_by`
- `updated_by`
- `author_id`
- `actor_user_id`
- `user_id` en tablas de identidad y notificaciones

Algunas son catalogo interno, otras son realmente identidad. No se deben migrar como bloque.

### 2.4 Tablas transaccionales con PK entera

Siguen existiendo entidades con PK `Integer` por compatibilidad o por diseno legado:

- `donations`
- `consolidation_tasks`
- `user_reminders`
- varias tablas de CMS
- varias tablas de Academy compat

No se migran todas al mismo tiempo. Se priorizan segun si representan identidad, transaccion o catalogo.

---

## 3. Criterio de Clasificacion

### Bloqueante

Rompe login, sede, build, data integrity, health checks o flujos de escritura.

Accion:

- corregir en microcambio;
- probar;
- validar arranque.

### Deuda conocida

Incumple el estado objetivo, pero la compatibilidad sigue activa y el cambio amplio todavia no tiene backfill o redireccion completa.

Accion:

- documentar;
- no tocar sin lote de migracion.

### Compat protegido

Existe para mantener consumidores activos.

Accion:

- no eliminar;
- no renombrar masivamente;
- migrar solo cuando el reemplazo este ya consumido.

---

## 4. Orden de Migracion Recomendado

### Lote 1: Identidad ministerial

Objetivo:

- eliminar `user_id:int` donde represente persona;
- dejar `persona_id:UUID` como contrato canonico.

Incluye:

- auth/admin ministerial;
- academy enrollment/progress;
- audit actor/persona.

### Lote 2: CMS y autoria

Objetivo:

- separar autoria real de compatibilidad compat;
- migrar solo campos que representen persona, no catalogo.

### Lote 3: Transacciones compat

Objetivo:

- revisar `donations`, `consolidation_tasks`, `user_reminders`;
- decidir caso por caso si la PK se mantiene o pasa a UUID.

### Lote 4: Limpieza de alias

Objetivo:

- retirar aliases compat solo cuando frontend, backend y datos ya hablen el mismo contrato.

---

## 5. Regla de Cierre Definitivo

La arquitectura puede declararse cerrada solo cuando se cumpla todo esto:

1. `quality_gate.py` pasa en `/root/ccf`.
2. `npm run typecheck` pasa.
3. `tests/test_auth.py`, `tests/test_smoke.py`, `tests/test_structural_contracts.py` y `tests/test_reglas_plataforma.py` pasan.
4. No quedan nuevas referencias a `apiFetch("/api/...")` en frontend de plataforma.
5. No quedan nuevas confirmaciones nativas en superficies de plataforma.
6. Todo contrato nuevo de persona usa UUID.
7. Cualquier compat restante esta enumerado y atado a un lote de migracion reversible.

---

## 6. Conclusión Operativa

La plataforma ya no esta en estado de inestabilidad funcional. Esta en estado de operacion estable con deuda compat acotada.

La frase correcta no es "ya esta 100% limpia".
La frase correcta es:

> La arquitectura ya es operable, validada y controlada; la deuda restante esta inventariada y puede retirarse por lotes sin poner en riesgo el arranque.
