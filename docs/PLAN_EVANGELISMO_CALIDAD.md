# Plan de Calidad — Modulo de Evangelismo CCF

> **Objetivo:** cerrar evangelismo como plataforma propia, con trabajo por capas y validacion repetible. Este plan complementa `docs/ESTADO_EVANGELISMO.md`; no reemplaza el estado canonico.

**Ejecucion 2026-07-16:** Fase 0 completada con smoke minimo verde (`18 passed, 1 xfailed`). Fase 2 tambien quedo validada con `tests/test_evangelism_module_coverage.py` en verde (`219 passed`). En consecuencia, los IDs `PARCIAL-EVENTS-001`, `PARCIAL-MULTIPLICATION-001`, `PARCIAL-FOLLOWUP-001`, `PEND-EVENTS-CONTRACT-001` y `PEND-SESSIONS-CONTRACT-001` salen del backlog activo y quedan como cierres documentados en `ESTADO_EVANGELISMO.md`. Ademas, `PARCIAL-RUNTIME-AUTH-001` avanzo: la superficie de estrategias ya quedo alineada con `require_pastor_or_admin` y deja de producir `401/403` estructurales para usuarios con solo `evangelism:read`.

## 1. Regla de trabajo

- No mezclar fixes de evangelismo con CRM, proyectos, calendario o CMS salvo que el contrato cruzado sea el origen real del fallo.
- Cada cambio debe quedar asociado a un ID estable de `ESTADO_EVANGELISMO.md`.
- Antes de editar, clasificar el problema como: auth/RBAC, contrato API, sede isolation, soft delete, serializacion, UI state, performance o datos.
- Evitar cambios cosmeticos en pantallas grandes mientras haya fallos de contrato o permisos.
- Si se toca backend y frontend en el mismo cambio, documentar el contrato que los une.

## 2. Fase 0 — Diagnostico base

**ID:** `EVANG-FASE0-DIAG`

Meta: saber si el modulo esta sano antes de corregir un fallo puntual.

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_EVANGELISMO.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_EVANGELISMO.md
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_evangelism_triple7_flow.py \
  tests/test_evangelism_crm_bridge.py \
  tests/test_evangelism_reports_api.py \
  tests/test_calculo_sesiones.py
```

Criterio de salida:

- Smoke minimo pasa.
- Si falla, abrir tarea sobre el primer fallo real antes de tocar UI.
- Ruta afectada, usuario/rol y endpoint quedan anotados.

## 3. Fase 1 — Auth, permisos y 401 runtime

**ID:** `PARCIAL-RUNTIME-AUTH-001`

Problema: pantallas como estrategia pueden disparar 401 en `/evangelism/grupos` o `/evangelism/sessions` aunque la ruta visual cargue.

Orden:

1. Confirmar token presente en frontend.
2. Confirmar rol y permiso del usuario sobre modulo `evangelism`.
3. Revisar `require_module_access("evangelism", "...")` del endpoint.
4. Confirmar que `apiFetch` envia token y no silencia un fallo que la pantalla necesita mostrar.
5. Definir si el endpoint debe ser `read`, `edit` o `manage`.

Criterio de salida:

- 401/403 se explica por rol real o se corrige en permisos.
- La UI no oculta errores estructurales.
- QA manual cubre ADMIN, GESTOR, EDITOR y MIEMBRO cuando aplique.

Estado 2026-07-16:

- Avance parcial cerrado en frontend para dashboard de estrategias, shell y detalle de estrategia.
- Pendiente validar manualmente otras rutas de evangelismo que compartan drift entre `evangelism:read` y `require_pastor_or_admin`.

## 4. Fase 2 — Contratos API y serializacion

**IDs:** `PEND-EVENTS-CONTRACT-001`, `PEND-SESSIONS-CONTRACT-001`, `PARCIAL-EVENTS-001`, `PARCIAL-FOLLOWUP-001`

Problema: la historia del modulo muestra fallos por respuestas ORM sin serializar, UUID sin convertir, aliases duplicados y codigos 400/404 inconsistentes.

Orden:

1. Correr cobertura enfocada:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py
```

2. Separar fallos por area:

- Eventos y roles: `backend/api/evangelism_events/`
- Sesiones y aliases: `backend/api/evangelism_grupos/grupos_sesiones.py`
- Asistencia/follow-up: `backend/api/evangelism_grupos/grupos_asistencias.py`
- Multiplicacion: `backend/api/evangelism_multiplication.py`

3. Corregir contrato en backend primero.
4. Ajustar frontend solo si estaba consumiendo mal el contrato real.

Criterio de salida:

- No hay `dict_type` por ORM crudo en responses.
- UUID sale como string cuando el schema lo exige.
- 400/404/403 tienen causa consistente.
- Aliases `/grupos` y `/groups` devuelven la misma forma.

## 5. Fase 3 — Sesiones, asistencia y CRM bridge

**IDs:** `PEND-SESSIONS-CONTRACT-001`, `PARCIAL-FOLLOWUP-001`

Flujo canonico:

```text
Estrategia -> Grupo -> Sesion habilitada -> Asistencia -> Seguimiento -> CasoCRM
```

Orden:

1. Validar generacion de sesiones por frecuencia.
2. Validar habilitacion/deshabilitacion individual y masiva.
3. Validar bloqueo de asistencia en sesion `DESHABILITADO`.
4. Validar asistencia con persona existente.
5. Validar visitante nuevo y creacion de caso CRM.
6. Validar follow-up pendiente y actualizacion.

Criterio de salida:

- `tests/test_evangelism_triple7_flow.py` pasa.
- `tests/test_evangelism_crm_bridge.py` pasa.
- La UI no permite guardar asistencia sobre una sesion bloqueada.

## 6. Fase 4 — Estrategia detail page

**IDs:** `PARCIAL-STRATEGY-PAGE-001`, `PEND-STRATEGY-DECOMPOSE-001`

Problema: `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` concentra demasiada logica.

Orden recomendado:

1. Extraer types locales si no rompen imports.
2. Extraer hooks de carga: estrategia, grupos, sesiones, roles, follow-up.
3. Extraer acciones: crear grupo, editar grupo, crear sesion, habilitar, guardar asistencia.
4. Extraer paneles visuales sin cambiar copy ni layout.
5. Agregar pruebas o e2e segun riesgo.

Criterio de salida:

- La page queda como orquestador.
- Los fetches siguen usando `apiFetch`.
- No cambia la ruta `/plataforma/evangelism/strategies/[id]`.
- Consola limpia en carga y acciones principales.

## 7. Fase 5 — Eventos

**IDs:** `PARCIAL-EVENTS-001`, `PEND-EVENTS-CONTRACT-001`

Orden:

1. Cerrar response schemas de `events_main.py`.
2. Cerrar roles de eventos: duplicados, locked roles y fallback.
3. Cerrar attendance y bulk attendance.
4. Cerrar visitor check-in duplicado.
5. Validar analytics y export.
6. Revisar UI de eventos despues de backend.

Criterio de salida:

- CRUD evento responde schema estable.
- Roles no permiten duplicados invalidos.
- Check-in duplicado no rompe constraint.
- Attendance history responde estructura documentada.

## 8. Fase 6 — Multiplicacion, rankings y reportes

**IDs:** `PARCIAL-MULTIPLICATION-001`

Orden:

1. Validar `/multiplication/check`.
2. Validar `/multiplication/split` con grupo inexistente, inactivo, lider invalido y pocos participantes.
3. Validar `/multiplication/history`.
4. Validar rankings de grupos, lideres y comparacion mensual.
5. Validar reportes PDF/Excel si se toca asistencia.

Criterio de salida:

- Errores esperados retornan 400/404, no 500.
- Rankings no hacen N+1 visible.
- Reportes respetan soft delete y sede.

## 9. Fase 7 — QA final y release

**ID:** `EVANG-FASE7-QA`

Comandos minimos:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_evangelism_triple7_flow.py \
  tests/test_evangelism_crm_bridge.py \
  tests/test_evangelism_reports_api.py \
  tests/test_calculo_sesiones.py
```

Si se toco frontend:

```bash
cd /root/ccf/frontend
npx playwright test tests/e2e/evangelism/sessions-detail.spec.ts tests/e2e/evangelism/rankings-multiplication.spec.ts
```

Criterio de salida:

- Smoke minimo pasa.
- Rutas QA de `EVANGELISMO_QA_CHECKLIST.md` pasan.
- `ESTADO_EVANGELISMO.md` se actualiza si cambio backlog o estado.
- Commit por fase o por unidad coherente.
