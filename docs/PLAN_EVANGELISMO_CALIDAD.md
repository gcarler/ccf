# Plan de Calidad — Modulo de Evangelismo CCF

> **Objetivo:** cerrar evangelismo como plataforma propia, con trabajo por capas y validacion repetible. Este plan complementa `docs/ESTADO_EVANGELISMO.md`; no reemplaza el estado canonico.

**Ejecucion 2026-07-16:** el modulo ya no tiene backlog activo en contratos backend de eventos, sesiones, follow-up o multiplicacion. El smoke minimo verde (`18 passed, 1 xfailed`), la suite amplia (`219 passed`), el smoke frontend base (`frontend/tests/e2e/evangelism/smoke.spec.ts`), la cobertura profunda de sesiones/rankings/multiplication/events/scanner y el gate `./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep` dejan el trabajo abierto concentrado en tres frentes: QA runtime de permisos, descomposicion de la pantalla de estrategia y busqueda remota de personas.

**Trabajo activo 2026-07-16:**

- `PARCIAL-RUNTIME-AUTH-001`
- `PARCIAL-STRATEGY-PAGE-001`
- `PEND-STRATEGY-DECOMPOSE-001`
- `PEND-PERSONAS-SEARCH-001`

## 1. Regla de trabajo

- No mezclar fixes de evangelismo con CRM, proyectos, calendario o CMS salvo que el contrato cruzado sea el origen real del fallo.
- Cada cambio debe quedar asociado a un ID estable de `ESTADO_EVANGELISMO.md`.
- Antes de editar, clasificar el problema como: auth/RBAC, contrato API, sede isolation, soft delete, serializacion, UI state, performance o datos.
- Evitar cambios cosmeticos en pantallas grandes mientras haya deuda de permisos runtime o deuda estructural abierta.
- Si se toca backend y frontend en el mismo cambio, documentar el contrato que los une.

## 2. Fase 0 — Diagnostico base

**ID:** `EVANG-FASE0-DIAG`

Meta: confirmar que el modulo sigue sano antes de abrir una nueva unidad de trabajo.

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_EVANGELISMO.md
cat docs/EVANGELISMO_API_CONTRACTS.md
cat docs/EVANGELISMO_RBAC_MATRIX.md
cat docs/EVANGELISMO_QA_CHECKLIST.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_EVANGELISMO.md
./venv/bin/python scripts/test_evangelism_quality.py
```

Criterio de salida:

- El estado canonico, contratos y matriz RBAC fueron leidos antes de editar.
- El smoke canonico pasa.
- Si falla, se abre trabajo sobre el primer fallo real antes de tocar UI.
- Ruta afectada, rol y endpoint quedan anotados.

## 3. Fase 1 — QA runtime de permisos

**ID:** `PARCIAL-RUNTIME-AUTH-001`

Problema: la superficie de estrategias ya fue alineada con `require_pastor_or_admin`, pero aun falta cerrar QA manual y revisar si existen otras pantallas de evangelismo con drift entre lo que la UI intenta cargar y el guard real del backend.

Orden:

1. Verificar el guard real en `docs/EVANGELISMO_RBAC_MATRIX.md` antes de tratar un `401/403` como bug.
2. Probar manualmente `/plataforma/evangelism`, `/groups`, `/events`, `/rankings`, `/multiplication` y `/scanner` con al menos ADMIN y un rol restringido.
3. Confirmar si la UI debe ocultar la accion, mostrar estado restringido o permitir flujo parcial.
4. Si hay drift, corregir primero la capa propietaria:
   - frontend si el fetch sobra para ese rol
   - backend si el guard real es el incorrecto
5. Actualizar docs solo si cambia la lectura por rol o el contrato operativo.

Criterio de salida:

- Todo `401/403` nuevo queda explicado por rol real o corregido.
- La UI no dispara fetches estructuralmente prohibidos para la pantalla/rol.
- QA cubre al menos ADMIN y un rol no pastoral sobre las rutas afectadas.

## 4. Fase 2 — Descomposicion de estrategia

**IDs:** `PARCIAL-STRATEGY-PAGE-001`, `PEND-STRATEGY-DECOMPOSE-001`

Problema: `frontend/src/app/plataforma/evangelism/strategies/[id]/page.tsx` concentra demasiada logica y sigue siendo la pieza mas sensible del modulo.

Orden recomendado:

1. Congelar contrato actual de datos y acciones antes de extraer.
2. Extraer hooks de carga: estrategia, grupos, sesiones, roles y follow-up.
3. Extraer acciones mutantes: crear grupo, editar grupo, crear sesion, habilitar y guardar asistencia.
4. Extraer paneles visuales sin cambiar copy, permisos ni layout.
5. Agregar prueba enfocada o e2e adicional segun el riesgo del bloque extraido.

Criterio de salida:

- La page queda como orquestador y no como archivo monolitico.
- Los fetches siguen usando `apiFetch`.
- No cambia la ruta `/plataforma/evangelism/strategies/[id]`.
- Consola limpia en carga y acciones principales.

## 5. Fase 3 — Busqueda remota de personas

**ID:** `PEND-PERSONAS-SEARCH-001`

Problema: el flujo de asistencia necesita evolucionar a busqueda remota con debounce para volumen alto sin romper el contrato de `personas.id` UUID ni los permisos contextuales.

Orden:

1. Revisar `GET /evangelism/personas/search` y confirmar filtros/shape real del response.
2. Definir debounce, cancelacion de requests y estados vacio/cargando/error en frontend.
3. Sustituir busqueda local donde el volumen haga inviable el flujo actual.
4. Validar que el alta de visitante y la seleccion de persona existente siguen apuntando a UUID.
5. Cubrir al menos el caso feliz y un caso de respuesta vacia o error controlado.

Criterio de salida:

- La busqueda remota evita listas locales pesadas.
- No aparecen duplicados por shape inconsistente.
- Asistencia y CRM bridge siguen funcionando sobre persona existente o visitante nuevo.

## 6. Fase 4 — Smoke canonico integrado

**IDs:** `PARCIAL-SMOKE-EVANGELISM-001`, `PEND-EXPAND-SMOKE-EVANGELISM-001`

Estado 2026-07-16: cerrada. `scripts/test_evangelism_quality.py` ya valida smoke minimo y regresiones criticas, y ahora tambien expone gates frontend oficiales vía `--frontend-smoke`, `--frontend-deep` y `--expanded`.

Orden:

1. Mantener `scripts/test_evangelism_quality.py` como punto de entrada canonico.
2. Integrar de forma controlada la suite amplia cuando el cambio toque contratos sensibles:
   - `tests/test_evangelism_module_coverage.py`
3. Integrar el smoke frontend ya disponible:
   - `frontend/tests/e2e/evangelism/smoke.spec.ts`
   - `frontend/tests/e2e/evangelism/sessions-detail.spec.ts`
   - `frontend/tests/e2e/evangelism/rankings-multiplication.spec.ts`
   - `frontend/tests/e2e/evangelism/events-scanner.spec.ts`
4. Definir cuando el script debe correr suites pesadas siempre y cuando solo en modo expandido.
5. Documentar la matriz minima: smoke rapido, smoke ampliado backend y smoke frontend.

Criterio de salida alcanzado:

- Existe una ruta canonica clara para validacion rapida y otra para validacion ampliada.
- Evangelismo ya no depende de memoria operativa para saber que suites correr.
- QA y `ESTADO_EVANGELISMO.md` apuntan al mismo comando/flujo.

## 7. Fase 5 — QA final y cierre por unidad

**ID:** `EVANG-FASE5-QA`

Comandos minimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
```

Si se toca backend estructural:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' tests/test_evangelism_module_coverage.py
```

Si se toca frontend:

```bash
cd /root/ccf/frontend
npm run test:e2e:evangelism
npm run test:e2e:evangelism:deep
```

Regla:

- La cobertura profunda de evangelismo corre sobre `webServer` administrado; no depende de arrancar `next dev` a mano.

Criterio de salida:

- Smoke relevante pasa segun la capa tocada.
- Rutas QA de `EVANGELISMO_QA_CHECKLIST.md` pasan para la unidad trabajada.
- `ESTADO_EVANGELISMO.md` se actualiza si cambio backlog o estado.
- `EVANGELISMO_API_CONTRACTS.md` o `EVANGELISMO_RBAC_MATRIX.md` se actualizan si cambio contrato o guard real.
- Commit por fase o por unidad coherente.

## 8. Historial reciente que ya no bloquea el plan

- `PARCIAL-EVENTS-001` cerrado operativamente el 2026-07-16.
- `PARCIAL-MULTIPLICATION-001` cerrado operativamente el 2026-07-16.
- `PARCIAL-FOLLOWUP-001` cerrado operativamente el 2026-07-16.
- `PEND-EVENTS-CONTRACT-001` cerrado operativamente el 2026-07-16.
- `PEND-SESSIONS-CONTRACT-001` cerrado operativamente el 2026-07-16.
- `PEND-RBAC-EVANGELISM-001` cerrado documentalmente el 2026-07-16.
- `PEND-FRONTEND-E2E-EVANGELISM-001` cerrado el 2026-07-16 con `frontend/tests/e2e/evangelism/smoke.spec.ts`.
- `PEND-FRONTEND-E2E-EVANGELISM-EVENTS-SCANNER-001` cerrado el 2026-07-16 con `frontend/tests/e2e/evangelism/events-scanner.spec.ts`.
- `PARCIAL-SMOKE-EVANGELISM-001` cerrado operativamente el 2026-07-16 con `scripts/test_evangelism_quality.py`.
- `PEND-EXPAND-SMOKE-EVANGELISM-001` cerrado operativamente el 2026-07-16 con `scripts/test_evangelism_quality.py`.
