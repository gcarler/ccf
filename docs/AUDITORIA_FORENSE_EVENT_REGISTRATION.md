# Auditoría Forense — Inscripción Pública a Eventos

**Fecha:** 2026-08-09 (revisado 2026-08-21)

---

## Alcance auditado

- Frontend: `frontend/src/app/public/events/[event_id]/register/page.tsx` (984 LOC)
- Backend API: `backend/api/public.py` (989 LOC) — endpoints públicos
- Backend service: `backend/services/event_registration_service.py` (1036 LOC)
- Tests: `tests/test_event_registrations.py` (685 LOC), `tests/test_event_registration_quality.py`, `tests/test_event_registrations_dynamic_form.py`
- Docs de referencia: `docs/PLAN_PREREGISTRO_EVENTOS_MASIVOS.md`, `docs/PLAN_CLASIFICADOR_CONTEXTUAL_PERSONAS_EVENTO.md`
- URL de producción: `https://elfarocc.tech/public/events/cc47a8e0-333a-40c9-ba17-d90c54fff2cb/register`

---

## Validaciones ejecutadas

| Validación | Resultado |
|---|---|
| Tests backend | **48/48 passed** (antes y después de cambios) |
| TypeScript | **0 errores** |
| Build Next.js | **OK** |
| Producción (PM2) | **Backend + Frontend online, HTTP 200** |
| Pre-push hook (structural contracts) | **OK** |

---

## Resultados — 13 hallazgos corregidos

### Grupo A: Auditoría forense inicial (E1-E7)

**PR #10 merged a `main`** (`ac0bcef3`), commit de fix `f51683cd`.

| # | Severidad | Archivo | Hallazgo | Fix |
|---|---|---|---|---|
| **E1** | Medio (datos) | BD producción | `registration_opens_at = 2099-01-01` — el formulario nunca se abriría | `UPDATE crm_events SET registration_opens_at = '2026-08-01'` en BD de producción |
| **E2** | Medio | `[event_id]/register/page.tsx:707` | Cuando `requires_email_verification=False`, el email quedaba opcional sin explicar que se necesita para recibir el QR | Mensaje explicativo "Te lo enviaremos para que recibas tu código QR de asistencia" |
| **E3** | Medio | `[event_id]/register/page.tsx:361` | `handleSubmit` sin `AbortController` — si el usuario navega fuera durante el POST, el callback actualiza estado desmontado (React warning) | `AbortController` + `signal: controller.signal` en `apiFetch` + guard `if (status === 'loading') return` + catch `AbortError` sin setear state |
| **E4** | Bajo | `event_registration_service.py:546,577` | `_send_confirmation_email` y `_send_verification_email` capturaban `except Exception` genérica — enmascara bugs de programación como "éxito silencioso" | `except (OSError, ConnectionError, RuntimeError)` — cubre SMTP sin capturar AttributeError/NameError/ImportError |
| **E5** | Bajo | `[event_id]/register/page.tsx:582` | `handleCheck` no validaba el formato del email antes de enviarlo al backend | `trim()` + regex `/^[^\s@]+@[^\s@]+\.[^\s@]+$/` + guard `if (checking) return` |
| **E6** | Medio | `event_registration_service.py:190-197` | `upsert_persona` usaba `or_(email==.., phone==..).first()` — orden no determinístico; si email match persona A y phone match persona B, toma cualquiera | Búsqueda secuencial: email primero (`db.query.filter(email==..).first()`); si None y hay phone, buscar por phone |
| **E7** | — | `[event_id]/register/page.tsx:769` | Botón submit no indica "aforo ilimitado" cuando `capacity_max` es NULL | **Decidido no tocar** — UX menor, el usuario entiende "Confirmar Registro" |

**Test nuevo**: `test_upsert_persona_email_priority_over_phone` — verifica determinismo email > phone.

### Grupo B: Vista adaptativa + tema (T2)

Commits `2d46aeef` + `ef3f1229`.

| # | Archivo | Hallazgo | Fix |
|---|---|---|---|
| **T2.1** | `[event_id]/register/page.tsx:906` | `max-w-xl` (672px) — muy estrecho en pantallas de PC | `max-w-2xl lg:max-w-3xl` (672px → 768px → 1024px en large) |
| **T2.2** | `layout.tsx:74-90` | Script inline forzaba `data-theme='night'` del `localStorage('theme-mode')` en TODAS las rutas — el usuario en tema día veía el formulario en oscuro | Rutas `/public`: respetan `prefers-color-scheme` del sistema. Rutas `/plataforma`: respetan `localStorage('theme-mode')` con fallback a sistema |

### Grupo C: Calidad QR + formulario (Q1-Q6)

Commit `c9bd6a9e`.

| # | Severidad | Archivo | Hallazgo | Fix |
|---|---|---|---|---|
| **Q1** | Medio | `[event_id]/register/page.tsx:137` | QR container `bg-white` hard-coded — en tema oscuro el QR queda ilegible (QR negro sobre negro) | `bg-[hsl(var(--surface-1))] dark:bg-white` — preserva contraste del QR en ambos temas |
| **Q2** | **Alto** | `event_registration_service.py:773` | `_promote_first_waitlist` email failure con `except Exception` — mismo anti-patrón que E4 pero peor (afecta promoción de waitlist) | `except (OSError, ConnectionError, RuntimeError)` |
| **Q3** | Medio | `event_registration_service.py:796-801` | `find_by_email_or_phone` usaba `or_(email, phone)` no determinístico — **mismo bug que E6** pero en la consulta pública de estado | Búsqueda secuencial email → phone |
| **Q5** | Bajo | `[event_id]/register/page.tsx:141` | QR `size={224}` fixed — no responsive (corta en móvil, pequeño en desktop) | `size={200}` + `className="w-full h-auto max-w-[200px] sm:max-w-[224px]"` |
| **Q6** | Bajo | `[event_id]/register/page.tsx:912` | Label "Pre-registro CCF" inconsistente con branding actual | → "Inscripción CCF" |

---

## Commits y PRs

| Commit | Contenido | En `main` | En producción |
|---|---|---|---|
| `f51683cd` | fix(events): calidad del proceso de inscripción pública (E1-E6) | ✅ PR #10 | ✅ |
| `2d46aeef` | fix(events): vista adaptativa + tema correcciones (T2.1+T2.2) | pendiente | ✅ |
| `ef3f1229` | fix(layout): simplificar tema en rutas públicas | pendiente | ✅ |
| `c9bd6a9e` | fix(events): calidad forense QR + formulario registro (Q1-Q6) | pendiente | ✅ |

---

## Verificación de producción

| Verificación | Resultado |
|---|---|
| URL register page | HTTP 200, 52ms ✅ |
| Event API `is_open: true` | ✅ |
| `capacity_remaining: 300` | ✅ |
| Theme script (`isPublicRoute` + `prefersDark`) | ✅ en producción |
| Label "Inscripción CCF" | ✅ en JS bundle |
| QR `dark:bg-white` | ✅ en JS bundle |
| QR `max-w-[200px]` responsive | ✅ en JS bundle |
| Backend health | HTTP 200 ✅ |
| Status endpoint (no inscripción) | 404 correcto ✅ |
| Register validation (sin datos) | 422 correcto ✅ |
| Tests backend | 48/48 ✅ |
| TypeScript | 0 errores ✅ |
| PM2 | Backend + Frontend online ✅ |

---

## Patrón transversal — OR-ambiguity

El bug E6 (`upsert_persona`) y el bug Q3 (`find_by_email_or_phone`) son el **mismo patrón anti**: buscar por múltiples claves débiles con `or_(*conditions).first()` produce un resultado no determinístico cuando dos registros distintos comparten partes del identificador.

**Patrón correcto**: en upserts/lookups por email + phone, hacer consultas **SECUENCIALES** con prioridad explícita (email > phone), no OR:

```python
# ANTI-patrón (no determinístico):
persona = db.query(Persona).filter(or_(Persona.email == email, Persona.phone == phone)).first()

# Patrón correcto (determinístico email → phone):
persona = None
if email:
    persona = db.query(Persona).filter(Persona.email == email).first()
if persona is None and phone:
    persona = db.query(Persona).filter(Persona.phone == phone).first()
```

**Rationale**: el email es un identificador personal fuertemente ligado (uno por persona humana); el phone puede compartirse entre familiares. El email gana prioridad porque editar la Persona seleccionada no debe pisar la identidad de otra (la cual está asociada con el phone).

---

## Patrón transversal — `except Exception` en I/O best-effort

Los bug E4, Q2 y W2 (wiki) son el **mismo patrón anti**: capturar `Exception` genérica en operaciones de I/O best-effort (email, push) enmascara bugs de programación como "éxito silencioso".

**Patrón correcto**: especificar las familias de excepción de runtime relevantes al I/O:

```python
# ANTI-patrón (enmascara bugs):
except Exception as exc:
    log.warning("Failed to send email: %s", exc)

# Patrón correcto (SMTP/SMTPConnectionError hereda OSError):
except (OSError, ConnectionError, RuntimeError) as exc:
    log.warning("Failed to send email: %s", exc)
```

- `OSError`: cubre `SMTPException`, `SMTPConnectionError`, `socket.error`
- `ConnectionError`: cubre fallos de red subyacentes
- `RuntimeError`: cubre fallos de formato de plantilla
- NO captura: `AttributeError`, `NameError`, `ImportError` (bugs de programación)

---

## Follow-up 2026-08-21 — Email de confirmación con QR (3 defectos corregidos)

La auditoría original no cubría el **contenido del email de confirmación** (solo el envío best-effort). Revisión de producción encontró y corrigió 3 defectos, validados con 70 tests (11 nuevos en `tests/test_event_registration_email.py`) y smoke E2E en vivo:

| # | Defecto | Impacto | Fix |
|---|---|---|---|
| E-EMAIL-01 | `Settings` no definía `public_base_url` → el link del QR en el email caía siempre a `https://ccf.co` (dominio placeholder ajeno) pese a tener `frontend_url=https://ministerioselfaro.org` | Enlace del QR roto en producción | Setting `public_base_url` en `backend/core/config.py` (vacío → `frontend_url`); `_settings_public_base_url()` y `resolve_public_base_url()` ya nunca devuelven el placeholder |
| E-EMAIL-02 | `resend_confirmation` (admin) pasaba `public_base_url=""` → email reenviado con URL **relativa** (inutilizable) | Reenvío de QR inservible | El admin router usa `resolve_public_base_url()`; idem `_promote_first_waitlist` |
| E-EMAIL-03 | Plantilla sin marca corporativa; el QR era solo texto “descargar” pese a decir “guarda este QR” | Baja conversión y riesgo de que el inscrito no lleve el QR | `render_event_confirmation_email` en `backend/services/email.py` con layout `_brand_wrap`, **QR embebido como imagen** (nuevo endpoint público `GET /api/public/events/{id}/qr.png`, hash-bound, dependencia `qrcode`) + botón “Abrir mi código QR” + link de cancelación |

**Validación en vivo 2026-08-21** (entorno `environment=staging` local): registro público real → `CONFIRMED` → `GET /ticket` 200 → `GET /qr.png` 200 `image/png` (930×930) → `POST …/ccf-evt-checkin` con JWT de la sede del evento → `CHECKED_IN` + `EventAttendance(role_at_event)` → idempotencia `is_duplicate=True` → limpieza completa de datos de prueba.
