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
| GESTOR | validar por guard real; no todo flujo pastoral/admin necesariamente equivale a `evangelism:manage` |
| EDITOR | puede quedar fuera de superficies con `require_pastor_or_admin` aunque tenga `evangelism:edit` |
| MIEMBRO | no debe acceder a acciones administrativas y solo puede entrar en superficies auth/contextuales si el flujo real lo habilita |

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

### Multiplicacion

- Ejecutar check.
- Probar split valido.
- Probar split con precondicion invalida.
- Confirmar historial.

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
