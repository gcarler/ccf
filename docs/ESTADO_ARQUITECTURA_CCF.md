# Estado Arquitectonico CCF

**Fecha:** 2026-07-01
**Contrato vigente:** plataforma v3.0.1 con Kernel de Personas + Axioma 3 multi-tenant completo.

## Contratos Activos

- `personas.id` es el unico identificador de una persona.
- `auth_users.id` comparte el UUID de `personas.id`.
- Auth expone exclusivamente `/api/v3/auth`.
- Academy expone exclusivamente `/api/academy` y persiste en tablas `academy_*`.
- Los roles de plataforma viven en `auth_roles` y `auth_user_module_roles`.
- Los datos administrativos y pastorales respetan `sede_id`.
- **Axioma 3 — Multi-Tenant** cerrado al 100 %: todo User-Generated Content
  del backend tiene scope por sede del actor en API-layer + defense-in-depth
  en CRUD-layer. See `docs/CIERRE_ARQUITECTURA_CCF.md` para la evidencia.

## Estado De Datos

Verificado en produccion antes de la migracion final:

- 769 personas y 769 usuarios Auth activos.
- 0 personas sin usuario Auth.
- 0 correos duplicados en personas.
- `gscarlosernesto@gmail.com` tiene rol `ADMINISTRADOR`.
- Las tablas Academy paralelas y las tablas Identity paralelas estan vacias;
  las migraciones abortan si esa precondicion cambia.

## Cobertura Axioma 3 (Multi-Tenant)

Tabla resumen de los modulos cubiertos:

| Modulo | Tabla | Columna `sede_id` | Migration | API-layer | CRUD-layer |
|---|---|---|---|---|---|
| Personas | `personas` | `sede_id` | legacy | SI | SI |
| Evangelismo (estrategias) | `estrategias_evangelismo` | `sede_id` | legacy | SI | SI |
| Evangelismo (grupos) | `grupos_evangelismo` | `sede_id` | legacy | SI | SI |
| Evangelismo (sesiones) | `sesiones_grupo` | indirecto | legacy | SI | SI |
| Evangelismo (asistencia) | `asistencias` | indirecto | legacy | SI | SI |
| CRM (casos) | `crm_casos` | `sede_id` | Phase 1-3 | SI | SI |
| CRM (tareas) | `tareas_crm` | `sede_id` | Phase 4 | SI | SI |
| Academy (cursos) | `academy_courses` | `sede_id` | Phase 4 | SI | SI |
| Academy (matriculas) | `academy_enrollments` | indirecto | Phase 4 | SI | SI |
| Messaging (hilos) | `messaging_threads` | `sede_id` | Phase 4 | SI | SI |
| Messaging (mensajes) | `messaging_messages` | indirecto | Phase 4 | SI | SI |
| Prayer (peticiones) | `prayer_requests` | `sede_id` | Phase 4 | SI | SI |
| Donations | `donations` | `sede_id` | Phase 4 | SI | SI |
| Spiritual Life | `spiritual_life_*` | `sede_id` | Phase 4 | SI | SI |
| Analytics | `dashboards` | scope via actor | n/a (no column) | SI | SI |
| Projects | `proyectos` | `sede_id` | Phase 4 | SI | SI |
| **CMS Media** | `cms_media_items` | `sede_id` | `20260701_0001` | SI | SI |
| **Testimonials** | `testimonials` | `sede_id` | `20260701_0001` | SI | SI |
| **Announcements** | `announcements` | `sede_id` + `created_by_persona_id` | `20260701_0001` | SI | SI |
| Chat | `chat_messages` | scope via actor | n/a | SI | SI |
| Agents | `agent_runs` | scope via actor | n/a | SI | SI |

> Total: **194+** referencias a `get_user_sede_id` / scope helpers en el backend.

## CmsSite (Faro Global)

Entidades del site publico: `CmsSite`, `CmsPage`, `CmsPageVersion`, `CmsSection`,
`CmsTheme`, `CmsMenu`. **NO reciben scope multi-tenant por diseno**: son
globales para mantener coherencia visual cross-sede. Solo los User-Generated
Content (Testimonial / Announcement / CmsMediaItem) son tenant-isolated.

## Academy

- Catalogo, lecciones, matriculas, progreso, evaluaciones, certificados, tareas y foro usan UUID.
- Un usuario `LECTOR` recibe `academy:study` y puede operar solo sobre su propia matricula y progreso.
- Edicion y gestion requieren `academy:edit` o `academy:manage`.
- Las consultas de curso y dashboard aplican el alcance de sede.
- No existe una ruta `/api/v2/academy` ni un segundo modelo Academy.

## Defensa del Upload CMS

Pipeline endurecido — Axioma 3 + Defense-in-Depth (orden de validacion en
`backend/api/cms.py::upload_cms_media`):

1. **Size guardrail** — `MAX_UPLOAD_SIZE` (10 MiB).
2. **Extension allow-list** — `ensure_allowed_extension` (png/jpg/jpeg/gif/webp/pdf/mp4/mp3/wav/zip).
3. **MIME / extension alignment** — `validate_mime_extension_alignment`.
4. **Filename sanitization** — `sanitize_filename` (anti path-traversal).
5. **`sede_id` server-side** — `actor_user_id` propaga y CRUD deriva de actor.

## Gate De Cierre (auditable)

El gate es la fuente unica de verdad. ``docs/CIERRE_ARQUITECTURA_CCF.md`` lo
referencia sin duplicarlo. La version ejecutable vive en
``tests/test_arquitectura_100pct.py``; si las versiones markdown y pytest
divergen, pytest es la fuente canonica.

> **Nota sobre exclusions (chicken-and-egg del auditor):** los comandos
> a continuacion excluyen ``-g '!tests/test_arquitectura*.py'`` y
> ``-g '!tests/test_structural_contracts.py'`` porque el auditor Y el
> assert estructural nombran literalmente las cadenas prohibidas. Para
> version auto-validable ver ``tests/test_arquitectura_100pct.py``.

```bash
# 1. Identidad canonica — personas por UUID, no integers.
rg -n "personas\\.user_id|users\\.id['\"].*persona" \
  backend frontend/src tests scripts \
  -g '!alembic/versions/*.py' \
  -g '!tests/test_arquitectura*.py' \
  -g '!tests/test_structural_contracts.py'
rg -n 'ForeignKey\("users\.id"\)' \
  backend frontend/src tests scripts \
  -g '!alembic/versions/*.py' \
  -g '!tests/test_arquitectura*.py' \
  -g '!tests/test_structural_contracts.py'
# Esperado: vacio.

# 2. CCF-MBR — busqueda de tokens legacy.
# EXCEPCION FIRMADA (REGLAS §9.1.1): los archivos en ``alembic/versions/``
# 0024_prod_hardening3.py + 0025_prod_final.py contienen la cadena como
# memoria del backfill mayo-2026. Ver REGLAS §9.1 para la regla.
rg -n "CCF-MBR" \
  backend frontend/src tests scripts \
  -g '!alembic/versions/*.py' \
  -g '!tests/test_arquitectura*.py'
# Esperado: vacio.

# 3. Academy — sin duplicacion legacy v2.
rg -n "/api/v2/academy" \
  backend frontend/src tests scripts \
  -g '!tests/test_arquitectura*.py' \
  -g '!tests/test_structural_contracts.py'
# Esperado: vacio. (El test structural_contracts es el assert de la ausencia.)

# 4. Sin scripts legacy en scripts/.
find scripts -name '_tmp_*' -o -name '_scratch_*' -o -name '_validate_legacy_*'
find scripts -path '*/__pycache__/*' -prune -o -type f -print | grep -E '(_tmp_|_scratch_|_validate_legacy_)\.py$'
# Esperado: vacio. REGLAS §9.2.

# 5. Conteo de cobertura multi-tenant — cuantificacion del "194+ referencias".
rg -c 'get_user_sede_id|_scope_|_get_scoped_' \
  backend -g '!**/__init__.py' \
  | awk -F: '{s+=$2} END {print "Cobertura multi-tenant refs: " s}'
# Esperado: >= 194 (baseline del cierre v3.0.1).

# 6. Version ejecutable (canonica) del gate via pytest.
source venv/bin/activate
python -m pytest -q -o addopts='' tests/test_arquitectura_100pct.py -v
# Esperado: 9 passed.

# 7. Validacion funcional del cierre v3.0.1.
python -m pytest -q -o addopts='' \
  tests/test_structural_contracts.py \
  tests/test_smoke.py \
  tests/test_academy_api.py \
  tests/test_cms_sede_isolation.py \
  tests/test_cms_metrics_sede_isolation.py \
  tests/test_cms_upload_and_image_hardening.py \
  tests/test_messaging_sede_isolation.py \
  tests/test_messaging_fase4_owner_and_crud_layer.py

# 8. Frontend.
cd frontend
npm run typecheck
npm run build
```

El cierre requiere ademas `alembic upgrade head`, health checks local/publicos
y un flujo autenticado Academy con un administrador y un usuario `LECTOR`.

### Evidencia Ejecutable — Verificacion de los 4 WARNINGs (commit `ffc76fee`)

Code-review post-merge del commit `ffc76fee`
(`feat(security): complete Axioma 3 multi-tenant hardening (close v3.0.1)`)
identifico 4 WARNINGs pre-tag. La verificacion se ejecuto directamente sobre
el bytecode compilado (`python3 -m py_compile` + ripgrep dirigido) y los
resultados se reproducen aqui como evidencia ejecutable para auditoria
independiente. **Todos los WARNINGs cerraron en PASS**, ninguno requiere
cambio de codigo antes del tag.

| # | WARNING | Verdict | Evidencia ejecutable (path:line) |
|---|---|---|---|
| 1 | `actor_user_id` con default `= None` en CRUD | **PASS (by design)** | `backend/crud/cms.py:427, 515, 560, 1306, 1378, 1407, 1434, 1512, 1561, 1661` ; `backend/crud/crm.py:694, 759, 1370`. Es el code path **orphan-FK LENIENT** disenado en `docs/CIERRE_ARQUITECTURA_CCF.md §"Orphan-fallback LENIENT"` (lineas 7-8) y `docs/REGLAS.md §4.1`. El enforcement non-None ocurre en la API-layer via `current_user.id`; el `= None` en CRUD es la senal explicita `actor=worker/script` para que el helper herede `actor_sede`. |
| 2 | Migracion Alembic SQLite-portable | **PASS** | `alembic/versions/20260701_0001_cms_content_sede_id.py` usa `op.batch_alter_table` (lineas 88, 119, 188, 207), helper `_uuid_type()` con branch `dialect.name == "postgresql"` (lineas 77-80), backfill SQL con branching explicito `bind.dialect.name` Postgres vs SQLite (lineas 136-164), guards idempotentes `_has_table / _has_column / _has_index / _has_fk` (lineas 34-65). **NO** usa `server_default=sa.func.now()` ni tipos Enum hostiles. |
| 3 | Public endpoints `/api/cms/testimonials` y `/api/cms/announcements` globales (no scoped) | **PASS** | `backend/api/cms.py:50` (`list_cms_testimonials`) y `:177` (`list_cms_announcements`) son `def list_*_cms(db: Session = Depends(get_db))` — sin `current_user`, sin imports de `_get_scoped_*` / `_scope_` / `get_user_sede_id`. `cms_v2.py` importa los helpers solo para paths admin (lineas 1148 pastoral_team, 1201 pastoral_profile_update IDOR, 1470 cms_media update). Comentario inline `cms.py:44-46` documenta la intencion: *"endpoints publicos (/cms/testimonials) siguen retornando solo testimonios aprobados para preservar el feed publico de la home"*. |
| 4 | Politica orphan: STRICT branch antes de LENIENT fallback | **PASS (distribuida entre capas)** | **LENIENT** orphan-FK en `backend/api/_cms_helpers/_shared.py:41-55` (`_actor_sede_or_none` retorna `None` cuando `current_user is None` o actor sin sede — bypass superadmin/anterior). **STRICT** orphan-persona en CRUD: `crud/cms.py:1458` (`if author_persona_id is None and actor_user_id is not None: author_persona_id = resolve_persona_id_for_user(...)`) precede el reject; `crud/crm.py:1321-1325` docstring lo formula literalmente *"Actor con sede y persona_id None: REJECT (orphan log)"*. La rama STRICT se ejecuta antes que el LENIENT inherit `actor_sede`. |

Comandos de re-validacion ejecutables (auto-contables, idempotentes):

```bash
cd /root/ccf

# WARNING 1 — localizar firmas reales con default None en CRUD (filtra log strings y docstrings).
# Lineas esperadas: 13 firmas reales (10 en backend/crud/cms.py + 3 en backend/crud/crm.py).
# NOTA AUDITOR: el regex pesca 2 falsos positivos adicionales dentro de literales —
# crud/cms.py:146 (log string `"...actor_user_id=%s (creator FK is None)"`) y
# crud/crm.py:774 (param docstring con `...None...`). La forma naive (`| wc -l`)
# devuelve 15; el filtro `rg -v "['"\\"]"` que sigue excluye lineas con cualquier
# caracter de comilla (' " `) y deja SOLO las 13 firmas reales. Si wc -l != 13,
# auditar los falsos positivos del filtro (lineas con comillas abiertas que no se cierran
# en la misma linea o strings raw con backticks).
rg -nP 'actor_user_id\s*[:=]\s*[^,)\n]*\bNone\b' backend/crud/ \
  | rg -v "['\"\`]" \
  | wc -l
# Esperado: 13 firmas reales.

# WARNING 2 — confirmar batch_alter_table + dialect branch + NO server_default
grep -nE 'batch_alter_table|dialect\.name' \
  alembic/versions/20260701_0001_cms_content_sede_id.py
rg -nP 'server_default\s*=\s*sa\.func\.now' alembic/versions/20260701* \
  || echo 'OK: sin sa.func.now()'
# Esperado: 4 ocurrencias de batch_alter_table, 3 de dialect.name (lineas 76, 141, 217 — la tercera en downgrade como noop), 0 de sa.func.now().

# WARNING 3 — confirmar que los handlers PUBLIC no llaman scope helpers
grep -nE 'get_user_sede_id|_get_scoped_|_scope_' \
  backend/api/cms.py \
  | rg 'list_cms_testimonials|list_cms_announcements|get_cms_testimonial|get_cms_announcement' \
  && echo 'FAIL: public handler con scope helper' \
  || echo 'OK: public handlers sin scope helpers'

# WARNING 4 — confirmar rama STRICT (crud) precede rama LENIENT (helper)
echo '--- LENIENT helper (origen del bypass) ---'
sed -n '41,55p' backend/api/_cms_helpers/_shared.py
echo '--- STRICT branch en crud/cms.py ---'
rg -nP 'author_persona_id is None and actor_user_id is not None|resolve_persona_id_for_user' backend/crud/cms.py | head -4
echo '--- STRICT branch en crud/crm.py (REJECT persona sin sede) ---'
sed -n '1320,1326p' backend/crud/crm.py
```

Checklist del cierre (auditable):

- [x] Commit `ffc76fee` en `main` (`git log --oneline -1`).
- [x] `git show --stat ffc76fee` reporta 27 archivos, `+5223 / -194`.
- [x] `python3 -m py_compile` sobre los 22 `.py` del HEAD: **21 OK + 1 expected-fail** (`scripts/_tmp_list_routes.py` borrado en el mismo commit).
- [x] Code-review post-merge: 0 CRITICAL, 4 WARNINGs — los 4 cierran en PASS con evidencia de linea arriba.
- [x] Tag auditable `v3.0.1` puede emitirse contra este commit.

## Documentos Relacionados

- `REGLAS.md` — Kernel de Personas, Auth v3, Axioma 3.
- `docs/PROTOCOLO_CAMBIOS_SEGUROS_CCF.md` — protocolo de cambios.
- `docs/ESTANDARES_DESARROLLO.md` — estandares tecnicos.
- `docs/AGENTES_OPERATIVOS_CCF.md` — guia operativa para agentes.
- `docs/CIERRE_ARQUITECTURA_CCF.md` — acta formal del 100 % v3.0.1.

## Riegos Residuales

- Personas con `sede_id=NULL` (orphan-persona) son rechazadas por el CRUD
  defense-in-depth cuando se usan como FK. Operadores deben reasignar
  manualmente la sede antes de que la fila quede habilitada para el staff.
- Announcements legacy sin `sede_id` son visibles solo para superadmin sin
  sede (consistente con TareaCRM orphan-guard). Documentado en la migration.
