# Plan de Saneamiento de Deuda Legacy CCF

**Fecha:** 2026-06-05
**Estado:** Plan maestro operativo
**Base obligatoria:** `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md`
**Objetivo:** retirar la deuda legacy protegida por lotes seguros hasta dejar la plataforma alineada con UUID/personas sin romper contratos vivos.

---

## 1. Principio de Trabajo

No se va a "limpiar todo" en una sola migracion.

La plataforma se deja a punto con ciclos pequenos:

1. inventario del saldo exacto;
2. contrato nuevo UUID paralelo;
3. backfill o resolucion dual;
4. migracion de consumidores;
5. tests y arranque;
6. deprecacion documentada;
7. retiro del legacy solo cuando no tenga consumidores.

Un lote no pasa a cierre si `quality_gate.py`, typecheck o smoke basico quedan peor que el baseline.

---

## 2. Baseline Antes Del Primer Lote

Antes de empezar codigo de saneamiento:

```bash
git status --short
python3 -m pytest -q -o addopts='' tests/test_smoke.py tests/test_structural_contracts.py tests/test_reglas_plataforma.py
cd frontend && npm run typecheck
python3 scripts/auditing/quality_gate.py
```

Estado observado el 2026-06-05:

- `npm run typecheck`: PASS.
- `tests/test_structural_contracts.py tests/test_reglas_plataforma.py`: PASS, `27 passed, 1 skipped`.
- `quality_gate.py`: NO EJECUTADO completo; timeout de 120s en "Backend Core Tests".
- Tests que usan `TestClient` pueden colgarse en startup en este entorno; si se repite, registrar stack con `-o faulthandler_timeout=10`.

Primer subtrabajo tecnico recomendado:

- estabilizar el arranque de `TestClient`/quality gate o clasificarlo como problema de entorno reproducible;
- no usar un gate colgado como evidencia de PASS.

---

## 3. Deuda A Retirar

### D1. `/api/auth/users/{user_id}` con `user_id:int`

Estado:

- Sigue vivo en `backend/api/auth.py`.
- Debe quedar solo como contrato legacy de autenticacion v1.
- Las superficies admin nuevas ya deben usar `/api/admin/users/{user_id}` UUID.

Objetivo:

- que ningun frontend de plataforma use `/api/auth/users/{id}` para gestion ministerial;
- mantener `/api/auth/users/{id}` solo para compatibilidad legacy hasta retiro formal.

### D2. Academy con rutas `/api/academy/users/{user_id}/...`

Estado:

- Consumidores detectados:
  - `frontend/src/hooks/useStudentEnrollments.ts`
  - `frontend/src/components/MyEnrollments.tsx`
  - `frontend/src/app/plataforma/academy/profile/progress/page.tsx`
  - `frontend/src/app/plataforma/academy/assessments/[id]/page.tsx`
  - `frontend/src/app/plataforma/academy/students/page.tsx`
  - `frontend/src/app/plataforma/academy/teachers/page.tsx`
  - `tests/test_academy_api.py`
- CRUD legacy usa `user_id:int` en `backend/crud/academy.py`.

Objetivo:

- agregar contratos por persona/auth UUID;
- migrar consumidores;
- dejar rutas legacy con aviso de deprecacion;
- retirar cuando no haya llamadas vivas.

### D3. `UserSelect` y `/api/auth/user-list`

Estado:

- `frontend/src/components/ui/UserSelect.tsx` usa `value:number` y `/api/auth/user-list`.
- Otros consumidores aun pueden esperar entero.
- `frontend/src/app/plataforma/crm/tasks/assign/page.tsx` tambien consume `/auth/user-list`.

Objetivo:

- crear selector nuevo UUID-first o migrar `UserSelect` a generico tipado;
- mover consumidores compatibles a `/api/admin/users` o a un endpoint de personas segun dominio;
- conservar wrapper legacy temporal si algun modulo requiere entero.

### D4. FKs/columnas a `users.id`

Estado:

- Persisten en CMS, Academy legacy, Identity legacy, Agents, Governance, CRM y servicios.
- Algunas representan autoria/auditoria; otras representan identidad ministerial real.

Objetivo:

- no migrar en bloque;
- clasificar cada columna como `auth_legacy`, `actor_persona`, `author_persona`, `catalog_owner` o `compat_only`;
- crear columnas UUID paralelas solo donde representen persona/actor real.

### D5. PK enteras en tablas transaccionales y modulos legacy

Estado:

- Hay muchas PK enteras, pero no todas son deuda.
- Catalogos pueden seguir enteros si estan documentados.
- Transacciones expuestas por API o ligadas a persona deben migrarse caso por caso.

Objetivo:

- separar catalogos permitidos de transacciones reales;
- migrar solo tablas con beneficio claro y ruta de rollback;
- evitar cambios de PK si basta con exponer UUID publico paralelo.

---

## 4. Orden Maestro De Ejecucion

### Lote 0: Gate y Observabilidad

Meta:

- tener una forma confiable de saber si un lote rompe la plataforma.

Acciones:

1. Diagnosticar timeout de `TestClient.__enter__` y `quality_gate.py`.
2. Separar en el gate los tests que cuelgan de los que fallan.
3. Agregar timeout interno por seccion del gate si no existe.
4. Registrar baseline exacto en `docs/CIERRE_ARQUITECTURA_CCF.md`.

Criterio de salida:

- `quality_gate.py` devuelve PASS/FAIL sin colgarse, o existe comando alterno documentado para validar lotes.

### Lote 1: Cierre De Superficie Admin/Auth Legacy

Meta:

- que administracion no dependa de `auth.users` entero.

Acciones:

1. Buscar `frontend/src` por `/auth/users` y `/auth/user-list`.
2. Migrar cualquier pantalla admin restante a:
   - `/api/admin/users` para usuarios auth UUID;
   - `/api/admin/users/{uuid}` para detalle/edicion;
   - `/api/admin/users/{uuid}/permissions` para permisos.
3. Agregar tests de contrato:
   - UUID valido: 200/204;
   - entero en endpoint admin UUID: 400;
   - `/api/auth/users/{int}` sigue vivo como legacy protegido.
4. Documentar `/api/auth/users/{user_id}` como `DEPRECATED_AUTH_V1`.

Criterio de salida:

- `rg '/auth/users' frontend/src/app/plataforma frontend/src/components` no encuentra usos nuevos, salvo allowlist documentada.
- Admin usa UUID de punta a punta.

### Lote 2: Academy Persona UUID

Meta:

- sacar enrollments/progress del contrato `user_id:int`.

Acciones:

1. Inventariar modelos Academy:
   - enrollments;
   - progress;
   - certificates;
   - attendance;
   - forum threads/comments;
   - `closed_by_user_id`.
2. Agregar helpers:
   - resolver `persona_id` desde auth UUID;
   - resolver legacy `users.id` solo para compatibilidad temporal.
3. Crear endpoints nuevos:
   - `GET /api/academy/personas/{persona_id}/enrollments`;
   - `GET /api/academy/personas/{persona_id}/progress`;
   - opcional: `GET /api/academy/me/enrollments`;
   - opcional: `GET /api/academy/me/progress`.
4. Migrar frontend:
   - `useStudentEnrollments.ts`;
   - `MyEnrollments.tsx`;
   - `academy/profile/progress/page.tsx`;
   - `academy/assessments/[id]/page.tsx`.
   - `academy/students/page.tsx`;
   - `academy/teachers/page.tsx`.
5. Mantener rutas `/api/academy/users/{user_id}/...` con resolucion dual y header/log de deprecacion.
6. Agregar tests de equivalencia: legacy y nuevo devuelven el mismo resultado para el mismo usuario vinculado.

Criterio de salida:

- ningun consumidor frontend usa `/academy/users/{user_id}/enrollments` ni `/progress`;
- rutas nuevas UUID tienen tests;
- rutas legacy quedan documentadas para retiro.

### Lote 3: Selectores De Usuario y Asignaciones

Meta:

- retirar `UserSelect` como fuente de enteros para flujos nuevos.

Acciones:

1. Inventariar consumidores de `UserSelect`.
2. Crear `PersonaSelect` o `UserSelectUuid` con:
   - `value: string | null`;
   - `onChange: (id: string | null) => void`;
   - consumo de `/api/admin/users` si selecciona cuenta auth;
   - consumo de `/api/crm/personas` si selecciona persona ministerial.
3. Migrar `crm/tasks/assign/page.tsx` a UUID si la tarea representa persona asignada.
4. Dejar `UserSelectLegacy` para modulos que todavia usen `users.id`.
5. Cambiar nombres para que el uso sea evidente:
   - `UserSelectLegacyInt`;
   - `AuthUserSelectUuid`;
   - `PersonaSelect`.

Criterio de salida:

- `UserSelect` legacy queda sin consumidores nuevos;
- cualquier uso entero queda en allowlist con razon y lote de retiro.

### Lote 4: FKs `users.id` Por Dominio

Meta:

- retirar FKs a `users.id` donde representen persona, autoria o actor ministerial.

Orden recomendado:

1. CRM:
   - `pastor_user_id` -> `pastor_id`;
   - `assignee_user_id` -> `assignee_id`;
   - `leader_user_id` -> `leader_id`.
2. Academy:
   - `user_id` en enrollment/progress/certificados;
   - `closed_by_user_id` -> `closed_by_persona_id`.
3. CMS:
   - `created_by`, `updated_by`, `author_id`, `actor_user_id`;
   - separar autoria persona de compatibilidad auth.
4. Agents/Governance:
   - `created_by`, `updated_by`, `actor_user_id`;
   - migrar a `*_persona_id` cuando represente actor humano.
5. Identity legacy:
   - refresh/reset/verification tokens pueden permanecer auth legacy hasta retirar auth v1.

Patron de migracion por columna:

1. agregar `*_persona_id UUID NULL`;
2. backfill desde `personas.user_id = users.id` o `auth_users.id = personas.id`;
3. validar cero huerfanos para filas activas;
4. adaptar writes para llenar ambas columnas;
5. adaptar reads para preferir UUID;
6. esperar un release;
7. retirar write entero;
8. retirar columna legacy en migracion posterior.

Criterio de salida:

- no quedan FKs a `users.id` que representen persona activa fuera de allowlist `auth_v1`.

### Lote 5: PK Enteras En Tablas Transaccionales

Meta:

- eliminar PK enteras solo donde aporten riesgo real o contrato publico inconsistente.

Clasificacion previa obligatoria:

- `catalogo_permitido`: puede seguir entero.
- `transaccion_interna`: puede seguir entero si no se expone como identidad publica.
- `transaccion_publica`: debe tener UUID publico o PK UUID.
- `historial/auditoria`: preferir UUID si cruza APIs o integraciones.

Estrategia preferida:

1. No cambiar PK fisica si no hace falta.
2. Agregar `public_id UUID UNIQUE NOT NULL` para contratos externos.
3. Migrar APIs/frontend a `public_id`.
4. Solo migrar PK real a UUID cuando la tabla sea nueva o el costo este justificado.

Prioridad:

1. `donations` y comprobantes externos.
2. `support_tickets` y conversaciones expuestas.
3. comentarios/adjuntos/activity logs de proyectos si se exponen por URL.
4. Academy forum/progress si se exponen por URL.
5. CMS publicable si cruza sitios/preview/API externa.

Criterio de salida:

- toda transaccion expuesta por API tiene UUID publico;
- catalogos enteros quedan documentados y fuera del gate de deuda.

### Lote 6: Retiro De Legacy

Meta:

- eliminar contratos viejos solo cuando no existan consumidores.

Acciones:

1. Agregar logs de uso a endpoints legacy.
2. Medir 1 release sin uso.
3. Bloquear nuevos consumidores con test estructural.
4. Marcar endpoint como 410 o remover segun decision.
5. Eliminar columnas legacy solo despues de backup y rollback probado.

Criterio de salida:

- `rg` y logs confirman cero consumidores;
- migracion de retiro tiene rollback;
- smoke de login, Academy, Admin, CRM y frontend pasa.

---

## 5. Tests Nuevos A Crear

### Estructurales

- `test_no_new_auth_users_frontend_consumers`
- `test_no_new_academy_user_id_frontend_consumers`
- `test_no_new_user_id_int_person_identity_params`
- `test_legacy_allowlist_has_owner_and_lote`

### Contrato API

- Admin users UUID CRUD.
- Academy persona enrollments/progress equivalentes a legacy.
- User/persona selector endpoints devuelven IDs UUID.
- Legacy endpoints devuelven header de deprecacion.

### Migraciones

- backfill cero huerfanos;
- downgrade reversible;
- columnas dual-write quedan consistentes.

---

## 6. Allowlist Temporal

Toda excepcion debe tener:

- archivo;
- linea o patron;
- razon;
- lote de retiro;
- fecha objetivo.

Allowlist inicial:

| Patron | Razon | Lote |
|---|---|---|
| `backend/api/auth.py` `/users/{user_id}` | Auth v1 legacy | Lote 1 / retiro Lote 6 |
| `frontend/src/components/ui/UserSelect.tsx` `/auth/user-list` | Selector entero compartido | Lote 3 |
| `backend/crud/identity.py user_id:int` | Identity/auth v1 | Lote 4 o retiro auth v1 |
| `backend/models_identity.py users.id` | Tokens/preferencias auth legacy | Lote 4 o retiro auth v1 |
| Catalogos con `Integer primary_key` | No toda PK entera es deuda | Lote 5 clasificacion |

---

## 7. Definicion De Plataforma A Punto

La plataforma se considera a punto cuando:

1. Admin y Academy no consumen rutas `users/{int}` para identidad ministerial.
2. Todo frontend nuevo trabaja con UUID para persona/auth user.
3. Las FKs a `users.id` restantes son solo auth v1 o catalogos documentados.
4. Toda transaccion expuesta por API tiene UUID publico o PK UUID.
5. `quality_gate.py` termina sin colgarse.
6. `npm run typecheck` pasa.
7. Tests estructurales bloquean reintroducir deuda.
8. Toda deuda remanente tiene owner documental, lote y rollback.

---

## 8. Primeros Cinco Microcambios Recomendados

1. Arreglar/aislar timeout de `quality_gate.py`.
2. Agregar tests estructurales para bloquear nuevos `/auth/users` y `/academy/users/{id}` en frontend.
3. Crear endpoints Academy UUID paralelos sin tocar legacy.
4. Migrar `useStudentEnrollments.ts` y `MyEnrollments.tsx`.
5. Crear `AuthUserSelectUuid` y migrar `crm/tasks/assign/page.tsx`.

Estos cinco pasos reducen riesgo visible sin tocar todavia FKs ni PKs fisicas.
