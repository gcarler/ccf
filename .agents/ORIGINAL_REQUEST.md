# Original User Request

## Initial Request — 2026-07-30T23:43:02Z

Implementar 5 features avanzadas en el CMS de CCF para completar la plataforma de contenido al nivel enterprise.

Working directory: /root/ccf
Integrity mode: development

## Contexto técnico

- Frontend: Next.js 14 App Router, TypeScript, `frontend/src/`
- Backend: FastAPI + SQLAlchemy + PostgreSQL, `backend/`
- CMS API: `backend/api/cms_v2/` con 101 endpoints existentes
- Modelos CMS: `backend/models_cms.py`
- Builder: `frontend/src/components/cms/builder/` + `frontend/src/hooks/usePageBuilder.ts`
- Public sections: `frontend/src/components/public/cms/sections/`
- PublicSectionRenderer: `frontend/src/components/public/cms/PublicSectionRenderer.tsx`
- WebSockets: FastAPI soporta WebSockets nativos
- Migraciones Alembic: `alembic/canonical_versions/`
- Toasts: `sonner`, Auth: `useAuth`, API: `apiFetch` de `@/lib/http`
- Framer-motion, @dnd-kit ya instalados
- TipTap + RichEditor en `frontend/src/components/cms/RichEditor.tsx`

## Requirements

### R1. Bloques nuevos en el Builder

Agregar 4 nuevos tipos de sección al CMS:

**A. Contador Animado** (tipo: `animated_counter`)
- Props: title (str), items (JSON array: [{label, value, suffix, prefix, duration_ms}])
- Ejemplo: {label: "Miembros", value: 1250, suffix: "+"}
- Renderizado público (`frontend/src/components/public/cms/sections/`): números se animan de 0 al valor final usando `requestAnimationFrame` al entrar en viewport (IntersectionObserver)
- Estilo: números grandes en color primary, label pequeño, grid responsivo

**B. Embed de Video** (tipo: `video_embed`)
- Props: title (str), video_url (str, acepta YouTube/Vimeo/URL directa), caption (str nullable), autoplay (bool default false)
- Renderizado: detecta YouTube (`youtu.be` o `youtube.com`) → `<iframe>` con embed URL; Vimeo → igual; URL directa → `<video>` HTML5
- Aspect ratio 16:9 con fallback de poster
- En el builder: campo URL + preview del tipo detectado

**C. Galeria Masonry** (tipo: `gallery_masonry`)
- Props: title (str), images (JSON array: [{url, alt, caption}]), columns (2|3|4 default 3)
- Renderizado: CSS columns layout (masonry nativa), hover overlay con caption, click abre lightbox full-screen
- Lightbox: overlay oscuro + imagen grande + botones prev/next + teclas arrow + Escape para cerrar

**D. Mapa** (tipo: `map_embed`)
- Props: title (str), address (str), lat (float nullable), lng (float nullable), zoom (int default 14), height_px (int default 400)
- Renderizado: `<iframe>` de OpenStreetMap (`https://www.openstreetmap.org/export/embed.html?bbox=...&marker=lat,lng`) - sin API key necesaria
- En el builder: campo dirección + lat/lng opcionales

Para cada sección nueva:
1. Agregar el tipo a `SECTION_TYPES` en `frontend/src/components/cms/builder/constants.ts`
2. Agregar el componente de renderizado público en `frontend/src/components/public/cms/sections/`
3. Registrar en `PublicSectionRenderer.tsx`
4. Agregar campos de edición en `BuilderSectionInspector.tsx`

### R2. Colaboración en Tiempo Real (Presence)

Indicar qué usuarios están editando la misma página en el builder.

**Backend** (`backend/api/cms_v2/presence.py`):
- Endpoint WebSocket: `WS /api/cms/v2/ws/presence/{site_key}/{slug}`
- Al conectar: autenticar via query param `?token=X`, registrar {user_id, name, avatar_initials, color} en un dict en memoria por `{site_key}/{slug}`
- Broadcast a todos los conectados: lista actual de usuarios presentes
- Al desconectar: remover del dict y broadcast updated list
- Endpoint REST: `GET /api/cms/v2/sites/{site_key}/pages/{slug}/presence` — devuelve lista de usuarios presentes ahora
- Registrar el WebSocket router en `backend/app.py`

**Frontend** (`frontend/src/hooks/usePresence.ts`):
- Hook que recibe `{siteKey, slug, token, user}`
- Abre un WebSocket a `ws(s)://API_HOST/api/cms/v2/ws/presence/{siteKey}/{slug}?token=X`
- Mantiene estado `presenceUsers: {id, name, color, initials}[]`
- Reconexion automática si se desconecta (backoff: 1s, 2s, 4s)
- Cleanup al desmontar

**UI en el builder** (`BuilderCanvas.tsx` o `builder/page.tsx`):
- Barra de "avatares" en la esquina superior derecha del canvas mostrando los usuarios presentes
- Cada avatar: círculo de color aleatorio (asignado por backend) con las iniciales del usuario
- Tooltip al hover: nombre completo
- Si hay más de 4: `+N más`
- Texto pequeño `"X personas editando ahora"` junto a los avatares

### R3. A/B Testing de Secciones

**Backend** (`backend/api/cms_v2/ab_testing.py`):
- Modelo `CmsAbTest` en `backend/models_cms.py`:
  - id (UUID), site_id, page_id (FK cms_pages), name (str)
  - section_a_id (UUID FK cms_sections), section_b_id (UUID FK cms_sections)
  - traffic_split (float 0.0-1.0, ej 0.5 = 50/50)
  - status ('active'|'paused'|'completed')
  - winner_section_id (UUID nullable)
  - created_at, started_at, ended_at
- Modelo `CmsAbTestEvent` en `backend/models_cms.py`:
  - id, test_id (FK), variant ('a'|'b'), event_type ('view'|'click'|'conversion')
  - visitor_id (str, fingerprint anonimizado), created_at
- Endpoints bajo `/api/cms/v2/sites/{site_key}/ab-tests`:
  - CRUD para tests
  - `POST /ab-tests/{id}/record-event` — registra view/click/conversion
  - `GET /ab-tests/{id}/results` — devuelve: views_a, views_b, clicks_a, clicks_b, conversion_rate_a, conversion_rate_b, statistical_significance
- Migración Alembic

**Frontend** (`frontend/src/app/plataforma/cms/ab-testing/page.tsx`):
- Lista de tests activos/pausados/completados
- Crear test: seleccionar página, seleccionar sección A y sección B, definir split %, nombre
- Vista de resultados: barras de progreso para views/clicks/conversion de variante A vs B, badge de ganador si hay significancia estadística (>95%)
- Botón "Aplicar ganador" — reemplaza sección en la página con la variante ganadora
- Agregar a `CmsModuleNav.tsx` con ícono `FlaskConical`

**En el público** (`PublicSectionRenderer`):
- Si una sección tiene un A/B test activo, el renderer llama al endpoint de results para determinar qué variante mostrar basado en un cookie `ab_visitor_id` (o lo genera si no existe)

### R4. Comentarios en Posts del Blog

**Backend** (`backend/api/cms_v2/post_comments.py`):
- Modelo `CmsPostComment` en `backend/models_cms.py`:
  - id (UUID), post_id (FK cms_posts), parent_id (UUID FK auto-referencial nullable, para replies)
  - author_name (str), author_email (str), content (Text)
  - status ('pending'|'approved'|'spam'|'deleted')
  - created_at, updated_at
- Endpoints:
  - `POST /api/cms/v2/public/posts/{post_id}/comments` — crear comentario (requiere nombre + email + contenido, va a status='pending')
  - `GET /api/cms/v2/public/posts/{post_id}/comments` — lista comentarios aprobados con sus replies anidados
  - `GET /api/cms/v2/sites/{site_key}/post-comments` — admin: lista todos los comentarios con filtro por status
  - `PATCH /api/cms/v2/sites/{site_key}/post-comments/{id}` — admin: cambiar status (aprobar/marcar spam/eliminar)
- Migración Alembic

**Frontend admin** (`frontend/src/app/plataforma/cms/comments/page.tsx`):
- Lista de comentarios pendientes de moderación (badge rojo con count)
- Tabs: Pendientes | Aprobados | Spam
- Cada comentario: autor, email, post al que pertenece, extracto del contenido, fecha
- Acciones: Aprobar ✓ | Marcar spam 🚫 | Eliminar 🗑
- Agregar a `CmsModuleNav.tsx` con ícono `MessageCircle` + badge con count de pendientes

**Frontend público** (en `frontend/src/components/public/cms/PostComments.tsx`):
- Componente que carga y muestra comentarios aprobados de un post
- Formulario de nuevo comentario: nombre, email, contenido (textarea)
- Replies anidados (1 nivel): botón "Responder" + formulario inline
- Contador de comentarios visible
- Incluir en la página pública de un post si existe

### R5. Búsqueda Full-Text en el CMS

**Backend** (`backend/api/cms_v2/search.py`):
- Endpoint: `GET /api/cms/v2/search?q=texto&site_key=X&types=pages,posts,announcements&limit=20`
- Busca en `CmsPage` (title, meta_description), `CmsPost` (title, content, excerpt), `CmsSection` (props_json como texto)
- Usa PostgreSQL `ILIKE` con `%q%` o `to_tsvector/to_tsquery` si está disponible
- Devuelve resultados unificados: `{type, id, title, excerpt, url, site_key, updated_at}`
- Ordenados por relevancia (exact match primero, luego partial)

**Frontend admin** (`frontend/src/app/plataforma/cms/search-admin/page.tsx`):
- La página ya existe según el audit anterior — verificar si ya tiene implementación real o es un stub
- Si es stub: implementar con campo de búsqueda, results en lista con tipo (badge), título, extracto, link al editor
- Debounce de 300ms en el input
- Resultados instantáneos mientras escribe

**Frontend público** (`frontend/src/components/public/cms/SearchBar.tsx`):
- Componente de búsqueda pública: input + resultados flotantes
- Al escribir ≥3 caracteres: llama al endpoint público de búsqueda
- Resultados como dropdown: título + tipo + extracto corto
- Click en resultado → navega a la URL del contenido
- `Escape` cierra el dropdown

## Acceptance Criteria

### R1 — Bloques nuevos
- [ ] `grep 'animated_counter\|video_embed\|gallery_masonry\|map_embed' frontend/src/components/cms/builder/constants.ts` devuelve 4 matches
- [ ] `grep -r 'animated_counter\|video_embed\|gallery_masonry\|map_embed' frontend/src/components/public/cms/sections/` devuelve ≥4 matches
- [ ] `grep 'animated_counter\|video_embed\|gallery_masonry\|map_embed' frontend/src/components/public/cms/PublicSectionRenderer.tsx` devuelve ≥4 matches

### R2 — Colaboración en tiempo real
- [ ] `ls backend/api/cms_v2/presence.py` existe
- [ ] `grep 'WebSocket\|websocket' backend/api/cms_v2/presence.py` devuelve ≥1 match
- [ ] `ls frontend/src/hooks/usePresence.ts` existe
- [ ] `grep -i 'presence\|presenceUsers\|editando' frontend/src/components/cms/builder/BuilderCanvas.tsx frontend/src/app/plataforma/cms/builder/page.tsx` devuelve ≥1 match

### R3 — A/B Testing
- [ ] `ls frontend/src/app/plataforma/cms/ab-testing/page.tsx` existe
- [ ] `ls backend/api/cms_v2/ab_testing.py` existe
- [ ] `grep 'CmsAbTest\|cms_ab_tests' backend/models_cms.py` devuelve ≥2 matches
- [ ] `grep 'FlaskConical\|ab-testing\|A/B' frontend/src/components/cms/CmsModuleNav.tsx` devuelve ≥1 match

### R4 — Comentarios en Posts
- [ ] `ls frontend/src/app/plataforma/cms/comments/page.tsx` existe
- [ ] `ls backend/api/cms_v2/post_comments.py` existe
- [ ] `grep 'CmsPostComment\|cms_post_comments' backend/models_cms.py` devuelve ≥1 match
- [ ] `ls frontend/src/components/public/cms/PostComments.tsx` existe
- [ ] `grep 'MessageCircle\|comments\|Comentarios' frontend/src/components/cms/CmsModuleNav.tsx` devuelve ≥1 match

### R5 — Búsqueda Full-Text
- [ ] `ls backend/api/cms_v2/search.py` existe
- [ ] `grep 'ILIKE\|tsvector\|to_tsquery' backend/api/cms_v2/search.py` devuelve ≥1 match
- [ ] `ls frontend/src/components/public/cms/SearchBar.tsx` existe
- [ ] `grep -i 'search\|búsqueda\|buscar' frontend/src/app/plataforma/cms/search-admin/page.tsx` devuelve ≥3 matches

### Build y Deploy
- [ ] `cd /root/ccf/frontend && npx tsc --noEmit 2>&1 | grep -c 'error TS'` devuelve **0**
- [ ] `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v 2>&1 | tail -3` muestra 'passed'
- [ ] `cd /root/ccf && git log --oneline -1` muestra commit con prefijo `feat(cms):`
- [ ] `cd /root/ccf && git status` muestra 'nothing to commit, working tree clean'

## Follow-up — 2026-07-31T00:35:14Z

Completar las **5 fases pendientes** del plan de mejora integral del módulo CMS v2 de la plataforma CCF (Centro Cristiano Faro): documentar la reducción de queries con SQL logging, refactorizar `backend/api/cms_v2.py` en 10 submódulos especializados, implementar suite E2E completa con Playwright (4 flujos críticos), mejorar accesibilidad y SEO (Lighthouse ≥ 90), y cerrar con documentación de arquitectura y runbook de deploy.

Working directory: /root/ccf
Integrity mode: development

---

## Contexto del Proyecto

- **Stack backend:** Python + FastAPI + SQLAlchemy (SQLite/PostgreSQL) — `backend/api/cms_v2.py` (~2000+ líneas), modelos en `backend/models_cms.py`, CRUD en `backend/crud/cms.py`, schemas en `backend/schemas/cms_v2_sections.py`.
- **Stack frontend:** React + TypeScript + Vite — builder en `frontend/src/components/cms/builder/BuilderCanvas.tsx`, renderer público en `frontend/src/components/cms/public/PublicSectionRenderer.tsx`, tipos en `frontend/src/types/cms-v2.ts`.
- **Tests existentes:** pytest en `tests/` (test_cms_v2_coverage.py, test_cms_site_content_defense.py, test_structural_contracts.py). Run con `PYTHONPATH=. python3 -m pytest tests/ -v`.
- **Linting/typecheck:** `cd frontend && npx tsc --noEmit` (0 errores requeridos) y `cd frontend && npm run lint -- --max-warnings=0`.
- **Estado actual (completado):**
  - Fase 0: Preparación y baseline ✅
  - Fase 1: Seguridad (tenant isolation, XSS, IDOR, race conditions) ✅
  - Fase 2: Tipado estricto frontend (47 sub-componentes, discriminated unions) ✅
  - Fase 3 parcial: N+1 queries eliminadas en `public_page` y `public_posts_list` ✅

---

## Requirements

### R1. Fase 3 — Documentar reducción de queries con SQL logging

Habilitar SQL query logging en el entorno de desarrollo para medir el número de queries emitidas por los endpoints `public_page`, `public_post`, `public_menu`, `public_theme` y `public_posts_list` antes y después de las optimizaciones ya implementadas. Documentar los resultados en un archivo de métricas (`docs/cms_query_metrics.md`).

### R2. Fase 4 — Refactor completo de `backend/api/cms_v2.py`

Dividir `backend/api/cms_v2.py` en los siguientes 10 submódulos bajo `backend/api/cms/`:
- `admin/pages.py` — CRUD de páginas y secciones
- `admin/menus.py` — CRUD de menús e ítems
- `admin/themes.py` — CRUD de temas
- `admin/sites.py` — CRUD de sites y configuración
- `public/pages.py` — endpoints públicos de páginas
- `public/menus.py` — endpoints públicos de menús
- `public/posts.py` — endpoints públicos de posts
- `seo.py` — endpoints de SEO y sitemap
- `workflow.py` — servicio `PageWorkflowService` con lógica de transición de estados
- `section_types.py` — CRUD global de tipos de sección

Cada submódulo debe tener su propio `APIRouter`. El archivo original `backend/api/cms_v2.py` debe quedar como punto de entrada que agrega todos los routers (o eliminarse si el enrutamiento central lo absorbe). Definir excepciones de dominio propias: `CmsNotFound`, `CmsPermissionDenied`, `CmsConflict` mapeadas a códigos HTTP consistentes.

### R3. Fase 5 — Suite E2E completa con Playwright

Configurar Playwright en el proyecto e implementar los siguientes 4 flujos E2E críticos del CMS:
1. **Flujo principal:** Login → crear página → agregar sección → publicar → verificar en sitio público.
2. **Flujo de menús:** Editar menú y verificar cambios en navbar del sitio público.
3. **Flujo de medios:** Subir imagen, verificar alt text en la media library y en el sitio público.
4. **Flujo de aislamiento:** Verificar que un usuario de Sede A no puede acceder ni modificar contenido de Sede B.

Los tests E2E deben poder ejecutarse con `npm run test:e2e:cms` (o equivalente) e integrarse en CI.

### R4. Fase 6 — Accesibilidad y SEO

En el componente `PublicSectionRenderer.tsx` y páginas públicas del CMS:
- Garantizar `alt` explícito (no vacío) en todas las imágenes funcionales del CMS.
- Agregar `aria-hidden="true"` en imágenes puramente decorativas.
- Generar un sitemap dinámico XML con las páginas publicadas del CMS (endpoint o archivo estático).
- Alinear `canonical_url` de cada página con la configuración de Next.js/Vite.
- Validar contraste de colores y navegación por teclado en el renderer público.

### R5. Fase 7 — Documentación y cierre

- Actualizar `docs/` con un diagrama de arquitectura del CMS actualizado (texto/Mermaid) que refleje la nueva estructura de submódulos.
- Documentar los contratos de la API CMS con ejemplos de request/response para los endpoints principales (al menos `public_page`, `public_posts_list`, `patch_section`, `transition_cms_page_status`).
- Escribir `docs/cms_runbook.md` con pasos para deploy, rollback y troubleshooting del módulo CMS.
- Actualizar `CHANGELOG.md` con los cambios de todas las fases.

---

## Acceptance Criteria

### Fase 3 — SQL Logging
- [ ] Existe `docs/cms_query_metrics.md` con tabla de queries antes/después para los 5 endpoints.
- [ ] La métrica muestra reducción de queries en `public_page` (de N×5 → 1 batch) y `public_posts_list` (de N×3 → ~3 totales).

### Fase 4 — Refactor Backend
- [ ] Existen los 10 archivos bajo `backend/api/cms/` con sus routers correspondientes.
- [ ] `backend/api/cms_v2.py` tiene < 100 líneas (solo enrutamiento e imports).
- [ ] `PYTHONPATH=. python3 -m pytest tests/ -v` pasa sin regresiones (todos los tests existentes siguen en verde).
- [ ] Existen las clases `CmsNotFound`, `CmsPermissionDenied`, `CmsConflict` en el código backend, mapeadas a 404, 403, 409 respectivamente.
- [ ] `cd frontend && npx tsc --noEmit` = 0 errores (el refactor no rompe contratos de la API consumida en el frontend).

### Fase 5 — Tests E2E
- [ ] `npm run test:e2e:cms` ejecuta los 4 flujos E2E y todos pasan.
- [ ] Existe configuración de Playwright (`playwright.config.ts` o equivalente) en el proyecto.
- [ ] Los tests E2E están en `tests/e2e/cms/` o `frontend/tests/e2e/`.

### Fase 6 — a11y y SEO
- [ ] `grep -rn 'alt=""' frontend/src/components/cms/public/` devuelve 0 resultados (ninguna imagen funcional con alt vacío).
- [ ] Existe un endpoint o archivo de sitemap XML que incluya al menos las páginas publicadas del CMS.
- [ ] Lighthouse a11y score ≥ 90 y SEO score ≥ 90 en la página principal pública del CMS (medido con `npx lighthouse` o herramienta equivalente y documentado).

### Fase 7 — Documentación
- [ ] Existe `docs/cms_architecture.md` o similar con diagrama Mermaid de la arquitectura post-refactor.
- [ ] Existe `docs/cms_runbook.md` con secciones de deploy, rollback y troubleshooting.
- [ ] `CHANGELOG.md` tiene entradas para todas las fases completadas.
- [ ] Existe documentación de contratos API con ejemplos para los 4 endpoints señalados.

### Criterios transversales
- [ ] `cd frontend && npm run lint -- --max-warnings=0` pasa.
- [ ] `cd frontend && npx tsc --noEmit` = 0 errores.
- [ ] `PYTHONPATH=. python3 -m pytest tests/ -v` — todos los tests previos siguen pasando.
- [ ] `git status` muestra working tree clean al finalizar (commit de cierre con prefijo `feat(cms):` o `docs(cms):`).

