# Original User Request

## Initial Request — 2026-07-30T17:23:07Z

Implementar 4 features que llevan el CMS de CCF (Next.js + FastAPI) a un nivel
superior a WordPress en usabilidad y funcionalidad para crear páginas, posts y popups.

Working directory: /root/ccf
Integrity mode: development

---

## Contexto técnico

- Frontend: Next.js 14 App Router, TypeScript, en `frontend/src/`
- CMS pages: `frontend/src/app/plataforma/cms/`
- TipTap instalado: `@tiptap/*` en `frontend/package.json`
- RichEditor en: `frontend/src/components/cms/RichEditor.tsx` (290 líneas)
- Visual builder en: `frontend/src/app/plataforma/cms/builder/`
- Media picker modal existente: busca `MediaPicker` o `media-picker` en `frontend/src/components/cms/`
- API CMS v2: `backend/api/cms_v2/`
- Posts page: `frontend/src/app/plataforma/cms/posts/page.tsx` (782 líneas)

---

## Requirements

### R1. TipTap conectado a la Media Library (no window.prompt)

En `frontend/src/components/cms/RichEditor.tsx`, la inserción de imágenes
actualmente usa `window.prompt()` para pedir una URL. Debe reemplazarse por
un modal integrado que abra la biblioteca de medios.

Implementar:
- Estado `showImagePicker: boolean` en RichEditor
- Al hacer click en el botón de imagen de la toolbar, abrir un modal simple
  con campo de URL + botón "Buscar en biblioteca"
- Si existe un componente `MediaPicker` en el proyecto, reutilizarlo
- Si no existe, crear un mini-modal en el propio RichEditor que muestre
  los últimos 12 archivos de imagen de `/cms/media?type=image&limit=12`
  como grid de thumbnails clicables
- Al seleccionar una imagen del grid, insertar su URL en el editor
- El modal debe tener campo de texto para escribir URL alternativa
- Mismo fix para la inserción de links: reemplazar `window.prompt` por
  un popover o input inline que aparezca sobre el texto seleccionado

Agregar también `BubbleMenu` de TipTap: menú flotante que aparece al
seleccionar texto con botones de Bold, Italic, Underline, Link.
Instalar si es necesario: `npm install @tiptap/extension-bubble-menu`

### R2. Editor de posts en pantalla completa

En `frontend/src/app/plataforma/cms/posts/page.tsx`, el editor de contenido
del post actualmente vive dentro de un `SidePanel` (panel lateral). Cuando
el usuario hace click en "Editar" un post, debe poder cambiar entre dos modos:

- **Modo compacto** (actual): SidePanel con metadatos + RichEditor pequeño
- **Modo pantalla completa**: overlay/modal que ocupa toda la pantalla con:
  - Columna izquierda (70%): RichEditor con `minHeight="calc(100vh - 120px)"`
  - Columna derecha (30%): metadatos del post (título, categorías, tags,
    estado, fecha de publicación)
  - Barra superior: Botón volver al modo compacto | Botón Guardar | Botón Publicar
  - Atajo de teclado: `Cmd/Ctrl + Shift + F` para toggle pantalla completa

La transición debe ser suave (CSS transition). El modo pantalla completa debe
usar `position: fixed; inset: 0; z-index: 100`.

### R3. Módulo de Popups nativo

Crear un módulo completo de Popups en el CMS:

**Backend** (`backend/api/cms_v2/popups.py`):
- Modelo `CmsPopup` en `backend/models_cms.py` con campos: id (UUID), site_id (FK a cms_sites), name (str), content_html (Text), trigger_type (str: 'time_delay'|'scroll_percent'|'exit_intent'|'on_load'), trigger_value (int, nullable), is_active (bool default True), show_on_pages (JSON array de slugs, vacío = todas), created_at, updated_at
- CRUD endpoints bajo `/api/cms/v2/sites/{site_key}/popups`:
  GET /popups (list), POST /popups (create), GET /popups/{id}, PATCH /popups/{id}, DELETE /popups/{id}
- Endpoint público: `GET /api/cms/v2/public/popups?site_key=X` devuelve popups activos
- Migración Alembic: nueva tabla `cms_popups`
- Registrar el router en `backend/api/cms_v2/__init__.py` o `backend/app.py`

**Frontend** (`frontend/src/app/plataforma/cms/popups/page.tsx`):
- UI premium nivel enterprise igual al resto del CMS
- Lista de popups como tarjetas con nombre, tipo de trigger (badge de color), estado activo/inactivo (toggle)
- Crear/editar popup con SidePanel que tiene:
  - Campo "Nombre" (interno)
  - RichEditor para el contenido HTML del popup
  - Selector visual de tipo de trigger:
    - ⏱ Tiempo (X segundos después de cargar)
    - 📜 Scroll (al llegar al X% de la página)
    - 🚪 Exit Intent (al mover el cursor hacia arriba para cerrar)
    - ⚡ Al cargar (inmediato)
  - Campo numérico para el valor del trigger
  - Toggle activo/inactivo
- Skeleton loaders, estado vacío con ícono, toasts de éxito/error, modal confirmación al eliminar

**PopupManager** (`frontend/src/components/cms/PopupManager.tsx`):
- Componente cliente "use client" que:
  1. Hace fetch a `/api/cms/v2/public/popups?site_key=default` al montar
  2. Para cada popup activo, implementa el trigger:
     - `on_load`: muestra inmediatamente
     - `time_delay`: setTimeout(trigger_value * 1000)
     - `scroll_percent`: window scroll listener
     - `exit_intent`: mouseleave en document con clientY < 10
  3. Renderiza overlay con backdrop oscuro, tarjeta centrada con el contenido HTML, botón X para cerrar
  4. Guarda en sessionStorage `popup_shown_{id}` para no repetir en la sesión
- Importar `PopupManager` en `frontend/src/app/layout.tsx` o en el layout de la plataforma pública

**Nav**: Agregar "Popups" con ícono `Layers` a `frontend/src/components/cms/CmsModuleNav.tsx`

### R4. TipTap mejoras adicionales

En `RichEditor.tsx`, agregar:
- Tablas: instalar `@tiptap/extension-table @tiptap/extension-table-row @tiptap/extension-table-header @tiptap/extension-table-cell` y agregar botón en toolbar
- Color de texto: instalar `@tiptap/extension-color @tiptap/extension-text-style` y agregar 6 swatches de color en toolbar
- Botón de "pantalla completa" en el propio editor (toggle `isFullscreen` state con `position: fixed; inset: 0`)

---

## Acceptance Criteria

### R1 — TipTap + Media Library
- [ ] `grep "window.prompt" frontend/src/components/cms/RichEditor.tsx` devuelve **0 resultados**
- [ ] `grep -i "imagePicker\|showImage\|mediaPicker\|ImageModal" frontend/src/components/cms/RichEditor.tsx` devuelve ≥1 match
- [ ] `grep "BubbleMenu\|bubble-menu" frontend/src/components/cms/RichEditor.tsx` devuelve ≥1 match

### R2 — Editor pantalla completa
- [ ] `grep -i "fullscreen\|fullScreen\|fixed.*inset\|isFullscreen" frontend/src/app/plataforma/cms/posts/page.tsx` devuelve ≥2 matches
- [ ] `grep "Shift\|fullscreen" frontend/src/app/plataforma/cms/posts/page.tsx` devuelve ≥1 match

### R3 — Módulo de Popups
- [ ] `ls frontend/src/app/plataforma/cms/popups/page.tsx` existe
- [ ] `ls backend/api/cms_v2/popups.py` existe
- [ ] `grep "cms_popups\|CmsPopup" backend/api/cms_v2/popups.py` devuelve ≥2 matches
- [ ] `grep "popups\|Popup" frontend/src/components/cms/CmsModuleNav.tsx` devuelve ≥1 match
- [ ] `grep -ri "PopupManager\|trigger_type\|exit.intent" frontend/src/` devuelve ≥3 matches

### R4 — TipTap mejoras
- [ ] `grep "extension-table\|TableRow\|TableHeader" frontend/src/components/cms/RichEditor.tsx` devuelve ≥2 matches
- [ ] `grep "extension-color\|TextStyle\|ColorPicker" frontend/src/components/cms/RichEditor.tsx` devuelve ≥2 matches

### Build y Deploy
- [ ] `cd /root/ccf/frontend && npx next build 2>&1 | grep -c "error TS"` devuelve **0**
- [ ] `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v 2>&1 | tail -3` muestra "passed"
- [ ] `cd /root/ccf && git log --oneline -1` muestra commit con prefijo `feat(cms):`
- [ ] `cd /root/ccf && git status` muestra "nothing to commit, working tree clean"
