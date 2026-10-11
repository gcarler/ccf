# Plan de Trabajo: Robustecimiento de Notificaciones + Espejo por Email — Plataforma CCF

**Fecha:** 2026-10-11
**Estado:** Propuesta para revisión
**Alcance acordado con el usuario:** espejo transaccional de email (no OAuth per-user); Calendar/Drive quedan como **fase futura explícita**, fuera del alcance actual.

---

## 1. Resumen Ejecutivo

Hoy la plataforma tiene un sistema sólido de notificaciones **in-app** (mensajería instantánea con rate limit, ownership por usuario, SSE en tiempo real) pero **no hay un canal de email consistente**: los fragmentos de email que sí existen (`backend/services/email.py`, task assignments, eventos, CRM, Academy) llevan envío SMTP ad-hoc, sin preferencias por usuario, sin trazabilidad central, sin plantillas reutilizables ni manejo de prepago/deliverability.

Este plan introduce una **arquitectura de notificaciones unificada** con espejo a email como primer canal externo, y deja la puerta abierta a Google Calendar/Drive como fase posterior.

## 2. Arquitectura Objetivo

```
                     ┌─────────────────────────────────────┐
   evento producto → │  NotificationOrchestrator (FastAPI) │
                     │  services/notification_hub.py       │
                     └─┬───────────────────────────────────┘
                       │ fan-out según preferencias
          ┌────────────┼───────────────────┐
          ▼            ▼                   ▼
    canal in-app   canal email        (fase 4+ push/whatsapp/etc.)
```

**Principios:**
- Los productores de eventos (tareas, menciones, agenda, evangelismo, Academy, CRM) **no mandan email directamente** — solo llaman al orchestrator.
- Un único daemon/celery worker o tarea programada entrega al proveedor real.
- Toda entrega queda registrada en `notification_deliveries` para auditoría.

## 3. Fundamentos Backend Ya Existentes (No reinventar)

- `Notification` / `auth_notifications`: modelo in-app por usuario con índices por `user_id` y `sede_id`.
- `POST/GET/PATCH /messaging/notifications` + `mark-all-read`: base para read-state unificado.
- `backend/services/email.py`: plantillas corporativas HTML (`_brand_wrap`), SMTP config, resolve colors dinámicos por CMS theme.
- `send_email()` en auth_v3, task_notifications, event_* services, academy_notifications: casos de uso ya implementados — solo hace falta refactorizarlos para que pasen por el hub.
- Redis operativo (rate limit de broadcasts) — disponible para colas de trabajo.

## 4. Fases del Plan

### FASE 1 — Preferencias por usuario y modelo de datos
**Objetivo:** que cada usuario decida *qué* recibe por email y *cómo*.

| Ítem | Detalle |
|---|---|
| `R1.T1` | Migración reversible Alembic: tabla `notification_preferences` (PK UUIDv4, `user_id` FK, `sede_id` nullable=global, `channel` ∈ {in_app, email}, `event_type` varchar, `enabled` bool, `created_at/updated_at`). Único constraint: UNIQUE(user_id, channel, event_type). |
| `R1.T2` | Seeder de preferencias por defecto: `in_app` ON para todo; `email` OFF para todo excepto `task_assigned`, `mention`, `event_reminder` (24h antes). |
| `R1.T3` | CRUD FastAPI `notification_preferences` con `require_module_access`, `current_user.id` obligatorio, Axioma 3 (solo propias), FastAPI Query params para filtros. |
| `R1.T4` | Frontend: sección "Notificaciones" en perfil ajustes (`/plataforma/profile`) con tabla de switches canal × evento, usando tokens semánticos y estados de carga (Skeleton) y `toast` (sonner). |
| `R1.T5` | Tests: pytest de API (CRUD + ownership multi-tenant) + vitest del componente de preferencias. |

**Criterios de aceptación:**
- `GET /api/v3/notifications/preferences` responde con defaults seedeados.
- `PATCH /api/v3/notifications/preferences/{event_type}` solo persiste si `current_user.id` == owner.
- Compilación `tsc --noEmit` limpia; suite frontend pytest + vitest verde.
- **Push seguro:** usar `scripts/push_branch.sh origin <rama>` (nunca `--no-verify`).

---

### FASE 2 — Notification Hub + entrega email real
**Objetivo:**心电图 un punto único de fan-out y correo saliente confiable.

| Ítem | Detalle |
|---|---|
| `R2.T1` | `backend/services/notification_hub.py`: API pública `notify(user_ids, event_type, payload, channels?, dedupe_key?)` que respeta preferencias (`in_app` + `email`), y crea registro entregado en `notification_deliveries`. |
| `R2.T2` | Migración reversible: tabla `notification_deliveries` (PK UUID, `notification_id` FK, `channel`, `status` ∈ {pending, sent, failed, suppressed}, `provider_message_id`, `error`, `attempted_at`, `delivered_at`). |
| `R2.T3` | Proveedor de email transaccional: integrar **proveedor externo** con API simple, dominio verificado (SPF/DKDM/DMARC en DNS de la iglesia) y webhook de estado de entrega. Recomendación inicial: **Knock** (orchestrator de notificaciones multi-canal, plan gratuito 10k mensajes/mes, email entregado vía provider conectado) o alternativas Pipeline/Pure SMTP self hosted si se prefiere evitar dependencia SaaS. Decisión de proveedor se toma al ejecutar fase 2. |
| `R2.T4` | Worker asíncrono (celery + Redis ya disponible, o FastAPI BackgroundTasks para volumen bajo) que consume el hub y ejecuta `send_email` con backoff exponencial. |
| `R2.T5` | Refactor: migrar los 23 call-sites actuales de `send_email()` que son notificaciones de producto hacia `notification_hub.notify()`. Los transactionals (verify-email, reset-password, task assignment init) pueden quedarse directos. |
| `R2.T6` | Rate limiting por destinatario (máx. aggregates: 1 email por 15 min por user/evento, digerido si hay sobredosis). |
| `R2.T7` | Tests: unit (preferencias respetadas, dedupe, backoff), integración (stub proveedor), pytest enfermedad. |

**Criterios de aceptación:**
- Disparo de `notify_mention` produce un `auth_notifications` + (si preferencia ON) una fila en `notification_deliveries` con status `sent`.
- `send_email` legacy ya no es llamado por los flujos de producto refactorizados (búsqueda `grep -rn "send_email(" backend/` solo muestra calls de auth/reset).
- Webhook del proveedor actualiza `notification_deliveries.status` y marca `bounced/spam/complaint` para desactivar intentos futuros a ese destinatario.
- Cero `datetime.utcnow()`, cero fetch() crudo en frontend, cero colores hardcodeados, rutas `/plataforma/...`.
- Migración con `upgrade()/downgrade()` verificada en local.

---

### FASE 3 — Unificación de bandeja + deduplicación
**Objetivo:** que la bandeja in-app y el email dijern si algo tiene estado, y que spam cero.

| Ítem | Detalle |
|---|---|
| `R3.T1` | Unificar read-state: `PATCH /messaging/notifications/{id}` marca leído in-app; si la preferencia lo indica, también suprime el email pendiente (cancelación pre-envío). |
| `R3.T2` | Dedupe por `dedupe_key` en el hub: si ya existe una notification in-app con la misma clave, no se genera otra, y el email se cancela/actualiza el asunto/agregación. |
| `R3.T3` | Digest diario opcional por usuario: toggle en preferencias (`email_digest_daily`) — un email 8am con resumen del día en vez de correos individuales. |
| `R3.T4` | Frontend: indicador de carga y de estado de envío/resumen en el panel de notificaciones (`/plataforma/messages`), con `Skeleton`/`EmptyState` y `toast`. |
| `R3.T5` | Tests: pytest de dedupe + vitest de UI, cubriendo cancelación pre-envío. |

**Criterios de aceptación:**
- Si el usuario marca una notificación como leída antes de que se dispare el email y su preferencia lo permite, no se envía el correo.
- `dedupe_key` evita duplicados: 2 menciones en 1 min del mismo comentario generan 1 email agregado.
- Los 3 criterios de compilación y suite verde como en fases anteriores.

---

### FASE 4 — Fase futura explicita (post-MVP, requiere decisión)

No están dentro del alcance actual pero sí previstos:

| Fase | Alcance | Requiere |
|---|---|---|
| F4.A | Google Calendar por OAuth de la organización (Workspace) — sync de eventos de agenda y recordatorios | Verificación OAuth de Google para scopes `calendar.events`; test con 100 usuarios; posible revisión de Google (criterios de seguridad/CASA) para scopes sensibles |
| F4.B | Gmail per-user OAuth (gmail.send) — correo sale desde la cuenta personal del usuario | Verificación OAuth de Google por scope sensibles; consentimiento y revocación per-user; riesgo alto de mantenimiento |
| F4.C | Drive per-user OAuth (drive.file) — adjuntar documentos de proyectos/tareas | Igual que F4.B |
| F4.D | WhatsApp Business API para notificaciones críticas | Cuenta WhatsApp Business verificada, coste por conversación |
| F4.E | Push Web (WebPush + service worker) | Nada en especial; se hace cuando haya capacidad |

**Nota:** Google exige revisión de seguridad (CASA/Tier 2) para scopes sensibles/moderados (`gmail.send`, `gmail.modify`, `calendar.events`, `drive.file`). Es un proceso con evidencia y vídeo; se debe planificar con semanas de margen si se ejecuta.

## 5. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| Deliverability (spam, bouncing) | Dominio verificado con SPF/DKIM/DMARC desde el día 1; webhook de bounces; supresión automática de direcciones inválidas. |
| Exceso de correos por cada evento | Rate limit 15-min + digest diario opcional + default preferencia email OFF para eventos de baja prioridad. |
| Consentimiento (anti-spam legal) | Footer con enlace de des-suscripción de notificaciones de email por tipo de evento; comunicaciones obligatorias (seguridad) no tienen opt-out. |
| Falla del proveedor | Retries con backoff en worker; si el proveedor cae, el in-app sigue funcionando (canal independiente). |
| Migraciones cerradas | Cada migración nueva es reversible y NO se edita una cerrada (regla existente del repo). |
| Dependencia SaaS externa | Alternativa documentada: SMTP directo (config ya existe) — Knock u otro es conveniente pero no bloqueante; si no quieres SaaS externo, se puede llegar al mismo resultado con un SMTP transaccional (Mailgun/Postal/SES) manteniendo el mismo hub. |

## 6. Orden de Ejecución y Estimación

| Fase | Contenido | Estimación |
|---|---|---|
| Fase 1 | Preferencias por usuario + CRUD + UI | 2–3 días |
| Fase 2 | Hub + deliverables + proveedor email + worker + refactor de call-sites | 4–6 días |
| Fase 3 | Bandeja unificada + dedupe + digest | 3–4 días |
| Total MVP (F1+F2+F3) | ~2 semanas de trabajo enfocado | |

**Criterios de cierre global:** suite pytest + vitest verde, compila con `tsc --noEmit`, verificación en vivo HTTP 200 en rutas afectadas (`scripts/deploy_frontend.sh` para build atómico), push con `scripts/push_branch.sh` y confirmación de SHA remoto.

## 7. Próximo Paso Propuesto

1. Revisar/ajustar este plan.
2. Si está de acuerdo, arrancar **Fase 1** (preferencias + modelo + CRUD + UI) en un branch `feat/notifications-email-fase1-20261011`.
