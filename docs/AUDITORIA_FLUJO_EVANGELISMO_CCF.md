# Auditoria de Flujo Evangelismo CCF

Fecha: 2026-06-04

## Alcance

Auditoria de continuidad de datos del componente Evangelismo, desde base de datos hasta frontend:

- modelos y relaciones: `models_evangelism.py`;
- esquemas y contratos: `schemas/evangelism.py`;
- endpoints: `backend/api/evangelism*.py`;
- CRUD y servicios: `crud/evangelism.py`, `services/evangelism_*`;
- pantallas plataforma: `frontend/src/app/plataforma/evangelism/**`;
- integracion CRM: creacion de casos por primera vez o seguimiento.

## Flujo Canonico

1. Estrategia: `estrategias_evangelismo.id` es string UUID y se filtra por `sede_id`.
2. Grupo: `grupos_evangelismo.estrategia_id` apunta a la estrategia y conserva `sede_id`.
3. Sesion: `sesiones_grupo.grupo_id` pertenece a un grupo de la misma sede.
4. Habilitacion: solo sesiones `HABILITADO` aceptan asistencia.
5. Asistencia: `asistencias.persona_id` usa `personas.id` UUID.
6. CRM bridge: primera vez o seguimiento crea `CasoCRM` en pipeline de nuevos visitantes.
7. Frontend: las vistas bajo `/plataforma/evangelism` consumen `/api/evangelism/**` via `apiFetch`.

## Correcciones Aplicadas

- `DELETE /evangelism/sessions/{session_id}` ya usa `db.commit()` y soft-delete real (`deleted_at`) en vez de `db.session.commit()`.
- `GET /evangelism/strategies/{strategy_id}/metrics` acepta UUID string de estrategias.
- Listado, detalle, update, delete y asistencia de sesiones filtran por `sede_id` y excluyen registros `deleted_at`.
- Creacion de sesiones valida que el grupo exista, pertenezca a la sede del usuario y no este eliminado.
- Habilitar/deshabilitar todas las sesiones de una estrategia queda limitado a la sede del usuario.
- La ruta FARO `/evangelism/faro/sessions/{id}/attendance` respeta la misma regla de habilitacion que `/evangelism/sessions/{id}/attendance`.
- El resumen de asignaciones FARO ya no calcula participantes asignados globalmente; filtra por grupos de la sede actual.
- Navegaciones frontend que salian a `/evangelism/...` fueron corregidas a `/plataforma/evangelism/...`.
- La creacion de casos CRM desde eventos y FARO ya no usa `pipeline_id=1` ni `etapa_actual_id=1`; reutiliza el resolvedor canonico de pipeline de nuevos visitantes.
- Los hilos de campanas, eventos y participantes esperados filtran por `sede_id` cuando construyen audiencias o tableros.
- Los estados de asistencia se normalizan desde un helper compartido.
- Reportes y rankings de evangelismo cargan asistencia, miembros y conteos con consultas por lotes o agregaciones, evitando N+1 en los caminos principales.
- Las acciones destructivas del frontend usan `ConfirmActionDrawer` y no `window.confirm` / `confirm`.
- La vista de detalle de estrategia redujo la precarga de personas para asistencia de `limit=1000` a consulta paginada de 200 registros ordenados.
- El flujo `estrategia triple 7` queda cubierto por prueba de regresion: estrategia geografica relacional semanal, grupos `g1` a `g4`, 10 personas por grupo, generacion semanal, habilitacion y registro de asistencia semana a semana.
- El trigger de ausencias recurrentes ya no referencia `current_user` fuera de alcance; recibe `sede_id` desde el endpoint de asistencia y consulta participantes activos reales.
- La habilitacion manual de una sesion ahora valida `sede_id`, `deleted_at` de grupo y `deleted_at` de sesion.
- El contador de miembros de grupo al reemplazar participantes ya excluye participantes soft-deleted.
- El frontend de roles personalizados usa el contrato real `nombre_rol` y envia `estrategia_id` UUID, no el codigo de estrategia.
- El frontend FARO crea sesiones con el identificador canonico de grupo.
- Las sesiones FARO creadas desde temporada quedan habilitadas para reporte y retornan `session_ids`.
- La vista FARO bloquea acciones de asistencia cuando la sesion no esta `HABILITADO`, evitando 403 esperables en runtime.
- El detalle de grupo devuelve `estado_habilitacion` y excluye participantes/sesiones soft-deleted.

## Deudas Cerradas

### P1 - Integracion CRM con IDs hardcodeados

Estado: cerrado.

El helper `crear_caso_nuevo_visitante` centraliza la creacion del caso y resuelve pipeline/etapa por sede. La busqueda estatica no encuentra `pipeline_id=1` ni `etapa_actual_id=1` en los hilos de evangelismo.

### P1 - Consultas globales sin sede

Estado: cerrado en los caminos auditados.

Los resolvedores de audiencia y eventos ahora reciben o derivan `sede_id`, y los endpoints de eventos validan acceso por sede antes de leer, modificar o eliminar.

### P2 - N+1 en reportes y detalle

Estado: cerrado en reportes/rankings principales.

Los reportes de asistencia, resumen de estrategia y rankings usan precargas por lote y agregaciones por `grupo_id`/`session_id`.

### P2 - Contratos mixtos de estado de asistencia

Estado: cerrado para lectura, metricas y rankings.

`evangelism_shared.py` define constantes y funciones de normalizacion reutilizadas por reportes, rankings, metricas y triggers de primera vez.

### P2 - Frontend todavia usa confirmaciones nativas

Estado: cerrado.

La busqueda estatica no encuentra `window.confirm` ni `confirm(` bajo `frontend/src/app/plataforma/evangelism` y `frontend/src/components/evangelism`.

## Riesgo Residual

- La normalizacion canonica de escritura podria reforzarse mas adelante con un enum unico en esquemas para impedir variantes de clientes futuros.
- La busqueda de personas en asistencia sigue siendo local sobre la primera pagina; para volumen alto conviene evolucionarla a busqueda remota por texto con debounce.
- Las sesiones generadas por frecuencia nacen `DESHABILITADO`; el flujo correcto exige habilitarlas antes de reportar asistencia. La prueba valida que el bloqueo ocurra y que luego la asistencia se pueda guardar al habilitar.

## Validaciones Ejecutadas

- `python3 -m py_compile` sobre modulos criticos de evangelismo: OK.
- `python3 -m pytest -q -o addopts='' tests/test_evangelism_crm_bridge.py tests/test_evangelism_reports_api.py`: OK, `11 passed, 1 xfailed`.
- `python3 -m pytest -q -o addopts='' tests/test_evangelism_triple7_flow.py`: OK, `1 passed`.
- `python3 -m pytest -q -o addopts='' tests/test_evangelism_triple7_flow.py tests/test_evangelism_crm_bridge.py tests/test_evangelism_reports_api.py`: OK, `12 passed, 1 xfailed`.
- `python3 -m pytest -q -o addopts='' tests/test_evangelism_triple7_flow.py tests/test_evangelism_crm_bridge.py tests/test_evangelism_reports_api.py tests/test_calculo_sesiones.py`: OK, `17 passed, 1 xfailed`.
- `npm run typecheck`: OK.
- `python3 -m pytest -q -o addopts='' tests/test_reglas_plataforma.py tests/test_structural_contracts.py tests/test_smoke.py`: OK, `29 passed, 1 skipped`.
- `python3 scripts/auditing/quality_gate.py`: OK, `CALIDAD TOTAL ALCANZADA`.
- `git diff --check`: OK.
