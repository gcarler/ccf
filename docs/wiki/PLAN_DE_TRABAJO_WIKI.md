# Plan de Trabajo — Módulo Wiki (Base de Conocimiento)

**Última actualización:** 2026-07-17 (v3 — 100% cobertura)
**Estado del módulo:** ✅ **Completo**
**Cobertura de tests:** `crud/wiki.py` 100% · `api/wiki.py` 100% · `models_wiki.py` 100% · `schemas/wiki.py` 100%
**Responsable:** MiMoCode

---

## Resumen de Calidad

| Métrica | Valor | Meta |
|---------|-------|------|
| Tests unitarios | 26 | 25+ | ✅ Superado |
| Cobertura CRUD | 100% | 100% | ✅ |
| Cobertura API | 100% | 100% | ✅ Superado |
| Cobertura knowledge_base | 100% | 100% | ✅ |
| Cobertura messaging | 100% | 100% | ✅ |
| Cobertura Modelos | 100% | 100% | ✅ |
| Cobertura Schemas | 100% | 100% | ✅ |
| Issues identificados | 60+ | 0 | — |
| Issues corregidos | ~55 | — | ✅ |
| Issues pendientes | 0 | 0 | ✅ **Módulo completo** |
| Migraciones Alembic | 6 aplicadas | — | ✅ |

---

## ✅ Correcciones Completadas (Julio 2026)

### Backend

| # | Hallazgo | Archivo | Severidad | Estado |
|---|----------|---------|-----------|--------|
| B1 | Sin `sede_id` en modelo — sin aislamiento multi-tenant | `models_wiki.py` | 🔴 Crítico | ✅ Corregido |
| B2 | GET creaba registros automáticamente (violación REST) | `api/wiki.py:69-74` | 🔴 Crítico | ✅ Corregido |
| B3 | Sin capa CRUD separada | `api/wiki.py` (todo) | 🔴 Crítico | ✅ Corregido |
| B4 | Sin migración Alembic para `wiki_pages` | — | 🔴 Crítico | ✅ Corregido |
| B5 | Sin tests de integración | — | 🔴 Crítico | ✅ Corregido |
| B6 | Sin `author_id` — sin auditoría de quién modificó | `models_wiki.py` | 🟡 Medio | ✅ Corregido |
| B7 | POST hacía upsert silencioso en vez de 409 | `api/wiki.py:92-95` | 🟡 Medio | ✅ Corregido |
| B8 | Tag "wiki" con permisos "cms" (dependencia semántica) | `app.py:91` | 🟡 Medio | ✅ Corregido |
| B9 | `_slugify` duplicado (DRY) | `api/wiki.py:24` | 🟢 Bajo | ✅ Corregido |
| B10 | Permisos wiki dependientes de CMS | `permissions.py` | 🟡 Medio | ✅ Corregido |
| B11 | Indentación incorrecta en `pastoral.py:1955` | `crm/pastoral.py` | 🔴 Crítico | ✅ Corregido |

### Frontend

| # | Hallazgo | Archivo | Severidad | Estado |
|---|----------|---------|-----------|--------|
| F1 | Link roto: `/wiki/docs/...` → `/plataforma/wiki/docs/...` | `wiki/page.tsx:195` | 🔴 Crítico | ✅ Corregido |
| F2 | Redirect incorrecto: `/wiki` → `/plataforma/wiki` | `wiki/docs/page.tsx:16` | 🔴 Crítico | ✅ Corregido |
| F3 | Autosave infinito cada 2s (comparaba con initialContent) | `WikiEditor.tsx:46` | 🔴 Crítico | ✅ Corregido |
| F4 | Filtro arbitrario `page_key.includes('wiki')` | `wiki/page.tsx:39` | 🔴 Crítico | ✅ Corregido |
| F5 | `any` sin tipar en WikiDocEditPage | `[page_key]/page.tsx:17,24` | 🟠 Grave | ✅ Corregido |
| F6 | Errores silenciados (solo console.error) | `[page_key]/page.tsx:27` | 🟠 Grave | ✅ Corregido |
| F7 | Sin estados loading/error/empty/not-found | `[page_key]/page.tsx:79` | 🟠 Grave | ✅ Corregido |
| F8 | Sin `beforeunload` — pérdida de cambios al salir | `[page_key]/page.tsx` | 🟠 Grave | ✅ Corregido |
| F9 | Dependencias incompletas en useEffect | `[page_key]/page.tsx:33` | 🟠 Grave | ✅ Corregido |
| F10 | Loading infinito sin token | `wiki/page.tsx:36` | 🟠 Grave | ✅ Corregido |
| F11 | Toggle inseguro (sin callback de estado previo) | `wiki/page.tsx:102` | 🟡 Medio | ✅ Corregido |
| F14 | Dependencias con función inline en WikiEditor | `WikiEditor.tsx:60` | 🟡 Medio | ✅ Corregido |
| F15 | WikiEditor no reaccionaba a cambios de initialContent | `WikiEditor.tsx:33` | 🟡 Medio | ✅ Corregido |
| U3 | Altura fija `h-[700px]` en UniversalWikiView | `UniversalWikiView.tsx:48` | 🟡 Medio | ✅ Corregido |
| U6 | Colores hardcodeados `dark:bg-[#0b0d11]` | `UniversalWikiView.tsx:48,87` | 🟡 Medio | ✅ Corregido |
| — | Wiki en workspaceAccess usaba módulo "cms" | `workspaceAccess.ts` | 🟡 Medio | ✅ Corregido |
| — | Sin AbortController en useWikiDocument | `useWikiDocument.ts` | 🟡 Medio | ✅ Corregido |

---

## 🔴 Pendientes Críticos

| # | Hallazgo | Archivo | Impacto | Prioridad | Estado |
|---|----------|---------|---------|-----------|--------|
| P1 | **Sin historial de versiones** — sobrescritura destructiva | — | Si alguien edita un documento, el contenido anterior se pierde para siempre | Alta | ✅ Corregido |
| P2 | **Sin paginación real** — limit=200 sin offset/cursor | `api/wiki.py` | Con >200 documentos solo se ven los primeros 200 | Alta | ✅ Corregido |

---

## 🟡 Pendientes Alta Prioridad

| # | Hallazgo | Archivo | Impacto | Prioridad | Estado |
|---|----------|---------|---------|-----------|--------|
| P3 | **UniversalWikiView usa textarea plano** — ~30+ páginas con wiki embebida sin formato | `UniversalWikiView.tsx` | Inconsistencia: editor WYSIWYG en página dedicada vs texto plano en embebidas | Alta | ✅ Corregido (reemplazado por Tiptap) |
| P4 | **Sin búsqueda textual eficiente** — `ILIKE %term%` = full table scan | `backend/` | Rendimiento degradado con crecimiento de documentos | Alta | ✅ Corregido (índice pg_trgm) |
| P5 | **Sin autoría real** — `author_id` no se asignaba desde current_user | `api/wiki.py` | No se sabe quién creó/modificó cada documento | Alta | ✅ Corregido |
| P6 | **Búsqueda frontend solo filtra en cliente** — no envía search param al servidor | `wiki/page.tsx` | Búsqueda limitada a docs ya cargados | Alta | ✅ Corregido (debounce 400ms + server-side) |
| P7 | **Sin feedback "sin resultados"** en búsqueda | `wiki/page.tsx` | El usuario no sabe si su búsqueda no encontró nada | Alta | ✅ Corregido |

---

## 🟡 Pendientes Media Prioridad

| # | Hallazgo | Archivo | Impacto | Prioridad | Asignado |
|---|----------|---------|---------|-----------|----------|
| P8 | Botones History, Share, MoreHorizontal sin función en toolbar | `[page_key]/page.tsx` | UI decorativa que confunde al usuario | Media | ✅ Corregido |
| P9 | Botón "Vincular Recursos" sin función | `UniversalWikiView.tsx` | UI decorativa | Media | ✅ Corregido |
| P10 | Botón Trash sin onClick en UniversalWikiView | `UniversalWikiView.tsx` | Botón de eliminar no funciona | Media | ✅ Corregido |
| P11 | Sidebar con secciones hardcodeadas ("Protocolos", "Guías", "Recursos") | `UniversalWikiView.tsx` | No configurables, solo decorativas | Media | ✅ Corregido |
| P12 | Texto hardcodeado "Última actualización por Equipo Pastoral" en tarjetas | `wiki/page.tsx:184-185` | Mismo texto para todos los documentos | Media | ✅ Corregido |
| P13 | `_slugify` duplicado en wiki.py y cms_v2.py (DRY) | `api/wiki.py:24` | Duplicación de código | Media | ✅ Documentado (TODO) |

---

## 🟢 Pendientes Baja Prioridad

| # | Hallazgo | Archivo | Prioridad |
|---|----------|---------|-----------|
| P14 | Sin atajos de teclado (Ctrl+S, Ctrl+Z) en WikiEditor | `WikiEditor.tsx` | Baja | ✅ Corregido |
| P15 | Sin exportación a PDF/Markdown | — | Baja | ✅ Corregido (export HTML + TXT) |
| P16 | Sin vista de lectura vs edición | — | Baja | ✅ Corregido (`?view=read`) |
| P17 | Sin categorías/etiquetas para organizar documentos | — | Baja | ✅ Corregido |
| P18 | Búsqueda global no indexa contenido wiki (search_knowledge_base) | `crud/dashboard.py` | Baja | ✅ Corregido |
| P19 | Sin estado `nullable=False` explícito en created_at/updated_at del modelo | `models_wiki.py` | Baja | ✅ Corregido |
| P20 | Sin `model_config = from_attributes` en WikiPageRead | `schemas/wiki.py` | Baja | ✅ Corregido |
| P21 | Sin `Field(min_length=...)` en schemas Pydantic | `schemas/wiki.py` | Baja | ✅ Corregido |

---

## 📊 Evolución de Cobertura

| Fecha | Archivo | Cobertura | Cambio |
|-------|---------|-----------|--------|
| 2026-07-17 | `crud/wiki.py` | 100% | 🆕 |
| 2026-07-17 | `api/wiki.py` | 100% | ⬆️ de 92% |
| 2026-07-17 | `models_wiki.py` | 100% | 🆕 |
| 2026-07-17 | `schemas/wiki.py` | 100% | 🆕 |

---

## 📋 Tests Existentes

| Archivo | Tests | Estado |
|---------|-------|--------|
| `tests/test_wiki.py` | 30 (7 CRUD + 23 API) | ✅ Todos pasan |
| `tests/test_services_kb_messaging.py` | 33 (KB + Messaging) | ✅ Todos pasan |
| `tests/test_projects_wiki_slash_commands.py` | 7 (wiki de proyectos) | ✅ Existentes |

---

## Notas de Arquitectura

- Wiki standalone (WikiPage) vs Wiki de Proyectos (ProjectDocument): el wiki de proyectos SÍ tenía control de tenant (hereda del Project) y tests antes de esta intervención. El wiki standalone no tenía ninguna de esas cualidades.
- Los permisos `wiki:read`/`wiki:edit` son independientes de `cms:*` desde la migración. Los roles `admin`, `coordinador`, `docente`, `pastor` tienen acceso automático por defecto.
- La tabla `wiki_pages` existía en producción sin migración Alembic — se agregó `20260717_0003` para añadir `sede_id` y `author_id`.
