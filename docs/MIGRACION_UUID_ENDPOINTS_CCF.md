# Migracion UUID por Endpoints CCF

**Fecha:** 2026-06-04
**Estado:** Auditoria inicial para plan de migraciones
**Regla base:** `personas.id` es UUID y toda identidad ministerial debe apuntar a `personas.id`.

---

## 1. Alcance Auditado

Inventario generado desde `backend.app:app`:

| Metrica | Total |
|---|---:|
| Rutas API FastAPI bajo `/api/` | 710 |
| Tablas cargadas con PK entera, FK a `personas` o FK a `users` | 156 |
| Tablas con FK a `personas` | 76 |
| Tablas con FK a `users` | 28 |
| Tablas con PK entera | 144 |

La cifra de PK enteras incluye catalogos permitidos y tablas legacy. No se migra todo en bloque.

---

## 2. Hallazgo Principal

La plataforma ya esta parcialmente orientada a UUID:

- Kernel moderno: `personas.id` UUID.
- Auth v2/v3: `auth_users.id` UUID ligado a `personas.id`.
- Modulos modernos: `crm_casos`, `crm_tareas`, `proyectos`, `tareas_proyecto`, `documentos_proyecto`, `agenda_eventos`, `academy_enrollments` usan UUID en zonas criticas.

Pero todavia hay contratos legacy activos:

- endpoints con `user_id:int`;
- columnas `*_user_id` paralelas a `*_persona_id`;
- tablas transaccionales con PK entera y FK a `personas`;
- endpoints v1 que aceptan IDs enteros de cursos, eventos, grupos, sesiones, tareas o tickets.

---

## 3. Endpoints Criticos de Identidad a Migrar Primero

Estos endpoints exponen identidad de persona como entero o dependen directamente de `users.id`. Son prioridad alta porque chocan con la regla UUID.

| Prioridad | Endpoint | Modulo | Parametros actuales | Accion |
|---|---|---|---|---|
| P0 | `/api/crm/volunteers/{persona_id}` | `backend.api.crm.pastoral` | `persona_id:str` UUID, con fallback temporal a `Persona.user_id` legacy | Migrado contrato de ruta a UUID sin romper consumidores legacy |
| P0 | `/api/spiritual-life/milestones/{person_id}` | `backend.api.spiritual_life` | `person_id:str` UUID | Migrado contrato y CRUD interno a `SpiritualMilestone.persona_id` |
| P0 | `/api/auth/users/{user_id}` | `backend.api.auth` | `user_id:int` | Mantener solo como auth legacy; agregar/usar endpoint por `persona_id` |
| P0 | `/api/admin/users/{user_id}/permissions` | `backend.api.admin` | `user_id:int` | Resolver permisos por persona/auth UUID |
| P0 | `/api/academy/users/{user_id}/enrollments` | `backend.api.academy` | `user_id` legacy | Migrar consumidores a persona/auth UUID |
| P0 | `/api/academy/users/{user_id}/progress` | `backend.api.academy` | `user_id` legacy | Migrar consumidores a persona/auth UUID |

Regla: estos cambios no deben eliminar de inmediato los endpoints legacy. Primero agregar ruta UUID o adaptar internamente con resolucion dual, luego migrar frontend, luego deprecar.

---

## 4. Modulos con Mayor Superficie de IDs Enteros

| Modulo | Rutas | Rutas con parametros `int` | Lectura |
|---|---:|---:|---|
| `backend.api.evangelism_grupos` | 50 | 22 | Grupos/sesiones/asistencias legacy |
| `backend.api.academy` | 44 | 20 | Cursos/lecciones/evaluaciones v1 legacy |
| `backend.api.crm.pastoral` | 53 | 17 | CRM pastoral mixto |
| `backend.api.cms_v2` | 47 | 13 | CMS: muchos enteros son catalogos/orden/secciones |
| `backend.api.agents` | 26 | 12 | Agentes internos, no identidad pastoral directa |
| `backend.api.evangelism_events` | 21 | 12 | Eventos CRM legacy |
| `backend.api.academy_core` | 19 | 11 | v2 academico todavia usa IDs enteros en catalogos/contenido |
| `backend.api.cms` | 26 | 11 | CMS legacy |
| `backend.api.agenda_core` | 21 | 9 | Recursos/reservas/participantes |
| `backend.api.crm_core` | 22 | 8 | Pipelines/etapas catalogables, casos ya UUID |

---

## 5. Clasificacion de Migraciones

### A. Migracion de Identidad

Objetivo: ninguna identidad de persona se representa con entero.

Incluye:

- `persona_id:int`;
- `person_id:int`;
- `user_id:int` usado para representar persona;
- columnas `pastor_user_id`, `assignee_user_id`, `leader_user_id`, `closed_by_user_id`, `created_by`, `updated_by` cuando representan actor/persona.

Estrategia:

1. agregar columna UUID paralela si no existe;
2. backfill desde `personas.user_id` o relacion historica equivalente;
3. adaptar endpoints a UUID;
4. mantener alias legacy temporal;
5. migrar frontend;
6. retirar entero solo despues de smoke tests.

### B. Migracion de Tablas Transaccionales con FK a `personas`

Objetivo: si una tabla tiene FK a `personas.id`, su PK debe migrar a UUID salvo excepcion documentada.

Ejemplos prioritarios:

- `agenda_events`, `agenda_participantes`;
- `asistencias`, `grupo_participantes`, `grupos_evangelismo`;
- `donations`;
- `project_comments`, `project_attachments`, `project_activity_logs`;
- `academy_lesson_progress`, `academy_course_attendance`, `academy_forum_threads`, `academy_forum_comments`;
- `spiritual_milestones`, `support_tickets`, `volunteer_shifts`.

### C. Catalogos Permitidos

No se migran automaticamente a UUID:

- `roles`, `badges`, `levels`;
- `funds`, `donation_categories`;
- `cms_sites`, `cms_menus`, `cms_themes` si se mantienen como catalogos internos;
- `crm_pipelines`, `crm_etapas_pipeline`;
- `categorias_estrategia`, `motivos_excusa`, `campaign_seasons`;
- `agenda_recursos` si se define como catalogo de recursos fisicos.

Cada excepcion debe quedar escrita en el modelo o en esta hoja de ruta.

---

## 6. Orden Seguro de Trabajo

### Lote 1: Contratos de Persona

1. `backend.api.crm.pastoral`: migrar volunteers `persona_id:int` a UUID. **Completado:** contrato `str` UUID con fallback legacy por `Persona.user_id`.
2. `backend.api.spiritual_life`: reemplazar `person_id:int` por `persona_id:str`. **Completado:** ruta acepta UUID y CRUD usa `persona_id`.
3. Tests de contrato para rechazar enteros en rutas nuevas de persona. **Completado:** `test_no_new_person_identity_int_params`.
4. `backend.api.admin` y `backend.api.auth`: separar endpoints de auth legacy (`user_id`) de endpoints ministeriales (`persona_id`).

### Lote 2: Academy Legacy

1. Mantener cursos/lecciones como catalogos si se decide que pueden ser enteros.
2. Migrar enrollments/progress/certificados a `persona_id` UUID.
3. Deprecar rutas `/academy/users/{user_id}/...`.

### Lote 3: Evangelism y Grupos

1. Migrar `grupos_evangelismo.id` a UUID o documentarlo como catalogo operativo con excepcion.
2. Migrar sesiones/asistencias/follow-up con backfill.
3. Mantener redirects `/faro`, `/grupos`, `/micro` durante transicion.

### Lote 4: Donaciones y Auditoria

1. `donations.id` a UUID si se considera transaccional externa/API.
2. Actor de auditoria por `actor_persona_id`; `actor_user_id` solo legacy.
3. Certificados y comprobantes deben aceptar UUID.

### Lote 5: Proyectos Complementarios

1. `projects` y `project_tasks` ya son UUID.
2. Migrar comentarios, adjuntos, mensajes, supplies e inbox state segun criticidad.

---

## 7. Pruebas Obligatorias por Lote

Minimo:

```bash
python3 scripts/auditing/quality_gate.py
python3 -m pytest -q -o addopts='' tests/test_structural_contracts.py tests/test_reglas_plataforma.py
npm run typecheck
```

Si toca runtime:

```bash
./startccf
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:8000/api/system/health
curl -f http://127.0.0.1:3000/
./stopccf
```

---

## 8. Regla Anti-Perdida de Datos

Nunca eliminar una columna entera legacy antes de:

1. crear columna UUID temporal;
2. completar backfill;
3. validar cero huerfanos;
4. actualizar FKs;
5. migrar frontend/API consumers;
6. tener rollback documentado.

Esta regla aplica especialmente a cualquier relacion historica que use `users.id`, `course_id`, `grupo_id`, `session_id`, `event_id`, `task_id` o `donation_id`.
