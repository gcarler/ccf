-- Dry-run SQL estático: equivalente a `alembic upgrade 20260724_0001:20260725_0003`
-- Módulo CRM — Auditoría forense de calidad 2026-07-25 (ses_065da89 + ses_06547803)
--
-- AVISO: este SQL se generó a partir del código fuente de las 3 migraciones
-- porque `alembic ... --sql` (modo offline) falla en este entorno: las
-- migraciones 0002 y 0003 usan helpers `sa.inspect(op.get_bind())` (ver
-- _has_column / _has_table) que no están disponibles con MockConnection del
-- modo offline. En prod real, los helpers retornan `False` en una DB sana
-- (columnas nuevas no existen todavía) → el `_has_column` guard es `False` →
-- la rama Postgres procede y ejecuta exactamente este DDL.
--
-- COMMITES DE ORIGEN:
--   20260725_0001 → C-04 (auditoría original) commit `30037749` + `7f6e5089`
--   20260725_0002 → QC-02 commit `8c2ac1c6`
--   20260725_0003 → QC-06 + QC-07 commit `eed938e3`
--
-- EJECÚTESE EN PROD dentro de una transacción (alembic wrap automáticamente):
--   cd /root/ccf && source venv/bin/activate && alembic upgrade head
--
-- REVERSIONES (en orden inverso):
--   alembic downgrade 20260724_0001   # revierte las 3 (0003 → 0002 → 0001)
--   alembic downgrade 20260725_0002   # revierte solo 0003
--   alembic downgrade 20260725_0001   # revierte solo 0002

-- ============================================================================
-- Migración 20260725_0001 — crm_automation_flows.sede_id (C-04)
-- ============================================================================
-- Add sede_id to crm_automation_flows (REGLAS.md §4.2: toda UGC con API admin
-- debe tener sede_id; era la única excepción legítima fuera de CMS site-faro).
-- Verificación backfill previa al deploy (sin datos legacy NULL): ver
-- ESTADO_CRM.md §18 + plan_crm_calidad.md §7 — prod DB ya tenía 0 flows pre-mig.

ALTER TABLE crm_automation_flows ADD COLUMN sede_id UUID;

CREATE INDEX ix_crm_automation_flows_sede_id
  ON crm_automation_flows (sede_id);

ALTER TABLE crm_automation_flows
  ADD CONSTRAINT fk_crm_automation_flows_sede_id
  FOREIGN KEY (sede_id) REFERENCES sedes (id);

UPDATE alembic_version
SET version_num = '20260725_0001'
WHERE alembic_version.version_num = '20260724_0001';

-- ============================================================================
-- Migración 20260725_0002 — communication_logs.deleted_at (QC-02)
-- ============================================================================
-- Soft-delete column faltante detectada por auditoría forense. Patrón:
-- CRUD delete_communication_log ya hacía row.deleted_at = _utcnow() pero la
-- columna no existía → Postgres abortaba el commit (column does not exist);
-- SQLite descartaba silenciosamente la asignación ORM. Migración añade la
-- columna para que el soft-delete sea funcional en prod.

ALTER TABLE communication_logs
  ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- No se crea índice en esta migración (la migración 0002 original no lo hace).
-- Patrón hermano: 20260719_0001_crm_events_deleted_at.

UPDATE alembic_version
SET version_num = '20260725_0002'
WHERE alembic_version.version_num = '20260725_0001';

-- ============================================================================
-- Migración 20260725_0003 — support_tickets + event_attendances deleted_at
-- ============================================================================
-- Réplica del patrón QC-02 en 2 entidades más (subagent explore re-audit):
--   - QC-06 SupportTicket.deleted_at en models_crm.py:936
--   - QC-07 EventAttendance.deleted_at en models_crm.py:161
-- Adicionalmente el "_get_*" CRUD ahora filtra deleted_at.is_(None) en
-- reads/updates/deletes + el bypass-CRUD query en health.py:63/78 también.
-- Ambas columnas indexed (la 0003 sí crea índices, a diferencia de 0002).

-- SupportTicket (QC-06)
ALTER TABLE support_tickets
  ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX ix_support_tickets_deleted_at
  ON support_tickets (deleted_at);

-- EventAttendance (QC-07)
ALTER TABLE event_attendances
  ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX ix_event_attendances_deleted_at
  ON event_attendances (deleted_at);

UPDATE alembic_version
SET version_num = '20260725_0003'
WHERE alembic_version.version_num = '20260725_0002';

-- ============================================================================
-- Verificaciones post-deploy (ejecutar manualmente contra prod):
-- ============================================================================
-- Confirmar que las 4 columnas existen:
--   SELECT column_name FROM information_schema.columns
--   WHERE table_name IN ('crm_automation_flows','communication_logs','support_tickets','event_attendances')
--     AND column_name IN ('sede_id','deleted_at');
-- -- Debe retornar 4 filas: sede_id (crm_automation_flows) + deleted_at × 3.
--
-- Confirmar índices:
--   SELECT indexname FROM pg_indexes
--   WHERE tablename IN ('crm_automation_flows','support_tickets','event_attendances')
--     AND indexname LIKE 'ix_%_deleted_at' OR indexname = 'ix_crm_automation_flows_sede_id';
-- -- Debe retornar 3 índices.
--
-- Confirmar FK (solo CrmAutomationFlow.sede_id → sedes.id):
--   SELECT conname FROM pg_constraint
--   WHERE conname = 'fk_crm_automation_flows_sede_id';
-- -- Debe retornar 1 fila.
--
-- Confirmar alembic_version es head actual:
--   SELECT version_num FROM alembic_version;
-- -- Debe retornar '20260725_0003'.
