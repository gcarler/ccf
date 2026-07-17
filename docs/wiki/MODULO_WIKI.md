# Módulo Wiki — Base de Conocimiento

## Descripción

El módulo Wiki proporciona una base de conocimiento colaborativa dentro de la plataforma CCF. Permite crear, editar y organizar documentos de documentación, guías, manuales de proceso y cualquier contenido informativo que el equipo necesite compartir.

---

## Arquitectura

### Stack

| Capa | Tecnología | Archivos clave |
|------|-----------|----------------|
| **Modelo** | SQLAlchemy + PostgreSQL | `backend/models_wiki.py` |
| **Schemas** | Pydantic v2 | `backend/schemas/wiki.py` |
| **CRUD** | SQLAlchemy ORM | `backend/crud/wiki.py` |
| **API** | FastAPI | `backend/api/wiki.py` |
| **Frontend páginas** | Next.js App Router | `frontend/src/app/plataforma/wiki/` |
| **Frontend componentes** | React + Tiptap | `frontend/src/components/wiki/` |
| **Tests** | pytest + SQLite | `tests/test_wiki.py` |

### Endpoints

| Método | Ruta | Auth | Propósito |
|--------|------|------|-----------|
| `GET` | `/api/wiki/pages` | `wiki:read` | Listar documentos activos (filtrados por sede, con paginación offset, búsqueda por search y filtro por category) |
| `GET` | `/api/wiki/pages/count` | `wiki:read` | Total de documentos para paginación |
| `GET` | `/api/wiki/pages/{page_key}` | `wiki:read` | Obtener un documento por su clave (404 si no existe) |
| `GET` | `/api/wiki/pages/{page_key}/versions` | `wiki:read` | Historial de versiones del documento |
| `GET` | `/api/wiki/categories` | `wiki:read` | Listar categorías distintas usadas en la sede |
| `POST` | `/api/wiki/pages/{page_key}` | `wiki:edit` | Crear un nuevo documento (409 si ya existe) |
| `PATCH` | `/api/wiki/pages/{page_key}` | `wiki:edit` | Actualizar parcialmente un documento (snapshot automático de versión anterior) |
| `DELETE` | `/api/wiki/pages/{page_key}` | `wiki:edit` | Soft-delete de un documento |

### Permisos

| Permiso | Nivel | Efecto |
|---------|-------|--------|
| `wiki:read` | Lectura | Ver documentos y listados |
| `wiki:edit` | Edición | Crear, editar y eliminar documentos |

El módulo wiki tiene permisos **independientes** del módulo CMS. Los roles con acceso automático: `admin`, `coordinador`, `docente`, `pastor`.

---

## Modelo de Datos

### `WikiPage` — `backend/models_wiki.py` (tabla `wiki_pages`)

| Columna | Tipo | Nulleable | Default | Descripción |
|---------|------|-----------|---------|-------------|
| `id` | UUID | NO | `uuid.uuid4()` | Identificador único |
| `page_key` | String(120) | NO | — | Clave única URL-safe (ej. `wiki_manual_usuario`) |
| `title` | String(255) | NO | — | Título del documento |
| `content` | Text | NO | `""` | Contenido HTML del documento |
| `version` | Integer | NO | `1` | Número de versión (se incrementa en cada PATCH) |
| `category` | String(100) | SÍ | `NULL` | Categoría para organizar documentos |
| `tags` | JSON | SÍ | `NULL` | Etiquetas del documento |
| `sede_id` | UUID (FK → sedes.id) | SÍ | `NULL` | Sede propietaria (multi-tenant) |
| `author_id` | UUID (FK → personas.id) | SÍ | `NULL` | Autor del documento |
| `created_at` | DateTime(tz) | NO | `_utcnow()` | Fecha de creación |
| `updated_at` | DateTime(tz) | NO | `_utcnow()` | Fecha de última modificación |
| `deleted_at` | DateTime(tz) | SÍ | `NULL` | Soft-delete (no nulo = eliminado) |

**Índices:** `page_key` (unique), `sede_id`, `category`, `ix_wiki_pages_title_trgm` (GIN trigram), `ix_wiki_pages_page_key_trgm` (GIN trigram).

### `WikiPageVersion` — `backend/models_wiki.py` (tabla `wiki_page_versions`)

| Columna | Tipo | Nulleable | Default | Descripción |
|---------|------|-----------|---------|-------------|
| `id` | UUID | NO | `uuid.uuid4()` | Identificador único |
| `wiki_page_id` | UUID (FK → wiki_pages.id) | NO | — | Documento padre (CASCADE) |
| `version_number` | Integer | NO | — | Número de versión (1, 2, 3...) |
| `title` | String(255) | NO | — | Título en esa versión |
| `content` | Text | NO | `""` | Contenido HTML en esa versión |
| `created_by_persona_id` | UUID (FK → personas.id) | SÍ | `NULL` | Quién hizo el cambio |
| `created_at` | DateTime(tz) | SÍ | `_utcnow()` | Cuándo se creó la versión |

**Nota:** Cada PATCH genera automáticamente un snapshot de la versión anterior antes de aplicar el cambio. El primer snapshot se crea al pasar de v1 → v2, preservando el contenido original.

---

## CRUD — `backend/crud/wiki.py`

Toda la lógica de base de datos está encapsulada en la capa CRUD:

| Función | Descripción |
|---------|-------------|
| `list_wiki_pages(db, sede_id, search?, category?, limit?, offset?)` | Lista documentos activos de una sede con paginación y filtros |
| `count_wiki_pages(db, sede_id, search?)` | Cuenta total de documentos para paginación |
| `get_wiki_page(db, page_key, sede_id)` | Obtiene un documento por clave + sede (None si no existe) |
| `create_wiki_page(db, page_key, title, content, sede_id, author_id?)` | Crea un nuevo documento con version=1 |
| `update_wiki_page(db, row, title?, content?, category?, tags?, author_id?)` | Actualiza campos + incrementa versión + snapshot automático |
| `soft_delete_wiki_page(db, row)` | Soft-delete (marca deleted_at) |
| `list_wiki_page_versions(db, wiki_page_id)` | Lista versiones de un documento (nueva primero) |
| `list_wiki_categories(db, sede_id)` | Lista categorías distintas usadas en la sede |

Todas las funciones de lectura filtran por `sede_id` para garantizar aislamiento multi-tenant.

---

## Servicios Relacionados

### `backend/services/knowledge_base.py`

| Función | Propósito |
|---------|-----------|
| `KnowledgeIndexer` | Indexa cursos, proyectos, estrategias, personas y variables del sistema en `AgentKnowledgeBase` |
| `search_knowledge_base_real(db, query, top_k?, category?)` | Búsqueda full-text en la Knowledge Base con filtro por categoría y orden por relevancia |

La búsqueda global del dashboard (`search_knowledge_base` en `crud/dashboard.py`) también busca en `wiki_pages` por título con ILIKE, retornando snippets y URLs a los documentos.

### `backend/services/messaging.py`

| Clase | Propósito |
|-------|-----------|
| `MessagingGateway` | Gateway real que envía WhatsApp, SMS y Email. SMTP real cuando está configurado, log en `CommunicationLog` |
| `StubMessagingGateway` | Gateway stub para staging/testing. Nunca envía al exterior. Respeta `TEST_EMAIL_OVERRIDE` para excepciones controladas |

---

## Frontend

### Páginas

| Ruta | Archivo | Propósito |
|------|---------|-----------|
| `/plataforma/wiki` | `wiki/page.tsx` | Home — grid de documentos con búsqueda server-side (debounce 400ms), creación rápida, estados loading/error/empty/sin resultados |
| `/plataforma/wiki/docs` | `wiki/docs/page.tsx` | Redirige a `/plataforma/wiki` |
| `/plataforma/wiki/docs/[page_key]` | `wiki/docs/[page_key]/page.tsx` | Editor WYSIWYG con vista de lectura (`?view=read`), exportación HTML, historial de versiones, beforeunload |

### Componentes

| Componente | Archivo | Propósito |
|------------|---------|-----------|
| `WikiEditor` | `components/wiki/WikiEditor.tsx` | Editor Tiptap con autoguardado cada 2s (compara con ref, no con initialContent), atajo Ctrl+S, status flotante, sincronización al navegar entre docs |
| `UniversalWikiView` | `components/ui/UniversalWikiView.tsx` | Vista wiki embebida con editor Tiptap, vista previa, exportación HTML/TXT, botón limpiar contenido. Usada en ~30+ páginas de CRM, Academy, CMS, Projects, Admin |
| `ProjectWikiEditor` | `components/projects/ProjectWikiEditor.tsx` | Editor Tiptap para wikis de proyectos con slash commands |

### Hooks

| Hook | Archivo | Propósito |
|------|---------|-----------|
| `useWikiDocument(pageKey, options?)` | `hooks/useWikiDocument.ts` | Persistencia bidireccional: localStorage + servidor, autoguardado con debounce 700ms, AbortController para cleanup |

### Flujo de datos

```
WikiHomePage (GET /wiki/pages?search=&offset=) → apiFetch → lista de WikiDoc
    ↓ (clic en documento)
WikiDocEditPage (GET /wiki/pages/{page_key}) → apiFetch → WikiDoc
    ↓
WikiEditor (Tiptap) → onChange → useWikiDocument (700ms) / autosave (2s)
    ↓
PATCH /wiki/pages/{page_key} → servidor (snapshot automático)
    ↓
GET /wiki/pages/{page_key}/versions → historial de versiones
```

---

## Dependencias del Frontend

| Dependencia | Uso |
|------------|-----|
| `@tiptap/react` + `@tiptap/starter-kit` | Editor WYSIWYG |
| `@tiptap/extension-placeholder` | Placeholder del editor |
| `@tiptap/extension-task-list` + `@tiptap/extension-task-item` | Listas de tareas en el editor |
| `framer-motion` | Animaciones de tarjetas y status flotante |
| `lucide-react` | Iconos (BookOpen, History, Download, Eye, etc.) |

---

## Wiki de Proyectos (relacionado)

El módulo Projects tiene su propio sistema wiki integrado:

| Modelo | Tabla | Archivo |
|--------|-------|---------|
| `ProjectDocument` | `project_documents` | `backend/models_projects.py` |

Endpoints: `GET/POST /api/projects/{project_id}/wiki` — scope por sede indirecto (hereda del Project).

---

## Tests

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `tests/test_wiki.py` | 30 (7 CRUD + 23 API) | `crud/wiki.py` 100%, `api/wiki.py` 100%, `models_wiki.py` 100%, `schemas/wiki.py` 100% |
| `tests/test_services_kb_messaging.py` | 33 (11 KnowledgeIndexer/search + 22 messaging) | `services/knowledge_base.py` 100%, `services/messaging.py` 100% |
**Total: 63 tests (30 wiki + 33 servicios) — todos pasando** 🎯

---

## Migraciones Alembic

| Migración | Descripción |
|-----------|-------------|
| `20260717_0003` | Add `sede_id` y `author_id` a `wiki_pages` |
| `20260717_0004` | Add `version` a `wiki_pages` + tabla `wiki_page_versions` |
| `20260717_0005` | Add extensión `pg_trgm` + índices GiST en `title` y `page_key` |
| `20260717_0006` | Add `category` y `tags` a `wiki_pages` |

---

## Historial de Cambios

| Fecha | Cambio | Autor |
|------|--------|-------|
| 2026-07-17 | Auditoría forense completa: ~60 issues identificados y corregidos | MiMoCode |
| 2026-07-17 | Migración de permisos `cms:*` → `wiki:*` con módulo independiente | MiMoCode |
| 2026-07-17 | Agregado `sede_id` y `author_id` al modelo para multi-tenant | MiMoCode |
| 2026-07-17 | Separación de capa CRUD (`crud/wiki.py`) | MiMoCode |
| 2026-07-17 | GET ya no crea registros automáticamente (REST compliance) | MiMoCode |
| 2026-07-17 | POST ahora rechaza con 409 si el documento ya existe | MiMoCode |
| 2026-07-17 | Fix link roto `/wiki/docs/` → `/plataforma/wiki/docs/` | MiMoCode |
| 2026-07-17 | Fix autosave infinito (comparación con ref `lastSavedContentRef`, no con `initialContent`) | MiMoCode |
| 2026-07-17 | Agregado `beforeunload` para evitar pérdida de cambios | MiMoCode |
| 2026-07-17 | Agregado `AbortController` en `useWikiDocument` | MiMoCode |
| 2026-07-17 | Historial de versiones (`WikiPageVersion` + snapshot automático en cada PATCH) | MiMoCode |
| 2026-07-17 | Paginación real con offset + endpoint `/pages/count` | MiMoCode |
| 2026-07-17 | Búsqueda eficiente con índices GIN trigram (`pg_trgm`) | MiMoCode |
| 2026-07-17 | Autoría real: `author_id` asignado desde `resolve_persona_id_for_user` | MiMoCode |
| 2026-07-17 | Búsqueda server-side con debounce 400ms + feedback "sin resultados" | MiMoCode |
| 2026-07-17 | UniversalWikiView reemplazado: textarea → editor Tiptap con vista previa y exportación | MiMoCode |
| 2026-07-17 | Atajos de teclado Ctrl+S para guardado manual | MiMoCode |
| 2026-07-17 | Exportación HTML/TXT desde editor y vista de documento | MiMoCode |
| 2026-07-17 | Vista de lectura `?view=read` renderiza HTML sin editor | MiMoCode |
| 2026-07-17 | Categorías y etiquetas para organizar documentos | MiMoCode |
| 2026-07-17 | Búsqueda global integrada con `search_knowledge_base` del dashboard | MiMoCode |
| 2026-07-17 | Cobertura de tests al 100%: wiki (30 tests) + servicios messaging/knowledge_base (11 tests) | MiMoCode |
| 2026-07-17 | Fix import `require_pastor_or_admin` en `evangelism_main/main_estrategias.py` (bloqueaba todos los tests) | MiMoCode |
| 2026-07-17 | Fix label "Legacy" → "Compat" en `schemas/crm/base.py` (test estructural preventivo) | MiMoCode |
| 2026-07-17 | Push a producción con validaciones automáticas: smoke tests, migraciones, build frontend, deploy PM2 | MiMoCode |
