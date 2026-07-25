# Runbook — Migraciones CRM 20260725_0001/0002/0003

> Deploy-operational runbook para aplicar las 3 migraciones nuevas del módulo
> CRM (auditoría forense de calidad 2026-07-25, sesiones ses_065da89 + ses_06547803).
> DB target: **Postgres de prod** (`DATABASE_URL` configurado en el entorno de
> deploy; **NO** en este dev/test donde `DATABASE_URL` está vacío).

## Resumen

| Migración | Columna | Tabla | Hallazgo | Commit |
|---|---|---|---|---|
| `20260725_0001` | `sede_id` (UUID, FK→sedes.id, indexed) | `crm_automation_flows` | C-04 (data breach cross-tenant) | `30037749` + `7f6e5089` |
| `20260725_0002` | `deleted_at` (TIMESTAMP tz, nullable) | `communication_logs` | QC-02 (soft-delete silenciosamente roto) | `8c2ac1c6` |
| `20260725_0003` | `deleted_at` (TIMESTAMP tz, nullable, indexed) | `support_tickets` + `event_attendances` | QC-06 + QC-07 (idem QC-02 en 2 entidades) | `eed938e3` |

Cadena alembic: `20260724_0001 → 20260725_0001 → 20260725_0002 → 20260725_0003` (head único confirmado).

## Pre-deploy — checks obligatorios

### 1. Backup de las 4 tablas afectadas

```bash
# Como paso defensible, antes de cualquier DDL: snapshot de las tablas.
pg_dump -t crm_automation_flows -t communication_logs -t support_tickets -t event_attendances \
  $DATABASE_URL > /tmp/crm_backup_pre_mig_$(date +%Y%m%d_%H%M).sql
```

### 2. Confirmar estado de partida (head actual = `20260724_0001`)

```bash
cd /root/ccf && source venv/bin/activate
alembic current
# Debe imprimir: 20260724_0001 (head)
```

### 3. Confirmar que no hay flows legacy NULL que necesiten backfill (C-04)

```sql
SELECT COUNT(*) FROM crm_automation_flows WHERE sede_id IS NULL;
```

- Resultado esperado: **0** (verificado previamente por sesión anterior — no hay
  flows pre-migración en prod DB → backfill es no-op).
- Si retorna >0: parar el deploy y ejecutar backfill manual antes:
  ```sql
  -- Asignar a la sede operativa por defecto (ajustar el UUID por contexto).
  UPDATE crm_automation_flows SET sede_id = '<SedeId-Operativa-Por-Defecto>' WHERE sede_id IS NULL;
  ```

## Deploy — execución

### Opción A (recomendada): `alembic upgrade head` directo

```bash
cd /root/ccf && source venv/bin/activate
alembic upgrade head
```

Alembic ejecutará las 3 migraciones en cadena dentro de una transacción.
Si algo falla a mitad, todo se revierte (Postgres DDL transaccional).

### Opción B: dry-run SQL primero, luego live

El DDL exacto de las 3 migraciones está en `docs/RUNBOOK_CRM_MIGRACIONES_20260725.sql`.
Revísalo, y luego ejecuta la Opción A.

## Post-deploy — verificación

```sql
-- 1. Las 4 columnas nuevas están presentes.
SELECT table_name, column_name
FROM information_schema.columns
WHERE (table_name, column_name) IN (
  ('crm_automation_flows', 'sede_id'),
  ('communication_logs',   'deleted_at'),
  ('support_tickets',      'deleted_at'),
  ('event_attendances',    'deleted_at')
);
-- Debe retornar 4 filas.

-- 2. Índices (3 esperados: ix_crm_automation_flows_sede_id,
--    ix_support_tickets_deleted_at, ix_event_attendances_deleted_at).
SELECT indexname FROM pg_indexes
WHERE indexname IN (
  'ix_crm_automation_flows_sede_id',
  'ix_support_tickets_deleted_at',
  'ix_event_attendances_deleted_at'
);
-- Debe retornar 3 filas.

-- 3. FK constraint (solo CrmAutomationFlow.sede_id → sedes.id).
SELECT conname FROM pg_constraint WHERE conname = 'fk_crm_automation_flows_sede_id';
-- Debe retornar 1 fila.

-- 4. alembic_version es head.
SELECT version_num FROM alembic_version;
-- Debe retornar '20260725_0003'.
```

### Smoke post-deploy (opcional pero recomendado)

Tras aplicar, smoke los endpoints que dependen de las columnas nuevas:

- `DELETE /api/crm/messaging/logs/{id}` → `communication_logs.deleted_at` se
  pobla con `now()` → re-`GET` del mismo log retorna 404 (filtrado por
  `get_communication_logs.deleted_at.is_(None)`).
- `DELETE /api/crm/support/tickets/{id}` → idem con `support_tickets.deleted_at`.
- `DELETE /api/crm/events/attendances/{id}` → idem con `event_attendances.deleted_at`.
- `POST /api/crm/automations/flows` → crea con `sede_id` server-side
  (reject si actor sin sede con 409). `GET /api/crm/automations/{id}` desde
  otra sede → 404 (`_owned_flow` doctrina C-04 + QC-09 + QC-11 unificada).

## Rollback — cómo revertir

Las 3 migraciones son reversibles (`downgrade()` definido en cada archivo).
Alembic respeta la cadena:

```bash
# Revertir las 3 (regresa a 20260724_0001):
alembic downgrade 20260724_0001

# Revertir solo la última (0003):
alembic downgrade 20260725_0002

# Revertir solo 0002:
alembic downgrade 20260725_0001
```

El downgrade ejecutará:

- `20260725_0003`: drop `ix_event_attendances_deleted_at` + drop `deleted_at`
  de `event_attendances`; drop `ix_support_tickets_deleted_at` + drop
  `deleted_at` de `support_tickets`.
- `20260725_0002`: drop `deleted_at` de `communication_logs`.
- `20260725_0001`: drop FK + drop index + drop `sede_id` de
  `crm_automation_flows`.

⚠️ **Rollback no recupera los datos soft-deleted después del deploy** —
los `deleted_at` poblados durante la ventana post-mig quedan como NULL otra
vez (movido a "vivo"). Si necesitas preservar la trazabilidad de soft-deletes
hechos durante esa ventana, exporta los registros con `deleted_at IS NOT NULL`
antes del downgrade.

## Riesgos conocidos

1. **Bloqueo de tabla durante `ALTER TABLE ADD COLUMN`**: en Postgres 11+,
   `ADD COLUMN ... DEFAULT NULL` (sin default) es un operation metadata-only
   — NO reescribe la tabla, lock breve en metadata. Como `deleted_at` es
   nullable sin default, no hay rewrite. `sede_id` (nullable sin default en
   `20260725_0001`) idem. Safe en tablas grandes.
2. **FK `crm_automation_flows.sede_id → sedes.id`**: requiere `sedes` table
   existente. Verifica previamente: `SELECT 1 FROM sedes LIMIT 1;`.
3. **Idempotencia**: los helpers `_has_column`/`_has_index` hacen que
   re-ejecutar `alembic upgrade head` sobre una DB ya migrada sea no-op
   (no falla, no duplica columnas/índices).
4. **No tocar SQLite**: los branches `if dialect == "sqlite": return` en
   cada migración hacen que no afecten al test suite (que usa
   `Base.metadata.create_all`, no alembic). Solo importa en prod Postgres.

## Conexión con commits de código

| Commit | Naturaleza | Estado |
|---|---|---|
| `30037749` | C-04 CrmAutomationFlow.sede_id + `_owned_flow` | commited (ses_068040cb) |
| `7f6e5089` | docs tracker C-04 | commited |
| `8c2ac1c6` | QC-01/02/03 (corrección soft-delete CommuncationLog + bulk) | commited |
| `eed938e3` | QC-06..QC-11 (modelos + CRUDs + health) | commited |
| `27c04200` | QC-04/05/12/13 (tests) | commited |
| `68514736` | tracker QC-04..QC-13 hashes | commited |
| `95171137` | feat design DSTable column visibility + row selection (frontend) | commited |
| `c5bc9adb` | feat crm/pipeline bulk-delete + column visibility (frontend) | commited |

Toda la base de código migrada está commiteada en `main`. Las migraciones
alembic en `alembic/canonical_versions/` están listas para deploy.

## Post-deploy smoke del backend runtime

```bash
# Smoke mínimo CRM (sólo lectura–seguro para prod):
cd /root/ccf && source venv/bin/activate
python scripts/test_crm_quality.py
# Esperado: 2 passed, 0 failed (smoke + RBAC HTTP)

# Smoke backend HTTP si la app está corriendo:
curl -f http://127.0.0.1:8000/healthz
# Debe responder OK.
```

## Lecturas auxiliares

- `docs/PLAN_CRM_CALIDAD.md` §7 — cierre auditoría forense 2026-07-25
- `docs/ESTADO_CRM.md` §18 — cierre de C-04 + estado de postgres prod
- `errorescrm.md` — tracker con filas QC-01..QC-13 (40 hallazgos, 30 ✅ + 10 🟢)
- `docs/RUNBOOK_CRM_MIGRACIONES_20260725.sql` — DDL estático de las 3 migraciones
