# Estado Arquitectonico CCF

**Fecha:** 2026-06-30
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
| Personas | `personas` | `sede_id` | pre-v3 | SI | SI |
| Evangelismo (estrategias) | `estrategias_evangelismo` | `sede_id` | pre-v3 | SI | SI |
| Evangelismo (grupos) | `grupos_evangelismo` | `sede_id` | pre-v3 | SI | SI |
| Evangelismo (sesiones) | `sesiones_grupo` | indirecto | pre-v3 | SI | SI |
| Evangelismo (asistencia) | `asistencias` | indirecto | pre-v3 | SI | SI |
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

### Erradicación de compatibilidad runtime

La migración `20260701_0002_eradicate_runtime_legacy.py` formaliza el
contrato estricto:

- actor/owner obligatorio en mutaciones protegidas;
- `sede_id` y persona owner `NOT NULL` en UGC CMS;
- assignee CRM exclusivamente UUID de `personas.id`;
- normalización de outcomes y tokens antiguos;
- `project_tasks.labels` como array JSON `NOT NULL` y prioridad canónica;
- `personas.baptism_date` como único nombre físico y público;
- contactos públicos escritos en `CasoCRM`/pipeline canónico;
- seguimiento de evangelismo con un solo vocabulario de campos;
- eliminación de funciones/tablas paralelas de membresía heredada;
- eliminación de aliases y stubs creados sólo para tests.

El Gate 10 de `tests/test_arquitectura_100pct.py` introspecciona firmas,
columnas y archivos para impedir que reaparezcan esos bypasses.

## Estado de Cobertura de Tests (2026-07-19)

| Métrica | Valor |
|---|---|
| Tests totales | ~4,630 |
| Archivos de test | 166 |
| Cobertura global backend | ~39% (target 40% en pytest.ini) |
| Módulos con suite de tests dedicados | Admin (53), Wiki (30), Chat (32), Finance (6), Vida Espiritual (10), Support (7), Donations (7), Agents (2), Enterprise CMS (52), Graph (5), Services (50+) |
| Módulos al 100% de cobertura | ~35+ archivos en backend/ (api/wiki, api/prayer, api/governance, api/workspace, core/config, core/logging, core/audit, core/context, core/security_headers, crud/audit, crud/crm, 14 modelos, 12+ schemas) |
| Smoke scripts canónicos | 13 scripts en scripts/ (admin, chat, wiki, spiritual_life, auth_v3, kernel, workspace, finance, fase3, crm, academy, cms, evangelism, messaging, agenda, projects, platform) |

## Auditoría Forense — Estado

Completadas las 3 fases del plan de auditoría forense definido en `docs/PLAN_ARQUITECTURA_MODULAR_CCF.md`:

| Fase | Módulos | Estado |
|---|---|---|
| Certificados (pre-auditados) | CRM, Academy, CMS, Messaging, Agenda, Evangelismo, Proyectos, Plataforma | 8 módulos |
| Fase 1 | Admin, Chat, Vida Espiritual | 3 módulos — ✅ remediados |
| Fase 2 | Auth v3, Kernel, Workspace, Wiki, Finance | 5 módulos — ✅ remediados |
| Fase 3 | Support, Community, Dashboard, Donations, System, Agents, Prayer, Graph, Analytics, Enterprise CMS, Governance, Tables, Youtube | 14 módulos — ✅ auditados |
| **Total** | **30/33 módulos** cubiertos con ESTADO + auditoría | |

## Documentos Relacionados

- `REGLAS.md` — Kernel de Personas, Auth v3, Axioma 3.
- `docs/ESTANDARES_DESARROLLO.md` — estandares tecnicos.
- `docs/AGENTES_OPERATIVOS_CCF.md` — guia operativa para agentes.
- `docs/CIERRE_ARQUITECTURA_CCF.md` — acta formal del 100 % v3.0.1.
- `docs/MATRIZ_COBERTURA_MODULAR_CCF.md` — matriz actualizada con todas las fases.

## Riesgos residuales

- CmsSite y los feeds publicados siguen siendo globales por decisión editorial.
- Las migraciones cerradas conservan texto SQL histórico, pero no existe
  compatibilidad activa en runtime.
