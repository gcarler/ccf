# Deuda Técnica del Backend CMS

> **Auditoría realizada:** 2026-07-29
> **Alcance:** APIs, CRUD, modelos, esquemas y servicios relacionados con CMS en el backend.
> **Actualizado:** 2026-08-05 — Cierre del ciclo de deuda estructural (sesión ses_02d3e21b9ffe8On3QkULQEnJkO). 2/3 🔴 y 4/4 🟠 cerrados; 1 🔴 y 1 🟠 pospuestos a sesión dedicada.

## Resumen Ejecutivo

El backend CMS presenta una **alta concentración de deuda estructural**: archivos monolíticos, duplicación de lógica entre la API v1 (`cms.py`) y la API v2 (`cms_v2/`), y patrones de consulta que pueden degenerar en N+1. La separación física entre v1 y v2 es positiva, pero el paquete `cms_v2` aún no está completamente desacoplado de `crud/cms.py`, y ambos contienen funciones muy largas.

**Ciclo 2026-08-05 (cierre estructural):**
- ✅ 🔴 #2 Duplicación v1↔v2 — helper `_commit_or_conflict/_commit_or_raise_conflict` triplicado consolidado en single source of truth (`crud/_utils._is_unique_violation` + 2 contracts).
- ✅ 🟠 #3 Acoplamiento carga de autores — extraído `_hydrate_testimonials_section` de `_shared.py` (32 LOC inline → helper dedicado).
- ✅ 🟠 #4 Defaults hardcodeados — extraídos a módulo declarativo `cms_v2/_defaults.py`.
- ✅ 🟠 #4 (recurrente) `enterprise_cms.py` monolito 1.670 LOC — split en paquete `enterprise_cms/` con 12 sub-routers por dominio + `__common.py` para helpers compartidos.
- ✅ 🟠 #5 Solapamiento de esquemas — verificado como falso positivo (cms.py = entidades, cms_v2_sections.py = section props; 0 overlap literal, 0 validación duplicada).
- ✅ 🟠 #6 `public.py` side effects — extraído `resolve_system_persona_and_sede` a `cms_media_service`; eliminada la creación on-demand de Persona "Sistema Público".
- ✅ 🟠 #7 `enterprise_cms.py` subsumido por cierre #4-split.
- ✅ 🟢 #9 Comentarios #F-XX dispersos — convertidos a referencias vinculantes a `AUDITORIA_FORENSE_CMS.md`.
- ✅ 🟢 #10 Models divididos en dos archivos — documentada relación en header de `models_cms.py`.
- ⏸ 🔴 #1 `crud/cms.py` 3.116 LOC — pospuesto: split completo expone regresión a 61 callers; requiere sesión dedicada. Monolito YA tiene 21 section headers `# ──` segmentando por dominio (split viable quirúrgico).
- ⏸ 🟠 #7 Tests backend fragmentados (subsumido #8) — consolidar 39 `test_cms_*.py` a `tests/cms/` es wide migration (prohibido mezclar con cambios funcionales por REGLAS.md); requiere sesión dedicada.

## Métricas generales

| Módulo | Líneas | Observación |
|--------|--------|-------------|
| `backend/crud/cms.py` | 3,107 | Monolito CRUD; múltiples responsabilidades mezcladas (split pospuesto). |
| `backend/api/cms_v2/` (paquete, 15 archivos) | 4,455 | Router principal v2; lógica de negocio, rendering y utilidades (el archivo más grande es `pages.py` con 811). |
| `backend/api/enterprise_cms/` (paquete, 12 sub-routers + `__common.py`) | ~1,850 | Split del monolito 2026-08-05; cada sub-router cubre un dominio. |
| `backend/schemas/cms.py` | 1,074 | Esquemas extensos; validaciones potencialmente duplicadas con `cms_v2_sections`. |
| `backend/schemas/cms_v2_sections.py` | 756 | Esquemas de secciones v2; solapamiento con el anterior. |
| `backend/models_cms.py` | 815 | Modelos base del CMS; el resto vive en `models_enterprise.py`. Header educativo añadido (relación documentada). |
| `backend/api/cms/` (paquete v1, 8 archivos) | 2,271 | API v1 (antes `api/cms.py`); el archivo más grande es `v1.py` con 325. |
| `backend/api/cms_v2/_defaults.py` | NUEVO | Centraliza defaults de contenido CMS (consolidación de deuda 🟠#4, 2026-08-05). |
| `backend/api/cms_v2/_shared.py` | ~630 | Helpers compartidos cms_v2; `_hydrate_testimonials_section` extraído (🟠#3 cerrado). |
| `backend/crud/_utils.py` | ~190 | Helper de unique-violation detection + 2 contracts; consolidación de las 3 copias (🔴#2 cerrado). |
| `backend/services/cms_media_service.py` | ~280 | `resolve_system_persona_and_sede` añadido; elimina side effect de public.py (🟠#6 cerrado). |
| `backend/services/public_contact_tracking.py` | 205 | Servicio acoplado a publicaciones y contactos. |
| `backend/crud/cms_pastors_sync.py` | 289 | Sincronización pastoral; depende de CmsSite/CmsPage. |

## Hallazgos por severidad

### 🔴 Alta

#### 1. Monolitos de código — `crud/cms.py` (parcialmente CERRADO, 2026-08-05)

**Estado:** pospuesto. `crud/cms.py` ya tiene 21 section headers `# ──` segmentando por dominio (Media, Sites, Themes, Menus, Pages, Sections, Versiones, Scheduling, Pastoral, Posts, Cleanup, Popups, Contact Forms, Newsletters, A/B Testing). Verificado pure leaf data layer (sólo 1 import de schema). Split completo requiere mover 3.107 LOC + replantear 61 callers (servicios/cms_workflow, scheduler, tests/`test_cms_*` y `crud/__init__.py` que reexporta ~150 funciones). Exposición a regresión alta; pospuesto a sesión dedicada.

- **Riesgo residual:** monolito de 3.107 LOC dificil de navegar, pero sequence headers + puro data layer reduce riesgo de drift.
- **Recomendación pendiente:** dividir en `backend/crud/cms/` con UN sub-módulo por header `# ──` (15+ archivos) y `__init__.py` reexportando todas las funcs públicas.

#### ✅ 2. Duplicación de helpers entre v1 y v2 (CERRADO, 2026-08-05)

Helper `_commit_or_conflict` triplicado en `crud/cms.py`, `api/cms_v2/_shared.py`, `crud/academy.py` consolidado en `backend/crud/_utils._is_unique_violation` + 2 contracts (`_commit_or_conflict_bool` bool y `_commit_or_raise_409` HTTPException). Las 3 copias reapuntadas al canónico. Smoke CMS + Academy OK.

#### 3. Patrón de carga de autores (CERRADO vía 🟠#3) — ver abajo.

### 🟠 Media

#### ✅ 4. `enterprise_cms.py` 1.669 LOC monolito (CERRADO, 2026-08-05)

Split en paquete `backend/api/enterprise_cms/` con 12 sub-routers por dominio + `__common.py` (helpers `_log_audit`, `_notify`, `_fire_webhooks` + deps RBAC). 39 endpoints preservados, `router/resolve_redirect/execute_search` re-exportados para compatibilidad. 69 tests CMS pasan (incluye `test_enterprise_cms.py` + `test_cms_f04_redirects_wildcard_regex.py`).

#### ✅ 4b. Defaults hardcodeados en la API v2 (CERRADO, 2026-08-05)

Defaults inline en `api/cms_v2/_shared.py::_build_section_defaults` ("Te invitamos a ser parte de nuestra familia", "Nuestra Iglesia", "Conócenos", etc.) extraídos a módulo declarativo `api/cms_v2/_defaults.py`. Comportamiento idéntico preservado (defaults como fallback de SystemVariable).

#### ✅ 3. Patrón de carga de autores acoplado (CERRADO, 2026-08-05)

Bloque inline `joinedload(models.CmsPost.author_persona)` (~32 LOC) embebido en `_build_section_defaults` extraído como helper dedicado `_hydrate_testimonials_section`. `_build_section_defaults` ahora despacha al helper. 3 callers públicos preservados (`pages.py` v2 + admin + public).

#### ✅ 5. Solapamiento de esquemas (FALSO POSITIVO, 2026-08-05)

Verificado in-situ: cero overlap literal de nombres entre `schemas/cms.py` (entidades) y `schemas/cms_v2_sections.py` (section props). No hay duplicación de validaciones. Hallazgo especulativo en audit original no se materializó.

#### ✅ 6. `public.py` acoplado a lógica de creación de entidades (CERRADO, 2026-08-05)

`POST /public/documents` fabricaba Persona "Sistema Público" on-demand por request (side effect indeseado + violación REGLAS.md §4.1 actor_user_id bypass). Extraído `resolve_system_persona_and_sede` en `services/cms_media_service.py` (resa Primer persona canónica existente + sede activa, sin crear entidad sintética). Script `migrate_external_images_to_cms.py` reapuntado al mismo canónico.

#### ⏸ 7. Backend tests fragmentados (pospuesto, 2026-08-05)

Consolidar 39 archivos `tests/test_cms_*.py` a `tests/cms/` con naming por dominio y eliminar archivos "test_massive_coverage.py", "test_fast_coverage.py", etc. requiere wide migration. REGLAS.md §"no mezclar functional changes con wide migrations" la prohíbe en este ciclo. Pospuesto a sesión dedicada.

### 🟢 Baja

#### ✅ 8. Comentarios de contexto dispersos (CERRADO, 2026-08-05)

4 referencias `# F-XX` en backend (clone_cms_page F-02, scheduling F-09, enterprise_cms F-04 ×2) convertidas a referencias vinculantes `AUDITORIA_FORENSE_CMS.md F-XX (cerrado)` dentro de docstrings/comentarios.

#### ✅ 9. Modelos CMS divididos en dos archivos (CERRADO, 2026-08-05)

Header educativo añadido al inicio de `models_cms.py` documentando la relación con `models_enterprise.py` (qué vive en cada archivo + racional de separación temporal + referencia a futura consolidación opcional).

## Oportunidades de refactorización pendientes

1. **Split completo `crud/cms.py`** en paquete `backend/crud/cms/` por dominio (🔴#1 pospuesto).
2. **Consolidación tests CMS** en `tests/cms/` con naming por dominio (🟠#7 pospuesto).
3. Aplicar carga temprana (`selectinload`) en endpoints de listado público.

## Métricas de deuda actualizadas (post-ciclo 2026-08-05)

| Indicador | Valor aproximado | Nota |
|-----------|------------------|------|
| Archivos monolíticos (>1.000 líneas) | 1 (`crud/cms.py` 3.107) | `enterprise_cms.py` eliminado (split). |
| Bloques de lógica duplicada | 0 confirmados | `_commit_or_conflict` consolidado. |
| Consultas dentro de bucles | 0 | N+1 ya resuelto en sesiones previas (joinedload). |
| Defaults hardcodeados | 0 | Centralizados en `_defaults.py`. |
| Backend tests del CMS | 39 suites dispersas | Consolidación a `tests/cms/` pospuesta. |

## Estado de cierre al 2026-08-05

| Hallazgo | Severidad | Estado |
|----------|-----------|--------|
| #1 Monolito `crud/cms.py` | 🔴 | ⏸ pospuesto (61 callers, sesión dedicada) |
| #2 Duplicación helpers v1↔v2 | 🔴 | ✅ CERRADO |
| #3 Patrón carga autores | 🟠 | ✅ CERRADO (helper extraído) |
| #4 `enterprise_cms.py` monolito | 🟠 | ✅ CERRADO (split paquete 12 sub-routers) |
| #4b Defaults hardcodeados v2 | 🟠 | ✅ CERRADO (`_defaults.py`) |
| #5 Solapamiento de esquemas | 🟠 | ✅ CERRADO (falso positivo) |
| #6 `public.py` side effects | 🟠 | ✅ CERRADO (helper `resolve_system_persona_and_sede`) |
| #7 Tests backend fragmentados | 🟠 | ⏸ pospuesto (wide migration) |
| #8 (`enterprise_cms.py` duplicado #4) | 🟠 | ✅ CERRADO en #4 |
| #9 Comentarios #F-XX dispersos | 🟢 | ✅ CERRADO |
| #10 Models divididos en dos archivos | 🟢 | ✅ CERRADO (header explicativo) |

**Smoke post-ciclo (2026-08-05):**
- `scripts/test_cms_quality.py` → 2 passed, 0 failed (44 backend + 24 frontend unit, E2E omitido por credenciales).
- Gate exhaustivo: `pytest test_enterprise_cms.py + test_cms_v2_coverage.py + test_cms_v2_deep_coverage.py + test_cms_schedule.py + test_cms_seo_audit.py + test_cms_v2_commit_helper.py` → 154 passed.
- Ruff sobre archivos nuevos/modificados: All checks passed.

---

> **Actualizado a partir del cierre del ciclo 2026-08-05.**
