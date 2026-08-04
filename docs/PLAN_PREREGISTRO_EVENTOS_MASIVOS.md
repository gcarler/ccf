# PLAN PREREGISTRO EVENTOS MASIVOS

**Propietario:** Plataforma CCF
**Estado:** Aprobado — pendiente de implementación
**Alcance:** Fases 1-7 (backend + check-in + campañas + frontend + tests)
**Compatibilidad:** Backward-compatible (`requires_registration=False` por defecto)

---

## 1. Resumen ejecutivo

Caso de uso objetivo: un evento masivo (concierto cristiano, conferencia, evento
especial con boletas) puede:

1. Abrir **pre-registro público**.
2. Generar un **QR único por inscrito** (o por evento, configurable).
3. Lanzar una **campaña de mensajes** (WhatsApp/Email/SMS) a los inscritos antes
   del evento (recordatorios, variables de evento).
4. El día del evento hacer **check-in con lector QR** o **constatación manual**,
   marcando quién asistió (`CHECKED_IN`) y quién no (`ABSENT`).

Estado actual en CCF: las piezas base ya existen (eventos, `EventAttendance`,
scanner `CCF-PER-`, motor de plantillas, gateways de mensajería). Lo que falta es
el concepto de **pre-registro** con ciclo de vida propio, su QR, y la campaña
ligada al evento.

### Decisiones acordadas

| Decisión | Valor |
|----------|-------|
| Alcance | Fases 1-7 (completo) |
| Migración | Backward-compatible, `requires_registration=False` por defecto |
| Emails de verificación/confirmación | `backend/services/email.py` |
| Archivo | `docs/PLAN_PREREGISTRO_EVENTOS_MASIVOS.md` |
| Naming interno | plan_de_preregistro |

---

## 2. Estado actual del código (inventario reutilizable)

| Pieza | Ubicación | Nota |
|-------|-----------|------|
| Scanner persona `CCF-PER-` | `backend/api/evangelism.py:63-125` | SHA-256 hash + expiry 365 días, ya funcional |
| `Persona.qr_token` | `models_crm.py:418` | 16-char hex auto-generated |
| `Persona.scanner_token_hash` | `models_crm.py:452` | token por persona |
| `EventAttendance` | `models_crm.py:141-176` | `attended`, `check_in_at`, `source`, `scanned_at` |
| Bulk attendance | `events_participantes.py:98-208` | sync presente/ausente para sesión |
| Session detail + ausentes | `events_participantes.py:211-307` | `get_expected_personas_for_event` |
| Export CSV Presente/Ausente | `events_main.py:459-514` | compare expected vs attended |
| Check-in visitante walk-in | `events_checkin.py:30-136` | crea Persona + attendance + caso CRM |
| Plantillas CRM | `models_crm.py:270-352` | `PlantillaMensaje`, `BitacoraEnvioPlantilla` |
| Gateways mensajería | `services/messaging.py` | WhatsApp/Email/SMS via async gateway |
| Email service | `services/email.py` | usado por `cms_v2/forms.py:59` |
| Hidratación `{{var}}` | `services/automation_engine.py:320-333` | `{{name}}`, `{{nombre}}`, `{{first_name}}` |
| Migraciones | `alembic/canonical_versions/` | patrón `YYYYMMDD_NNNN_*`, reversible |

---

## 3. Modelo de datos

### 3.1 Columnas nuevas en `crm_events`

```sql
ALTER TABLE crm_events
    ADD COLUMN requires_registration        BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN requires_email_verification  BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN registration_opens_at        TIMESTAMPTZ          DEFAULT NULL,
    ADD COLUMN registration_closes_at       TIMESTAMPTZ          DEFAULT NULL,
    ADD COLUMN capacity_max                 INTEGER              DEFAULT NULL,
    ADD COLUMN waiting_list_enabled         BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN qr_mode                      VARCHAR(20)  NOT NULL DEFAULT 'PER_REGISTRANT',
    ADD COLUMN contact_person               VARCHAR(255)          DEFAULT NULL,
    ADD COLUMN settings_json                JSONB       NOT NULL DEFAULT '{}'::jsonb;
```

### 3.2 Tabla `event_registrations`

```sql
CREATE TABLE event_registrations (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id                UUID        NOT NULL REFERENCES crm_events(id) ON DELETE CASCADE,
    persona_id              UUID        NOT NULL REFERENCES personas(id)   ON DELETE CASCADE,
    registration_status     VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    qr_token                VARCHAR(100)          NULL,
    qr_token_hash           VARCHAR(128)          NULL,
    qr_generated_at         TIMESTAMPTZ           NULL,
    registered_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    confirmed_at            TIMESTAMPTZ           NULL,
    cancelled_at            TIMESTAMPTZ           NULL,
    check_in_at             TIMESTAMPTZ           NULL,
    check_out_at            TIMESTAMPTZ           NULL,
    checked_in_by           UUID                  NULL REFERENCES personas(id) ON DELETE SET NULL,
    source                  VARCHAR(30)  NOT NULL DEFAULT 'public_form',
    extras                  JSONB        NOT NULL DEFAULT '{}'::jsonb,
    waiting_list_position   INTEGER                NULL,
    reminder_sent_count     INTEGER      NOT NULL DEFAULT 0,
    last_reminder_sent_at   TIMESTAMPTZ           NULL,
    deleted_at              TIMESTAMPTZ           NULL,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_event_reg_persona   ON event_registrations (event_id, persona_id);
CREATE INDEX ix_reg_event_status          ON event_registrations (event_id, registration_status);
CREATE INDEX ix_reg_qr                    ON event_registrations (qr_token_hash);
```

### 3.3 Tabla `event_campaigns`

```python
CREATE TABLE event_campaigns (
    id                     UUID       PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id               UUID       NOT NULL REFERENCES crm_events(id) ON DELETE CASCADE,
    name                   VARCHAR(200) NOT NULL,
    plantilla_id           UUID       NULL REFERENCES crm_plantillas_mensaje(id),
    canal                  VARCHAR(20) NOT NULL DEFAULT 'EMAIL',   -- WHATSAPP|EMAIL|SMS
    trigger_type           VARCHAR(50) NOT NULL DEFAULT 'MANUAL', -- MANUAL|RELATIVE_TO_EVENT|RELATIVE_TO_REGISTRATION
    trigger_offset_minutes INTEGER              DEFAULT NULL,      -- -1440 = 24h antes
    target_status          JSONB      NOT NULL DEFAULT '["CONFIRMED"]'::jsonb,
    sent_count             INTEGER    NOT NULL DEFAULT 0,
    last_sent_at           TIMESTAMPTZ           NULL,
    created_by_id          UUID       REFERENCES personas(id) ON DELETE SET NULL,
    is_active              BOOLEAN    NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at             TIMESTAMPTZ           NULL
);
```

### 3.4 Diagrama de estados

```
                      ┌──────────┐
      new/✔register ─▶│ PENDING  │
                      └──────────┘
                         │  email url verification (opcional)
                         ▼
                      ┌──────────┐   check_in   ┌────────────┐
   PENDING/verify ──▶ │CONFIRMED │ ───────────▶ │  CHECKED_IN │
                      └──────────┘             └────────────┘
                         │ closure (no attend)        │
                         ▼                            ▼
                     ┌────────┐                   ┌──────────┐
                     │ ABSENT │                   │   (done) │
                     └────────┘                   └──────────┘

WAITLIST ──(promove when slot frees)──▶ CONFIRMED
Any ──cancelled──▶ CANCELLED (soft, deleted_at set)
```

---

## 4. API Contracts

### 4.1 Públicos (sin auth + rate-limit)

| Método | Ruta | Función |
|--------|------|---------|
| GET | `/api/public/events/{event_id}` | Metadata pública del evento |
| POST | `/api/public/events/{event_id}/register` | Pre-registro |
| GET | `/api/public/events/{event_id}/verify` | Verificación email por token |
| GET | `/api/public/events/{event_id}/status` | Estado del inscrito |
| POST | `/api/public/events/{event_id}/cancel` | Auto-cancelación (con token) |

Prefijo `/api` (alineado con `/api/public/contact` y `/api/crm/prayer-requests/public` existentes).

```python
class PublicEventRegister(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    extra: dict = {}
    accept_contact: bool = True
    registration_mode: Literal["open", "requires_registration"] = "requires_registration"
```

### 4.2 Admin (Axioma 3 + RBAC)

| Método | Ruta | RBAC | Función |
|--------|------|------|---------|
| GET | `/api/evangelism/events/{id}/registrations` | `read` | Lista paginada |
| GET | `/api/evangelism/events/{id}/registrations/export.csv` | `read` | CSV |
| GET | `/api/evangelism/events/{id}/registrations/stats` | `read` | KPI |
| POST | `/api/evangelism/events/{id}/registrations` | `manage` | Alta manual |
| PATCH | `/api/evangelism/events/{id}/registrations/{rid}` | `edit` | Edit status |
| POST | `/api/evangelism/events/{id}/registrations/import` | `manage` | Bulk import |
| POST | `/api/evangelism/events/{id}/registrations/{rid}/resend-confirmation` | `edit` | Reenviar QR |
| POST | `/api/evangelism/events/{id}/registrations/broadcast` | `edit` | Disparar campaña |
| DELETE | `/api/evangelism/events/{id}/registrations/{rid}` | `manage` | Soft-delete |

**Axioma 3 (Multi-Tenant — REGLAS §4):** todo endpoint arriba primero resuelve
`sede_id = get_user_sede_id(db, current_user.id)` y filtra con
`_scope_by_user_sede_via_persona(db, current_user, q)` sobre los JOINs de
`event_registrations.persona_id → personas.sede_id`. El `CrmEvent.sede_id`
(`models_crm.py:87`) debe coincidir con la sede del actor; registros de otra
sede devuelven 404. Bulk import y broadcast aún requieren el scope sede por
`persona_id`, no por `event_id` (una persona puede estar en evento numa sede
pero ser importada en otra → rechazada con 409).

### 4.3 Check-in unificado (día D)

| Método | Ruta | RBAC | Función |
|--------|------|-----|---------|
| POST | `/api/evangelism/events/{id}/sessions/{date}/checkin` | `edit` | QR / manual |
| POST | `/api/evangelism/events/{id}/sessions/{date}/checkout` | `edit` | Marcar salida |

```python
class CheckinPayload(BaseModel):
    qr_token: Optional[str] = None          # CCF-EVT- o CCF-PER-
    persona_id: Optional[UUID] = None       # via manual
    first_name: Optional[str] = None        # walk-in simple
    last_name: Optional[str] = None
    phone: Optional[str] = None
```

### 4.4 Checkin lógica (pseudocódigo)

```python
def checkin(event, payload, actor):
    persona = resolve(qr_token) or db.query(Persona).filter(id=payload.persona_id)
    is_duplicate = bool(
        db.query(EventAttendance)
          .filter(EventAttendance.event_id == event.id,
                  EventAttendance.session_date == session_date,
                  EventAttendance.persona_id == persona.id)
          .first()
    )
    if payload.qr_token.startswith("CCF-EVT-"):
        reg = find EventRegistration by qr_token_hash(sha256(qr_token))
        if reg and reg.status == "CONFIRMED":
            reg.status = "CHECKED_IN"; reg.check_in_at=now; reg.checked_in_by=actor
            # always create/update EventAttendance (attended=True, idempotente por
            # UNIQUE(event_id, session_date, persona_id))
            attendance = upsert(event, session_date, persona)
            return {"status": "success", "is_duplicate": is_duplicate}
        # reg ya CHECKED_IN o no existe → retornar is_duplicate
        return {"status": "noop", "is_duplicate": is_duplicate}
    elif payload.qr_token.startswith("CCF-PER-"):
        # Reusa el scanner de persona existente (evangelism.py:84) que valida
        # scanner_token_hash + expiry; aquí solo nos interesa resolver la persona.
        persona = verify_scanner_per_token(db, payload.qr_token)  # 404 si invalido/expirado
        attendance = upsert(event, session_date, persona)        # idempotente
        return {"status": "success", "is_duplicate": is_duplicate}
    else:
        # manual via persona_id o walk-in simple (first_name/last_name/phone)
        persona = upsert_persona(payload)
        attendance = upsert(event, session_date, persona)
        return {"status": "success", "is_duplicate": is_duplicate}
```


---

## 5. Campañas de mensajería

### 5.1 Variables dinámicas nuevas

- `{{evento_nombre}}`, `{{evento_fecha}}`, `{{evento_ubicacion}}`, `{{evento_hora}}`
- `{{qr_url}}` (link al QR del inscrito)
- `{{inscripcion_estado}}`, `{{inscripcion_id}}`

### 5.2 Scheduler job (en `backend/scheduler.py`)

```python
for campaign in active EventCampaign where event.event_date + offset <= now
   and not sent (last_sent_at < campaign.created_at):
    for reg in EventRegistration(status IN target_status)
        + reg.last_reminder_sent_at < campaign.last_sent_at:
         gateway.send(reg.persona, template, vars hydrated)
         reg.reminder_sent_count += 1
         reg.last_reminder_sent_at = now
```

---

## 6. Tests

Archivos nuevos:

- `tests/test_event_registrations.py`
- `tests/test_event_campaigns.py`
- Añadir assertions a `tests/test_structural_contracts.py`

 Casos clave:

1. Pre-registro happy path (sin email url) → status `CONFIRMED`, QR generado.
2. Pre-registro con email url → PENDING hasta verificar.
3. Aforo lleno → 409 `EVENT_FULL` + waitlist.
4. Cancelación libera slot y promueve waitlist automáticamente.
5. Check-in QR `CCF-EVT-` marca `CHECKED_IN` + `EventAttendance`.
6. Check-in duplicado → `is_duplicate=True`.
7. Axioma 3: registro de otra sede → 404/403.
8. Hidratación `{{evento_nombre}}` en campaña.

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Tormenta de formulario público | `rate_limiter(limit=PUBLIC_RATE, window_seconds=60)` |
| Enumeración de tokens/verify | tokens de 32 bytes + hash sha256, no exponer persona_id |
| Scanner QR expira a 365 días | alinear con `scanner_token_expires_at`; permitir re-generar |
| Check-in duplicado | `is_duplicate=True` + UNIQUE(event_id, persona_id) |
| Aforo races | `SELECT ... FOR UPDATE` sobre count en transacción |

---

## 8. Rollout incremental (orden de commits)

1. `db(events): add preregistration columns + event_registrations + campaign tables (migration)`
2. `feat(events): pre-registration public API (register/verify/status/cancel)`
3. `feat(events): admin registrations + stats + export + import`
4. `feat(events): unified check-in (QR CCF-EVT-/CCF-PER-/manual) + checkout`
5. `feat(events): campaigns (model + scheduler + endpoints)`
6. `feat(frontend/events): public registration page + QR render + admin UI`
7. `test(events): registration + campaigns suites`

Cada commit debe pasar `npx tsc --noEmit` (frontend), `pytest` (backend) y
`alembic upgrade head` antes de merge a `main`.

---

## 9. Ubicación de archivos a crear/modificar

| Archivo | Acopio |
|---------|--------|
| `alembic/canonical_versions/{YYYYMMDD}_NNNN_event_registration_features.py` | migración |
| `backend/models_crm.py` | `EventRegistration`, `EventCampaign`, relaciones |
| `backend/schemas/crm/base.py` | schemas Pydantic |
| `backend/api/evangelism_events/events_registrations.py` | admin regs |
| `backend/api/public.py` | endpoints públicos |
| `backend/api/evangelism_events/events_checkin.py` | checkin unificado |
| `backend/scheduler.py` | job de campañas |
| `frontend/src/app/public/events/[id]/register/` | página pública |
| `frontend/src/app/plataforma/evangelism/events/page.tsx` | admin |
```

## 10. Rollback

```bash
alembic downgrade -1
# borra event_campaigns, event_registrations, quita columnas de crm_events
```

Si se revierte: limpiar `qr_token_hash` en `Persona` si se generó un ciclo de
QRs en producción.

---

*fin del plan — plan_de_preregistro*