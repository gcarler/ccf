# QA Checklist — Evangelismo CCF

> **Objetivo:** validar evangelismo como módulo aislado antes de cerrar una tarea, commit o despliegue.
>
> **Última actualización:** 2026-09-27 (Certificación Integral Super-PRO Eventos — 100/100 A+)
> **Métricas:** 7/7 suites canónicas aprobadas en `scripts/test_evangelism_quality.py`, 46/46 contratos estructurales, 0 errores `tsc --noEmit`, 0 regresiones.
> **Reporte Forense:** [`docs/AUDITORIA_FORENSE_EVANGELISMO_2026-09-06.md`](file:///root/ccf/docs/AUDITORIA_FORENSE_EVANGELISMO_2026-09-06.md) y [`docs/PLAN_DE_TRABAJO_EVANGELISMO.md`](file:///root/ccf/docs/PLAN_DE_TRABAJO_EVANGELISMO.md)

## 1. Preflight

```bash
cd /root/ccf
git status --short
python3 --version && node --version
```

Confirmar:

- Los cambios sucios ajenos no se incluyen en el commit.
- Se sabe qué usuario/rol se está probando.
- La ruta afectada está identificada.
- Se consultó `docs/EVANGELISMO_RBAC_MATRIX.md` si la operación involucra 401/403 o visibilidad por rol.

## 2. Backend smoke mínimo y suites canónicas

Ejecutar el gate canónico que orquesta las 7 suites del módulo:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
```

Suites incluidas en la ejecución canónica:
1. `tests/test_evangelism_triple7_flow.py`, `crm_bridge.py`, `reports_api.py`, `calculo_sesiones.py` (Smoke base).
2. `tests/test_evangelism_habilitacion_regression.py`, `custom_role_regression.py` (Regresiones críticas).
3. `tests/test_evangelism_form_studio_pass.py` (Form Studio y Pase PDF Super-PRO).
4. `tests/test_evangelism_gatekeeper.py` (Gatekeeper Scanner, Alarma 409 y Aforo).
5. `tests/test_evangelism_post_analytics.py` (Analytics Post-Evento y Embudo CRM).
6. `tests/test_evangelism_followup_campaigns.py` (Automatización de Seguimiento y Mentores).
7. `tests/test_evangelism_cohort_retention.py` (Cohortes 30d/60d/90d, SMI y Auditoría Multi-Sede).


## 3. Backend cobertura profunda

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
| `/plataforma/evangelism/events/{id}/studio` | Event Form Studio, vista previa de formulario y enlace público |
| `/plataforma/evangelism/scanner` | Gatekeeper Scanner (cámara/físico), feedback sonoro/lumínico y aforo en vivo |
| `/plataforma/evangelism/events/{id}/analytics` | Analytics Post-Evento, Embudo de 6 etapas y canalización CRM |
| `/plataforma/evangelism/events/{id}/followup` | Campañas de seguimiento 24h-72h-7d y asignación de mentores |
| `/plataforma/evangelism/cohorts` | Análisis de Cohortes (Heatmap matrix), ranking multi-sede y exportación CSV |
| `/plataforma/evangelism/rankings` | rankings cargan sin errores de contrato |
| `/plataforma/evangelism/multiplication` | check e historial cargan |

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
| EDITOR | con `evangelism:edit` accede a lectura y operacion en superficies canonicas (incluye Gatekeeper Scanner); queda fuera de superficies que requieren `evangelism:manage` |
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

### Eventos (Suite Super-PRO)

- **Form Studio**: Configurar campos personalizados, generar enlace público y emitir pase PDF con correlativo único `#CCF-EVT-YYYY-XXXX`.
- **Gatekeeper Scanner**: Validar QR de acceso; ante reingreso duplicado verificar alarma visual/sonora y respuesta `409 duplicate_access` con detalle del primer ingreso.
- **Aforo en vivo**: Comprobar actualización instantánea de aforo y porcentaje de ocupación en `/occupancy`.
- **Analytics Post-Evento**: Visualizar embudo de conversión de 6 etapas y retención de visitantes; ejecutar canalización idempotente a CRM.
- **Seguimiento & Mentores**: Comprobar cadencia de contacto (24h/72h/7d) y balanceo automático de mentores por carga activa y zona geográfica.
- **Cohortes & LTV Espiritual**: Revisar matriz de calor mensual de retención 30d/60d/90d, puntuación de madurez espiritual (SMI 0-100) y descargar exportación CSV con UTF-8 BOM para Excel.

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
