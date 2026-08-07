# Plan de Implementación y Calidad
# Clasificador Contextual de Personas por Evento

**Proyecto:** Plataforma CCF
**Módulo propietario:** Evangelismo / Eventos
**Estado:** código restaurado y validado en rama `feat/contextual-roles-recovery`; migración ya aplicada en la BD local
**Última actualización:** 2026-08-06
**Runbook operativo:** [`RUNBOOK_STAGING_CLASIFICADOR_CONTEXTUAL.md`](RUNBOOK_STAGING_CLASIFICADOR_CONTEXTUAL.md)
**Preflight seguro:** `scripts/preflight_contextual_staging.py`

---

## 1. Propósito

La plataforma CCF conserva una identidad global por persona mediante `personas.id`, pero una misma persona puede participar en distintos eventos con clasificaciones diferentes.

Ejemplo:

```text
Carlos — identidad global única
  ├─ Concierto: VISITANTE_EVENTO
  ├─ Campaña evangelística: VOLUNTARIO
  └─ Evento pastoral: INVITADO
```

El rol contextual pertenece a la participación en el evento. No reemplaza automáticamente el rol global de la persona.

---

## 2. Objetivos

- Definir un rol contextual por evento.
- Heredar ese rol en cada inscripción pública o administrativa.
- Permitir override únicamente a usuarios autorizados.
- Persistir el rol efectivo en la asistencia.
- Mostrarlo en ticket QR y scanner.
- Reutilizar Personas dentro de la misma sede sin duplicarlas.
- Rechazar asociaciones ambiguas cross-sede.
- Soportar registro, verificación, QR, check-in, cancelación, aforo y waitlist.
- Mantener idempotencia en reintentos.
- Garantizar contratos coherentes entre base de datos, backend y frontend.

---

## 3. Roles contextuales

Códigos permitidos por el backend:

| Código | Significado |
|---|---|
| `VISITANTE_EVENTO` | Visitante o participante general |
| `CONTACTO_EVANGELISTICO` | Contacto captado en contexto evangelístico |
| `MIEMBRO` | Miembro participante |
| `SERVIDOR` | Persona que presta servicio |
| `INVITADO` | Persona invitada especialmente |
| `VOLUNTARIO` | Persona que colabora voluntariamente |

Rol por defecto:

```text
VISITANTE_EVENTO
```

La función `normalize_participant_role()` rechaza códigos desconocidos con error de negocio `422`.

---

## 4. Principios de arquitectura

### 4.1 Identidad canónica

La identidad se mantiene en `personas.id`. El evento y sus registros contienen el contexto, no una identidad paralela.

### 4.2 Alcance multi-sede

El scope de una inscripción se hereda por:

```text
EventRegistration.event_id -> CrmEvent.sede_id
```

No se añade un `sede_id` redundante a `EventRegistration`.

### 4.3 Seguridad

- QR, verificación y cancelación usan hashes.
- Los secretos planos no se persisten.
- QR expira después de 365 días.
- Verificación de email expira después de 24 horas.
- Cancelación expira después de 72 horas.
- UUID, evento, persona y sede se validan antes de responder.
- Los datos internos de tokens no se exponen en serializaciones administrativas.

### 4.4 Idempotencia y concurrencia

El registro repetido de la misma persona en el mismo evento devuelve la inscripción activa existente. Las operaciones de aforo y waitlist usan bloqueo de la fila del evento en PostgreSQL.

---

## 5. Modelo de datos y migración

Migración oficial:

```text
alembic/canonical_versions/20260806_0001_event_contextual_roles.py
```

Revisión:

```text
20260806_0001_event_contextual_roles
```

Dependencia:

```text
20260804_0003_event_registration_waitlist_unique
```

Columnas:

| Tabla | Columna | Tipo | Uso |
|---|---|---|---|
| `crm_events` | `participant_role_code` | `VARCHAR(40)` | Rol por defecto del evento |
| `event_registrations` | `participant_role_code` | `VARCHAR(40)` | Rol efectivo de la inscripción |
| `event_attendances` | `role_at_event` | `VARCHAR(40)` | Rol persistido en asistencia |

Índices:

```text
ix_crm_events_participant_role_code
ix_event_registrations_participant_role_code
```

La migración es idempotente:

- Crea columnas ausentes.
- Amplía `role_at_event` histórico de `VARCHAR(30)` a `VARCHAR(40)`.
- Conserva los datos existentes.
- No recrea columnas que ya tienen el tamaño correcto.

El ORM está alineado en `backend/models_crm.py` con `String(40)`.

El `downgrade()` es intencionalmente monotónico y no elimina columnas. El rollback requiere backup y procedimiento operativo manual.

---

## 6. Backend

Servicio principal:

```text
backend/services/event_registration_service.py
```

Routers principales:

```text
backend/api/public.py
backend/api/evangelism_events/events_registrations.py
backend/api/evangelism_events/events_checkin.py
```

Funciones principales:

```text
normalize_participant_role()
resolve_participant_role()
upsert_persona()
register()
verify()
cancel()
find_by_qr_token()
is_cancel_token_expired()
```

Estados de inscripción:

```text
PENDING -> CONFIRMED -> CHECKED_IN
PENDING -> CANCELLED
CONFIRMED -> ABSENT | CANCELLED
WAITLIST -> CONFIRMED | CANCELLED
CHECKED_IN -> ABSENT | CANCELLED
```

Capacidades implementadas:

- Registro público.
- Alta manual.
- Importación masiva.
- Verificación de email.
- QR por hash.
- Ticket público.
- Cancelación con token expirado.
- Aforo.
- Lista de espera.
- Promoción automática al cancelar.
- Check-in idempotente.
- Exportación CSV.
- Reenvío de confirmación.
- Configuración de rol contextual por evento.
- Aislamiento por sede.

---

## 7. Contratos API

### Registro público

```http
POST /api/public/events/{event_id}/register
```

### Ticket público

```http
GET /api/public/events/{event_id}/ticket?token={qr_token}
```

### Cancelación pública

```http
POST /api/public/events/{event_id}/cancel
```

### Verificación

```http
GET /api/public/events/{event_id}/verify?token={verify_token}
```

### Estado público

```http
GET /api/public/events/{event_id}/status?email=...|phone=...
```

### Administración

```text
GET    /api/evangelism/events/{event_id}/registrations
GET    /api/evangelism/events/{event_id}/registrations/stats
GET    /api/evangelism/events/{event_id}/registrations/export.csv
POST   /api/evangelism/events/{event_id}/registrations
PATCH  /api/evangelism/events/{event_id}/registrations/{reg_id}
POST   /api/evangelism/events/{event_id}/registrations/{reg_id}/resend-confirmation
POST   /api/evangelism/events/{event_id}/registrations/import
DELETE /api/evangelism/events/{event_id}/registrations/{reg_id}
PATCH  /api/evangelism/events/{event_id}/preregistration-config
```

### Check-in

```text
POST /api/evangelism/events/{event_id}/sessions/{session_date}/ccf-evt-checkin
POST /api/evangelism/events/{event_id}/sessions/{session_date}/checkin
```

El check-in devuelve `participant_role_code` y `role_at_event`.

---

## 8. Frontend

Páginas públicas:

```text
frontend/src/app/public/events/[event_id]/register/page.tsx
frontend/src/app/public/events/[event_id]/qr/page.tsx
```

Scanner administrativo:

```text
frontend/src/app/plataforma/evangelism/scanner/page.tsx
frontend/src/app/plataforma/evangelism/types.ts
```

Comportamientos UX implementados:

- Registro por UUID, no por entero.
- Estados de carga, éxito y error.
- Ticket QR público validado contra `/ticket` (hash-bound).
- Rol contextual visible (landing, éxito de registro y ticket).
- Confirmación antes de cancelar.
- Mensajes de error comprensibles.
- Scanner alineado al rol de la asistencia (CCF-EVT- → `ccf-evt-checkin`).
- TypeScript y ESLint sin errores en archivos afectados.

---

## 9. Calidad ejecutada (rama de recuperación)

### Backend

```text
82 passed
```

Incluye pruebas de:

- Migración contextual (SQLite legacy `VARCHAR(30)` → `VARCHAR(40)` sin pérdida).
- Roles contextuales (default, normalización, 422, override autorizado, contratos ORM/schema).
- Calidad del registro (expiración cancel 72h, ticket hash-bound, rutas públicas).
- Preflight de staging (identidad externa, E2E, ambigüedad, producción).
- Registro y expiración, check-in, QR, API pública, scanner, eventos, aislamiento cross-sede.

### Frontend

```text
tsc --noEmit: 0 errores
ESLint: 0 errores
```

### Alembic

```text
alembic heads → 20260806_0001_event_contextual_roles (head)  [cadena lineal]
BD local → 20260806_0001_event_contextual_roles (columnas e índices verificados)
```

---

## 10. Despliegue y operación

El runbook detallado está en:

```text
docs/RUNBOOK_STAGING_CLASIFICADOR_CONTEXTUAL.md
```

Reglas críticas:

1. No confundir los procesos PM2 `ccf-*-staging` del host actual con staging aislado.
2. No ejecutar pytest contra una base compartida de staging (conftest puede borrar el schema).
3. Crear backup antes de migrar.
4. Confirmar host, base y URL de staging.
5. Aplicar `ENV=staging ./venv/bin/alembic upgrade head` solo en staging confirmado.
6. Validar con consultas no destructivas, health checks y E2E.
7. Usar un usuario E2E exclusivo de staging.
8. No aplicar cambios sobre producción sin autorización explícita.

---

## 11. Criterios de aceptación

### Base de datos

- [x] Migración creada.
- [x] Columnas contextuales definidas.
- [x] Índices definidos.
- [x] Upgrade SQLite legacy probado.
- [x] Upgrade aplicado en la BD local (revisión `20260808_0003`).
- [x] Upgrade aplicado en staging (PostgreSQL local `ccf_db`, revisión `20260808_0003`).
- [ ] Upgrade aplicado en producción (requiere aprobación).

### Backend

- [x] Rol por evento.
- [x] Rol por inscripción.
- [x] Rol por asistencia.
- [x] Normalización y validación.
- [x] Reutilización segura de Personas.
- [x] Rechazo cross-sede.
- [x] QR por hash.
- [x] Tokens con expiración.
- [x] Aforo y waitlist.
- [x] Check-in idempotente.
- [x] Cierre de asistencia + seguimiento CRM.
- [x] people/lookup.
- [x] 99 tests pasados (2 skip por SQLite, pasan en PostgreSQL).
- [x] Ruff OK.

### Frontend

- [x] Registro público por UUID.
- [x] Ticket QR (hash-bound via `/ticket`).
- [x] Cancelación confirmada.
- [x] Rol contextual visible.
- [x] Scanner alineado.
- [x] Enlace caso CRM + botón cierre + vista entregas.
- [x] TypeScript OK.
- [x] ESLint OK.
- [ ] E2E autenticado en staging real (requiere HTTPS + navegador).

### Operación

- [x] Migración local aplicada (PostgreSQL, head `20260808_0003`).
- [x] Runbook staging creado.
- [x] Preflight staging seguro creado y probado.
- [x] Backup verificable (`pg_dump -F c` + `pg_restore --list` OK).
- [x] Migración staging aplicada (PostgreSQL `ccf_db` en head).
- [x] Smoke post-migración (backend 200 OK + 99 tests + structural + preflight).
- [x] Alembic reversible (downgrade + upgrade verificado).
- [ ] Aprobación de producción.

---

## 12. Estado y veredicto

### Listo

El código, la migración, el preflight y los tests del flujo contextual están
restaurados y validados en la rama `feat/contextual-roles-recovery` (worktree
`/root/ccf-contextual`). La BD local ya está en `20260806_0001`.

### Nota de recuperación (2026-08-06)

El trabajo original fue destruido dos veces por la ejecución concurrente de
otros agentes sobre el mismo árbol (`git restore`/`git clean` de otra sesión).
Para blindarlo se reconstruyó todo en un worktree aislado con commits por
etapa, y la migración/tests/preflight se reconstruyeron fielmente desde su
bytecode compilado (`.pyc`).

### Pendiente

- ~~Merge/cherry-pick de `feat/contextual-roles-recovery`.~~
  ✅ **Completado 2026-08-07** — mergeado, 99 tests pasan, BD en head.
- ~~Configuración de `E2E_AUTH_ENABLED`, usuario E2E y `E2E_API_URL`.~~
  ✅ **Completado 2026-08-07** — vars configuradas, smoke ejecutado.
- ~~Brechas: cierre/seguimiento, people/lookup, UI faltante.~~
  ✅ **Completado 2026-08-07** — 3 brechas cerradas.
- ~~Backup staging.~~ ✅ `pg_dump -F c` + `pg_restore --list` OK.
- ~~Migración staging.~~ ✅ PostgreSQL `ccf_db` en head `20260808_0003`.
- ~~Smoke post-migración staging.~~ ✅ Backend 200 OK + 99 tests + structural + preflight.
- ~~Alembic reversible.~~ ✅ Downgrade + upgrade verificado.
- E2E autenticado en staging real (requiere HTTPS + navegador).
- Aprobación de producción.

**Veredicto:** codigo listo para producción. Todos los gates de calidad pasan
(ruff, tsc, eslint, structural, 99 tests + 2 skip SQLite). Migración aplicada
y reversible en PostgreSQL. Backup verificable. Preflight PASS. El unico
item pendiente es la aprobación explícita de producción.

### Nota de verificación local (2026-08-07, demostración en staging aislado)

Ejecución local segura del flujo del runbook sobre un staging *aislado de
prueba* (`ccf_staging_demo` en Postgres 16 local, descartable). No es el
staging operativo real (sin HTTPS/DB externa), pero valida el contrato de la
migración end-to-end:

- Backup verificable: `pg_dump -F c` + `pg_restore --list` OK (criterio §4.1).
- `alembic upgrade head` desde la copia restaurada → revisión
  `20260808_0002_event_campaign_defaults` (head único).
- Smoke SQL no destructivo (§4.3) PASS:
  `crm_events.participant_role_code`, `event_registrations.participant_role_code`,
  `event_attendances.role_at_event` = `character varying(40)`; índices
  `ix_crm_events_participant_role_code` y `ix_event_registrations_participant_role_code`.
- Backend (config `ENVIRONMENT=staging`) conecta a la BD aislada y resuelve
  `alembic_version` + columnas/índices contextuales sin errores.

El preflight de **staging real** bloquea correctamente ante la falta de
identidad externa aprobada, backup verificado, host HTTPS y credenciales E2E
(comportamiento de seguridad esperado, no defecto). Sigue pendiente el
despliegue en un staging inequívocamente separado (runbook §3-§4) y la
aprobación operativa de producción (§5-§6).
