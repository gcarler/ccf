# QA Checklist — Evangelismo CCF

> **Objetivo:** validar evangelismo como modulo aislado antes de cerrar una tarea, commit o despliegue.

## 1. Preflight

```bash
cd /root/ccf
git status --short
python3 --version && node --version
grep -nE "PARCIAL-|PEND-" docs/ESTADO_EVANGELISMO.md
```

Confirmar:

- Los cambios sucios ajenos no se incluyen en el commit.
- Se sabe que usuario/rol se esta probando.
- La ruta afectada esta identificada.
- Se consulto `docs/EVANGELISMO_RBAC_MATRIX.md` si el bug involucra 401/403 o visibilidad por rol.

## 2. Backend smoke minimo

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
```

Smoke mínimo bruto:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_evangelism_triple7_flow.py \
  tests/test_evangelism_crm_bridge.py \
  tests/test_evangelism_reports_api.py \
  tests/test_calculo_sesiones.py
```

Debe pasar antes de cerrar cambios en sesiones, asistencia, reportes o CRM bridge.

## 3. Backend smoke ampliado

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py
```

Ejecutar si se toca:

- `backend/api/evangelism_events/`
- `backend/api/evangelism_grupos/`
- `backend/api/evangelism_multiplication.py`
- `backend/api/evangelism_main/`
- `backend/schemas/evangelism.py`
- `backend/models_evangelism.py`

Adicionalmente, si se toca **preregistro público, email de confirmación o QR** (`backend/api/public.py`, `backend/services/event_registration_service.py`, `backend/services/email.py`):

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_event_registration_email.py \
  tests/test_event_registrations.py \
  tests/test_event_registrations_dynamic_form.py \
  tests/test_event_registration_quality.py
```

> `tests/test_event_registration_email.py` cubre la resolución de dominio (`public_base_url → frontend_url`), la plantilla corporativa con QR embebido y el endpoint `GET /api/public/events/{id}/qr.png` (200 PNG, 404 token desconocido, 404 no-inscrito, `cancel` codificado en el contenido).

## 4. Frontend smoke

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --frontend-smoke
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
cd /root/ccf/frontend
npm run test:e2e:evangelism
npm run test:e2e:evangelism:deep
```

Nota operativa:

- `scripts/test_evangelism_quality.py --frontend-smoke` ejecuta el comando oficial del módulo desde el gate raíz.
- `scripts/test_evangelism_quality.py --frontend-deep` aísla la cobertura profunda frontend desde el gate raíz.
- Ambos comandos levantan el frontend con `webServer` administrado por Playwright.
- `test:e2e:evangelism` ejecuta smoke autenticado + cobertura profunda mockeada.
- `test:e2e:evangelism:deep` aísla sesiones, rankings, multiplication, events y scanner cuando no hace falta correr el smoke autenticado completo.

Ejecutar si se toca:

- `frontend/src/app/plataforma/evangelism/**`
- `frontend/src/components/evangelism/**`
- `frontend/src/lib/api*`
- auth/token handling que afecte plataforma

## 5. Rutas manuales

Validar con consola abierta:

| Ruta | Validar |
|---|---|
| `/plataforma/evangelism` | carga sin 404 de assets, sin errores AG Grid, sin 401 inesperado |
| `/plataforma/evangelism/strategies/{id}` | estrategia carga, tabs no disparan 401 inesperado |
| `/plataforma/evangelism/strategies/{id}/analytics` | graficas/metricas cargan o muestran estado vacio controlado |
| `/plataforma/evangelism/groups` | lista grupos visibles para el rol |
| `/plataforma/evangelism/groups/{id}` | detalle, sesiones y asistencia cargan |
| `/plataforma/evangelism/events` | lista eventos o estado vacio controlado |
| `/plataforma/evangelism/events/{id}` | detalle, tabs y asistencia |
| `/plataforma/evangelism/rankings` | rankings cargan sin errores de contrato |
| `/plataforma/evangelism/multiplication` | check e historial cargan |
| `/plataforma/evangelism/scanner` | permisos y validacion de token |

## 6. Consola del navegador

No cerrar tarea si aparece:

- `401 Unauthorized` no explicado por rol.
- `403 Forbidden` en accion que el rol debe ejecutar.
- `404 Not Found` en assets `_next/static`.
- `404 Not Found` en endpoints existentes.
- `500 Internal Server Error`.
- Errores AG Grid.
- Errores de hidratacion React.
- `TypeError` por respuesta inesperada.

## 7. Network/API

Para cada endpoint nuevo o modificado:

- Request usa `/api/evangelism` en backend o `/evangelism` via `apiFetch` en frontend.
- Token presente cuando endpoint es privado.
- Payload usa UUID string.
- Response coincide con schema documentado.
- Errores esperados son 400/403/404, no 500.
- Listados respetan sede y soft delete.
- No asumir que todo endpoint privado depende de `evangelism:*`; revisar el guard real.

## 8. Roles minimos

Validar al menos:

| Rol | Esperado |
|---|---|
| ADMIN | acceso completo en superficies del modulo |
| GESTOR | validar por guard real; con `evangelism:manage` accede a superficies canonica del modulo, no todo flujo pastoral/admin necesariamente equivale a un nivel concreto |
| EDITOR | con `evangelism:edit` accede a lectura y operacion en superficies canonicas; queda fuera de superficies que requieren `evangelism:manage` (creacion/eliminacion/estrategia) |
| MIEMBRO | no debe acceder a acciones administrativas y solo puede entrar en superficies auth/contextuales si el flujo real lo habilita |

> Tras la migracion RBAC radical (cerrada el 2026-07-17 + wrapper legacy eliminado el 2026-07-21), `require_pastor_or_admin` no gobierna ninguna superficie de evangelismo. Toda la matriz opera con la taxonomia `evangelism:read/edit/manage` mas el bypass por rol (`pastor` = total, `coordinador` = read/edit) definido en `permissions.py`. No hay superficie evangelism donde `EDITOR` con `evangelism:edit` quede fuera por tener el nombre historico del guard equivocado.

Si el comportamiento real difiere, actualizar `EVANGELISMO_API_CONTRACTS.md`, `EVANGELISMO_RBAC_MATRIX.md` o corregir permisos.

## 9. Flujos funcionales

### Estrategia y sesiones

- Abrir estrategia.
- Crear o identificar grupo activo.
- Generar sesion.
- Habilitar sesion.
- Registrar asistencia.
- Ver reflejo en metricas.

### Visitante y CRM bridge

- Registrar visitante desde asistencia o evento.
- Confirmar que persona usa UUID.
- Confirmar caso CRM sin pipeline/etapa hardcodeados.
- Confirmar follow-up pendiente si aplica.

### Eventos

- Crear evento.
- Abrir detalle.
- Registrar asistencia/check-in.
- Validar duplicado controlado.
- Revisar analytics/export si aplica.

### Preregistro público → email con QR → check-in (añadido 2026-08-21)

Flujo completo del CTA de `/aniversario40` y de la sección 7 del `RUNBOOK_PRODUCCION.md`:

- **Registro público**: `POST /api/public/events/{id}/register` con el `form_data` del formulario dinámico vinculado → `CONFIRMED` (o `WAITLIST` si `capacity_max` lleno) y rol contextual (`VISITANTE_EVENTO`, etc.). Idempotente: repetir con el mismo email no duplica.
- **Validación del form**: 422 si `form_data` no cumple el contrato del `CmsForm`; 404 si el form está inactivo/eliminado; 400 captcha si `form.captcha_enabled`.
- **Email de confirmación corporativo**: plantilla `render_event_confirmation_email` con layout `_brand_wrap`, QR embebido como `<img>`, botón “Abrir mi código QR” y link de cancelación (72h). Verificar en el HTML que los links usan el dominio canónico (`https://ministerioselfaro.org`) y **no** contienen `https://ccf.co` (placeholder) ni URLs relativas.
- **QR PNG**: `GET /api/public/events/{id}/qr.png?token=…&cancel=…` → `200 image/png` (PNG válido) con token real; `404` con token inválido; `409` si la inscripción no está `CONFIRMED`/`CHECKED_IN`.
- **Ticket**: `GET /api/public/events/{id}/ticket?token=…` → `200` con estado y rol contextual (hash-bound, el token plano nunca se persiste).
- **Check-in contextual**: `POST /api/evangelism/events/{id}/sessions/{fecha}/ccf-evt-checkin` con JWT de `evangelism:edit` **de la sede del evento** → `CHECKED_IN` + `EventAttendance(role_at_event)`; repetir → `is_duplicate=True`.
- **Reenviar QR (admin)**: `POST …/registrations/{reg_id}/resend-confirmation` → el email reenviado debe llevar URL absoluta con el dominio canónico (nunca relativa).
- **Cancelación y waitlist**: `POST /api/public/events/{id}/cancel?token=…` (token 72h) libera el cupo y promueve el siguiente `WAITLIST` con su propio email de confirmación.

Smoke E2E reproducible: pasos 1–4 de `RUNBOOK_PRODUCCION.md` §7.5 (registro → ticket → qr.png → check-in → limpieza de datos de prueba).

### Multiplicacion

- Ejecutar check.
- Probar split valido.
- Probar split con precondicion invalida.
- Confirmar historial.

### Soft-delete y cross-sede (auditoria forense 2026-07-26)

- Validar que `actualizar_participante`, `submit_asistencia`, `remover_participante` excluyen registros eliminados.
- Validar que `add_groups_attendance` (asistencia masiva) excluye personas eliminadas en la branch `persona_ids`.
- Validar que `_count_personas` y `split_group` en multiplicacion excluyen registros eliminados.
- Validar que la sesion en `submit_asistencia` usa `SesionGrupo.deleted_at.is_(None)`.
- Validar que endpoints GET de multiplicacion (`check`, `history`) usan `require_evangelism_read`, no `manage`.
- Validar que eventos cross-sede retornan 404 (no 403) para usuarios de otra sede.

## 10. Criterio de cierre

Una tarea de evangelismo queda cerrada cuando:

- Smoke relevante pasa.
- Rutas afectadas se probaron manualmente o con e2e.
- Consola queda limpia de errores nuevos.
- El documento canonico se actualizo si cambio estado/backlog/contrato.
- La matriz RBAC se actualizo si cambio el guard real o la lectura por rol.
- Commit incluye solo archivos de la unidad trabajada.
- Push pasa pre-push.

## 11. Pendientes QA / deuda reconocida

- `PEND-FRONTEND-E2E-EVANGELISM-001` cerrada el 2026-07-16 con `frontend/tests/e2e/evangelism/smoke.spec.ts`
- `PEND-FRONTEND-E2E-EVANGELISM-DEEP-001` cerrada el 2026-07-16 con `frontend/tests/e2e/evangelism/sessions-detail.spec.ts` y `frontend/tests/e2e/evangelism/rankings-multiplication.spec.ts`
- `PEND-FRONTEND-E2E-EVANGELISM-EVENTS-SCANNER-001` cerrada el 2026-07-16 con `frontend/tests/e2e/evangelism/events-scanner.spec.ts`
- `PEND-EXPAND-SMOKE-EVANGELISM-001` cerrada el 2026-07-16 con `scripts/test_evangelism_quality.py`
