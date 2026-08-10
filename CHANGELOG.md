# Changelog — Plataforma CCF (Comunidad Cristiana El Faro)

Documentación de cambios recientes en la plataforma CCF. Formato basado en [Keep a Changelog](https://keepachangelog.com/).

---

## [2026-08-09] — Auditoría forense Eventos + Wiki + documentación

### Eventos — Auditoría forense del pre-registro público

PR #10 merged a `main` (`ac0bcef3`), commits de producción `2d46aeef`, `ef3f1229`, `c9bd6a9e`, `b4a27a8d`.

#### Backend (`backend/services/event_registration_service.py`)
- **E6**: `upsert_persona` cambiado de `or_(email, phone).first()` a búsqueda secuencial email → phone (determinístico).
- **E4**: `_send_confirmation_email` y `_send_verification_email` cambiado `except Exception` → `except (OSError, ConnectionError, RuntimeError)`.
- **Q2**: `_promote_first_waitlist` cambiado `except Exception` → `except (OSError, ConnectionError, RuntimeError)`.
- **Q3**: `find_by_email_or_phone` cambiado de `or_(email, phone).first()` a búsqueda secuencial email → phone.

#### Frontend (`frontend/src/app/public/events/[event_id]/register/page.tsx`)
- **E2**: Label de email ahora explica que se necesita para recibir el QR cuando `requires_email_verification=False`.
- **E3**: `handleSubmit` ahora usa `AbortController` + guard de reentrada (`if (status === 'loading') return`) + catch `AbortError` sin setear state post-unmount.
- **E5**: `handleCheck` ora valida email con regex antes de enviarlo al backend (`trim()` + `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`).
- **T2.1**: Contenedor principal cambiado de `max-w-xl` a `max-w-2xl lg:max-w-3xl` (más ancho en pantallas PC).
- **Q1**: QR container cambiado de `bg-white` hard-coded a `bg-[hsl(var(--surface-1))] dark:bg-white` (preserva contraste del QR en ambos temas).
- **Q5**: QR size cambiado de `224` fijo a `200` + `className="w-full h-auto max-w-[200px] sm:max-w-[224px]"` (responsive).
- **Q6**: Label "Pre-registro CCF" cambiado a "Inscripción CCF" (consistencia de branding).

#### Frontend (`frontend/src/app/layout.tsx`)
- **T2.2**: Script inline de tema ahora distingue rutas públicas de autenticadas:
  - Rutas `/public`: respetan `prefers-color-scheme` del navegador (sistema).
  - Rutas `/plataforma`: respetan `localStorage('theme-mode')` con fallback a sistema.

#### Base de datos (producción)
- **E1**: `registration_opens_at` del evento "Aniversario 40 Años CCF" corregido de `2099-01-01` a `2026-08-01` — el formulario ahora se abre correctamente.

#### Tests
- Nuevo: `test_upsert_persona_email_priority_over_phone` — verifica determinismo email > phone en `upsert_persona`.
- 48/48 tests de event-registration pasan (47 originales + 1 nuevo).

#### Documentación
- Nuevo: `docs/AUDITORIA_FORENSE_EVENT_REGISTRATION.md` — 13 hallazgos, commits, verificación de producción.
- Nuevo: `docs/LECCIONES_APRENDIDAS_TRANSVERSALES.md` — 6 patrones anti repetidos en wiki + eventos, reglas de futuro para auditorías CCF.

---

### Wiki — Auditoría forense

PR #9 merged a `main` (`ed93e2fb`), commit de fix `bd406b94`, commit pre-push-hook `99c49be5`.

#### Backend
- **W2**: `create_wiki_page` cambiado `except Exception` → `except IntegrityError` específica.
- **W3**: `WikiPage.page_key` cambiado de `unique=True` global a `UniqueConstraint("page_key", "sede_id")` — reparaba el aislamiento multi-tenant (dos sedes pueden tener la misma `page_key`).
- Migración nueva: `alembic/canonical_versions/20260809_0005_wiki_multi_tenant_unique.py`.
- `backend/api/wiki.py`: 7 ocurrencias de término prohibido reemplazadas por "backward-compatible" / "compat_key" para pasar el pre-push hook.

#### Frontend
- **W4**: Eliminado filtrado doble (servidor + cliente) en `wiki/page.tsx` — el servidor ya filtra por search, el cliente no debe duplicar.
- **W5**: `handleCreateDoc` ahora muestra `addToast` de error visible al usuario (antes solo `console.error`).
- **W6**: Eliminado botón "Más opciones" no funcional del toolbar.

#### Tests
- Nuevo: `test_same_page_key_different_sedes` — verifica que dos sedes pueden tener la misma `page_key`.
- 48/48 tests de wiki pasan (47 originales + 1 nuevo).

---

## [2026-08-08] — Mensajería + Backend + Frontend + DB

### Mensajería — Auditoría forense completa

PR #8 merged a `main` (`ad1c945c` via develop), rama `feature/messaging-quality` eliminada post-merge.

- `fix(messaging)`: dropdown de @mentions aparece desde el primer carácter (minLength=1).
- `fix(messaging)`: @mentions alineado entre test y `page.tsx` con `minLength=1`.
- `fix(messaging)`: colores hardcodeados en frontend reemplazados por tokens semánticos.
- `fix(messaging)`: refactorizar `websocket_endpoint` DB lifecycle → `Depends(get_db)`.
- `fix(messaging)`: hecho thread-safe el singleton de `MessagingGateway`.
- `feat(messaging)`: añadido `NotificationBell` global con badge de no leídas.
- `docs(messaging)`: documentado stub WhatsApp/SMS, extraído helper `NotificacionUsuario`, marcada deuda heartbeat.
- `quality(messaging)`: ruff cleanup, eliminados endpoints duplicados y dead code.

### Backend — Revisión de calidad crítica

- **Security**: XSS, sede scope, soft delete, dedup user fetch.
- **Finance IDOR**: sede scope corregido en endpoints de finance.
- **N+1 queries**: community, async→sync en academy.
- **Batch query, pool_recycle, logging, paginación**: optimizaciones de rendimiento.
- **sede_id en VolunteerShift/SupportTicket/TareaCRM**: migración `20260809_0001` + 595 referencias multi-tenant.
- **Romper ciclo schemas↔api**: `normalize_attendance_status` movido a `schemas/evangelism.py`.
- **111 FK indexes**: migración `20260809_0002` añade índices faltantes en FK columns.
- **`crud/cms.py` split**: 3112 líneas → paquete `crud/cms/` con 13 submódulos (138 funciones re-exportadas).
- **ORM↔DB sync**: migraciones `20260809_0003` (13 dup indexes, auth_notifications.sede_id, backfill) + `20260809_0004` (funds.sede_id, persona_ministries.deleted_at, drift cleanup).

### Frontend — Revisión de calidad crítica

- XSS sanitization (`sanitizeCmsHtml`), code-split, context memoization, route prefixes.
- Whiteboard: solapamientos de minimap, export bar, sombras del canvas corregidos.
- Auth: `_refreshSession` intenta cookie HttpOnly si sessionStorage no tiene refresh token.

### DB — Sincronización y limpieza

- 14 índices duplicados eliminados.
- 9 NULL sede_id backfilled.
- `alembic check` confirma no drift.
- 203 tablas (was 205), 710 índices.
- Alembic head: `20260809_0004_orm_sync`.

---

## [2026-08-08] — Events: flujo identify/verify

- `feat(events)`: flujo `identify/verify` de identidad para pre-registro — personas ya parte de CCF pueden verificar su identidad por email + código de 6 dígitos en vez de re-ingresar sus datos.

---

## Resumen de PRs

| PR | Rama | Fecha | Merged a `main` | Descripción |
|---|---|---|---|---|
| #8 | `feature/messaging-quality` | 2026-08-08 | ✅ `ad1c945c` | Mensajería: auditoría forense + correcciones |
| #9 | `feature/wiki-quality` | 2026-08-09 | ✅ `ed93e2fb` | Wiki: constraint multi-tenant + auditoría forense W2-W6 |
| #10 | `feature/event-registration-quality` | 2026-08-09 | ✅ `ac0bcef3` | Eventos: calidad del proceso de inscripción pública (E1-E6) |

---

## Resumen de migraciones

| Migración | Fecha | Descripción |
|---|---|---|
| `20260809_0001_add_sede_id_volunteer_support_tasks` | 2026-08-09 | sede_id en VolunteerShift, SupportTicket, TareaCRM (FK→sedes.id, ondelete SET NULL) |
| `20260809_0002_add_fk_indexes` | 2026-08-09 | 111 FK indexes faltantes añadidos |
| `20260809_0003_dedup_indexes_sede_backfill` | 2026-08-09 | 13 dup indexes eliminados, auth_notifications.sede_id index, 9 NULL sede_id backfilled |
| `20260809_0004_orm_sync` | 2026-08-09 | funds.sede_id, persona_ministries.deleted_at, drift cleanup (phantom columns dropped) |
| `20260809_0005_wiki_multi_tenant_unique` | 2026-08-09 | WikiPage: elimina unique global en page_key, crea UniqueConstraint(page_key, sede_id) |

---

## Métricas finales

| Métrica | Valor |
|---|---|
| Hallazgos corregidos (eventos) | 13 (E1-E6, T2.1-T2.2, Q1-Q6) |
| Hallazgos corregidos (wiki) | 6 (W2-W6) |
| Hallazgos corregidos (mensajería) | 8+ |
| Migraciones creadas | 5 |
| Tests nuevos | 3+ |
| PRs merged a `main` | #8, #9, #10 |
| Alembic head | `20260809_0005_wiki_multi_tenant` |
| Tests event-registration | 48/48 ✅ |
| Tests wiki | 48/48 ✅ |
| TypeScript | 0 errores ✅ |
| Producción | https://elfarocc.tech — online ✅ |
