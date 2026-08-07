# Runbook operativo
# Despliegue del Clasificador Contextual de Personas por Evento

**Proyecto:** Plataforma CCF
**Módulo:** Evangelismo / Eventos — clasificador contextual de personas por evento
**Rama de trabajo:** `feat/contextual-roles-recovery` (worktree `/root/ccf-contextual`)
**Última actualización:** 2026-08-06
**Plan:** [`PLAN_CLASIFICADOR_CONTEXTUAL_PERSONAS_EVENTO.md`](PLAN_CLASIFICADOR_CONTEXTUAL_PERSONAS_EVENTO.md)
**Preflight seguro:** `scripts/preflight_contextual_staging.py` (no modifica la base)

---

## 0. Reglas de oro

1. **El preflight no migra, no crea usuarios y no toca datos.** Solo valida configuración. Si pasa, la migración la ejecuta un operador humano de forma explícita.
2. **Backup verificable antes de migrar**, en staging y en producción. `CCF_STAGING_BACKUP_VERIFIED=1` / `CCF_PRODUCTION_BACKUP_VERIFIED=1` se fijan **después** de comprobar que el backup es restaurable.
3. **Identidad aprobada externa**: `CCF_APPROVED_ENV_FILE` debe apuntar a un JSON **fuera del repositorio** (secret manager / ops). Nunca contiene contraseñas.
4. **No confundir los procesos PM2 `ccf-*-staging` del host actual con un staging aislado.** Esos procesos corren contra la base local de desarrollo; no son el staging objetivo del runbook.
5. **Nunca ejecutar pytest contra la base compartida de staging**: el conftest puede borrar el schema.
6. **Producción exige autorización explícita** (`--ack-production` + `CCF_PRODUCTION_CHANGE_APPROVED=1` + backup verificado). Sin esos tres, el preflight bloquea.

---

## 1. Visión general del flujo

```text
[local]                [staging aislado]            [producción]
  ──┬──                  ──┬──                        ──┬──
    │ merge/cherry-pick     │ §3 preflight staging       │ §5 preflight producción
    │ de feat/contextual-   │ §4 backup + alembic        │ §6 backup + alembic
    │ roles-recovery        │    upgrade head            │    upgrade head
    ▼                       ▼                            ▼
  BD local ya migrada     staging en 20260806_0001      producción en 20260806_0001
  (20260806_0001)         smoke no destructivo + E2E    smoke no destructivo
```

---

## 2. Contrato de la migración

| Atributo | Valor |
|---|---|
| Archivo | `alembic/canonical_versions/20260806_0001_event_contextual_roles.py` |
| Revisión | `20260806_0001_event_contextual_roles` |
| Dependencia | `20260804_0003_event_registration_waitlist_unique` |
| Columnas | `crm_events.participant_role_code VARCHAR(40)`, `event_registrations.participant_role_code VARCHAR(40)`, `event_attendances.role_at_event VARCHAR(40)` |
| Índices | `ix_crm_events_participant_role_code`, `ix_event_registrations_participant_role_code` |

La migración es idempotente: crea columnas ausentes, amplía `role_at_event` histórico de `VARCHAR(30)` a `VARCHAR(40)` y conserva los datos. El `downgrade()` es monotónico (no elimina columnas); el rollback real requiere backup y procedimiento manual.

**Antes de operar, verificar que el head es único:**

```bash
cd /root/ccf-contextual
./venv/bin/alembic heads
# → 20260806_0001_event_contextual_roles (head)
```

---

## 3. Preflight de staging (obligatorio)

### 3.1 Requisitos de entorno

| Variable | Valor esperado | Motivo |
|---|---|---|
| `ENV` o `ENVIRONMENT` | `staging` | Entorno coherente |
| `DATABASE_URL` o `STAGING_DATABASE_URL` | URL Postgres **sin credenciales embebidas** | Se usa `.pgpass` / secret manager |
| `CCF_APPROVED_ENV_FILE` | Ruta a JSON externo | Identidad aprobada (ver §3.2) |
| `CCF_STAGING_BACKUP_VERIFIED` | `1` | Solo tras backup restaurable (§4.1) |
| `E2E_AUTH_ENABLED` | `1` | E2E aislado habilitado |
| `E2E_EMAIL`, `E2E_PASSWORD` | Usuario exclusivo de staging | No reutilizar datos reales |
| `E2E_API_URL` | `https://` + host aprobado | Debe coincidir con `NEXT_PUBLIC_API_URL` |
| `NEXT_PUBLIC_API_URL` | `https://` + host aprobado | Debe coincidir con `E2E_API_URL` |

> Ambigüedad bloqueante: si están **ambas** `DATABASE_URL` y `STAGING_DATABASE_URL`, el preflight falla (podrían apuntar a entornos distintos).

### 3.2 Archivo de identidad aprobada (ejemplo)

Guardar **fuera del repo** (ej. `/etc/ccf/staging-identity.json`):

```json
{
  "target": "staging",
  "db_host": "staging-db.ejemplo.com",
  "db_name": "ccf_staging",
  "base_url": "https://staging.ejemplo.com"
}
```

Sin contraseñas. El preflight valida que `db_host` y `db_name` coincidan con la URL configurada y que `base_url` use HTTPS.

### 3.3 Ejecución

```bash
cd /root/ccf-contextual
ENV=staging \
CCF_APPROVED_ENV_FILE=/etc/ccf/staging-identity.json \
CCF_STAGING_BACKUP_VERIFIED=1 \
E2E_AUTH_ENABLED=1 \
E2E_EMAIL=e2e-staging@ejemplo.com \
E2E_PASSWORD='...' \
E2E_API_URL=https://staging.ejemplo.com \
NEXT_PUBLIC_API_URL=https://staging.ejemplo.com \
./venv/bin/python scripts/preflight_contextual_staging.py --target staging
```

Salida esperada (todo en `PASS`):

```text
PASS environment: ENV/ENVIRONMENT=staging; expected=staging
PASS database configured: driver=postgresql host=staging-db... database=ccf_staging
PASS postgresql required: driver=postgresql
PASS database URL has no embedded credentials: use .pgpass or a secret manager
PASS approved environment identity: external identity file loaded
PASS approved staging target: identity target must be staging
PASS approved staging DB host: database host matches external identity
PASS approved staging DB name: database name matches external identity
PASS approved staging base URL: approved base URL must use HTTPS
PASS staging backup verified: set only after verifying a restorable backup
PASS E2E_AUTH_ENABLED: must equal 1
PASS E2E_EMAIL: test-only staging user required
PASS E2E_PASSWORD: test-only staging password required
PASS E2E_API_URL: must be HTTPS and use approved staging host
PASS NEXT_PUBLIC_API_URL: must be HTTPS and use approved staging host
PASS E2E URL consistency: E2E/API URLs must target the same approved host

Preflight aprobado. Este comando no ejecutó migraciones ni modificó datos.
```

Cualquier `BLOCK` detiene el proceso: **no continuar** hasta resolver la causa.

---

## 4. Migración de staging

### 4.1 Backup previo (obligatorio)

```bash
# En el host de staging, antes de migrar:
pg_dump -h "$STAGING_DB_HOST" -U "$STAGING_DB_USER" -d ccf_staging \
  -F c -f "/backups/ccf_staging_$(date +%Y%m%d_%H%M%S).dump"
```

Verificar restaurabilidad (no solo creación del archivo):

```bash
pg_restore --list "/backups/ccf_staging_$(date +%Y%m%d_%H%M%S).dump" >/dev/null \
  && echo "backup restaurable"
```

Solo entonces fijar `CCF_STAGING_BACKUP_VERIFIED=1` en el entorno del preflight.

### 4.2 Aplicar la migración

```bash
cd /root/ccf-contextual
ENV=staging ./venv/bin/alembic upgrade head
```

Verificar la revisión:

```bash
ENV=staging ./venv/bin/alembic current
# → 20260806_0001_event_contextual_roles
```

### 4.3 Smoke no destructivo post-migración

Consultas de solo lectura:

```bash
ENV=staging ./venv/bin/python - <<'PY'
import os
import sqlalchemy as sa

engine = sa.create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    cols = conn.execute(sa.text(
        "select table_name, column_name, data_type, character_maximum_length "
        "from information_schema.columns "
        "where (table_name, column_name) in ("
        "  ('crm_events','participant_role_code'),"
        "  ('event_registrations','participant_role_code'),"
        "  ('event_attendances','role_at_event'))"
        "order by table_name"
    )).all()
    for t, c, d, m in cols:
        print(f"OK {t}.{c} {d}({m})")
    idx = conn.execute(sa.text(
        "select indexname from pg_indexes where indexname like "
        "'ix_%participant_role_code%' order by indexname"
    )).scalars().all()
    print("indices:", idx or ["MISSING"])
PY
```

Resultado esperado:

```text
OK crm_events.participant_role_code character varying(40)
OK event_registrations.participant_role_code character varying(40)
OK event_attendances.role_at_event character varying(40)
indices: ['ix_crm_events_participant_role_code', 'ix_event_registrations_participant_role_code']
```

### 4.4 Health checks y E2E

- Health check del API: `GET /health` en staging → `200`.
- Smoke E2E autenticado (usuario exclusivo de staging): registro público → ticket QR (`/ticket` con token) → check-in contextual (`ccf-evt-checkin`) → cancelación con token.
- Verificar que el rol contextual aparece en: inscripción (admin), ticket QR y asistencia.

### 4.5 Rollback (si algo falla)

La migración no elimina datos; el rollback correcto es **restaurar el backup**:

```bash
pg_restore -h "$STAGING_DB_HOST" -U "$STAGING_DB_USER" -d ccf_staging \
  --clean --if-exists "/backups/ccf_staging_<TIMESTAMP>.dump"
```

No usar `alembic downgrade` como rollback de datos: el `downgrade()` es monotónico a propósito.

---

## 5. Preflight de producción (obligatorio)

### 5.1 Requisitos adicionales

| Variable | Valor esperado | Motivo |
|---|---|---|
| `ENV` o `ENVIRONMENT` | `production` | Entorno coherente |
| `CCF_APPROVED_ENV_FILE` | JSON con `target: "production"` | Identidad de producción aprobada |
| `CCF_PRODUCTION_CHANGE_APPROVED` | `1` | Autorización operativa explícita |
| `CCF_PRODUCTION_BACKUP_VERIFIED` | `1` | Backup restaurable verificado |
| `--ack-production` | flag en CLI | Reconocimiento explícito de la ventana de cambio |

### 5.2 Ejecución

```bash
cd /root/ccf-contextual
ENV=production \
CCF_APPROVED_ENV_FILE=/etc/ccf/production-identity.json \
CCF_PRODUCTION_CHANGE_APPROVED=1 \
CCF_PRODUCTION_BACKUP_VERIFIED=1 \
./venv/bin/python scripts/preflight_contextual_staging.py \
  --target production --ack-production
```

Si falta cualquiera de las tres condiciones (ack, aprobación, backup), el preflight bloquea con:

```text
BLOCK explicit production acknowledgement: pass --ack-production only after approved change window
BLOCK production approval: explicit operational approval required
BLOCK production backup verified: set only after verifying a restorable backup
```

---

## 6. Migración de producción

1. Backup verificable (igual que §4.1, contra la base de producción).
2. Aplicar:

```bash
cd /root/ccf-contextual
ENV=production ./venv/bin/alembic upgrade head
ENV=production ./venv/bin/alembic current   # → 20260806_0001_event_contextual_roles
```

3. Smoke no destructivo (igual que §4.3, contra producción).
4. Observar métricas/logs del módulo de eventos (errores 5xx, latencia de `/ticket` y check-in) durante la primera hora.

---

## 7. Checklist de despliegue

### Staging
- [ ] `alembic heads` → head único `20260806_0001`
- [ ] Backup creado y **verificado restaurable**
- [ ] `CCF_STAGING_BACKUP_VERIFIED=1`
- [ ] Identidad externa `staging-identity.json` fuera del repo
- [ ] Preflight staging: 100% `PASS`
- [ ] `ENV=staging alembic upgrade head`
- [ ] Smoke SQL: 3 columnas `varchar(40)` + 2 índices
- [ ] Health check `GET /health` → 200
- [ ] E2E autenticado sin skips (registro → ticket → check-in → cancelación)

### Producción
- [ ] Ventana de cambio aprobada
- [ ] `CCF_PRODUCTION_CHANGE_APPROVED=1` y `--ack-production`
- [ ] Backup verificado → `CCF_PRODUCTION_BACKUP_VERIFIED=1`
- [ ] Preflight producción: 100% `PASS`
- [ ] `ENV=production alembic upgrade head`
- [ ] Smoke SQL no destructivo
- [ ] Monitorización post-despliegue (1h)

---

## 8. Prohibiciones

- ❌ No ejecutar pytest contra la base de staging (conftest puede borrar el schema).
- ❌ No aplicar la migración sin backup verificado.
- ❌ No usar `DATABASE_URL` y `STAGING_DATABASE_URL` a la vez.
- ❌ No usar credenciales embebidas en la URL de staging/producción.
- ❌ No reutilizar `E2E_EMAIL`/`E2E_PASSWORD` de staging en otros entornos.
- ❌ No usar `alembic downgrade` como rollback de datos.
- ❌ No operar sobre los procesos PM2 `ccf-*-staging` del host local creyendo que son staging aislado.
