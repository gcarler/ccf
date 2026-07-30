# Original User Request

## 2026-07-30T18:50:58Z

Implementar 3 módulos nuevos en el CMS de CCF (FastAPI + Next.js) que faltan para estar al nivel de WordPress:

Working directory: /root/ccf
Integrity mode: development

---

## Contexto técnico

- Frontend: Next.js 14 App Router, TypeScript, `frontend/src/app/plataforma/cms/`
- Backend: FastAPI, SQLAlchemy, PostgreSQL, `backend/api/cms_v2/`
- Modelos CMS en: `backend/models_cms.py`
- Migraciones Alembic en: `alembic/canonical_versions/`
- Nav del CMS: `frontend/src/components/cms/CmsModuleNav.tsx`
- Patrones existentes: ver `backend/api/cms_v2/popups.py` y `frontend/src/app/plataforma/cms/popups/page.tsx` como referencia de implementación
- TipTap ya instalado, RichEditor en `frontend/src/components/cms/RichEditor.tsx`
- API fetch en frontend: `import { apiFetch } from '@/lib/http'`
- Auth en frontend: `import { useAuth } from '@/context/AuthContext'`
- Toasts: `import { toast } from 'sonner'`

---

## Requirements

### R1. Módulo de Formularios de Contacto

**Backend** (`backend/api/cms_v2/forms.py`):
- Modelo `CmsForm` en `backend/models_cms.py`:
  - id (UUID PK), site_id (FK cms_sites), name (str), description (str nullable)
  - fields (JSON: array de {id, label, type: 'text'|'email'|'phone'|'textarea'|'select'|'checkbox', required: bool, options: list nullable})
  - submit_button_text (str default 'Enviar'), success_message (str)
  - notify_emails (JSON array de emails a notificar), is_active (bool default True)
  - created_at, updated_at
- Modelo `CmsFormSubmission` en `backend/models_cms.py`:
  - id (UUID PK), form_id (FK cms_forms), data (JSON), submitted_at, ip_address (str nullable)
- CRUD endpoints bajo `/api/cms/v2/sites/{site_key}/forms`
- Endpoint público: `POST /api/cms/v2/public/forms/{form_id}/submit` — guarda submission y envía email si `notify_emails` configurado
- Endpoint: `GET /api/cms/v2/sites/{site_key}/forms/{form_id}/submissions` — lista submissions con paginación
- Migración Alembic: tablas `cms_forms` y `cms_form_submissions`
- Registrar router en `backend/api/cms_v2/__init__.py` o donde corresponda

**Frontend** (`frontend/src/app/plataforma/cms/forms/page.tsx`):
- Lista de formularios como tarjetas: nombre, número de campos, submissions count, estado activo/inactivo
- Crear/editar form con:
  - Campo nombre y descripción
  - Constructor de campos drag-reorderable: botón "+ Agregar campo" con selector de tipo (texto, email, teléfono, área de texto, desplegable, checkbox)
  - Cada campo tiene: label, placeholder, required toggle, opciones (si es select)
  - Campo "Texto del botón de envío" y "Mensaje de éxito"
  - Campo "Emails de notificación" (chips)
- Tab "Respuestas" que muestra submissions en tabla paginada con fecha y datos
- Skeleton loaders, estado vacío, toasts, modales de confirmación al eliminar

**Agregar a CmsModuleNav**: entrada "Formularios" con ícono `ClipboardList`

### R2. Newsletter / Email Marketing

**Backend** (`backend/api/cms_v2/newsletter.py`):
- Modelo `CmsNewsletter` en `backend/models_cms.py`:
  - id (UUID PK), site_id (FK), name (str), subject (str), content_html (Text)
  - status ('draft'|'scheduled'|'sent'), scheduled_at (datetime nullable)
  - sent_at (datetime nullable), recipient_count (int default 0)
  - created_at, updated_at
- Modelo `CmsSubscriber` en `backend/models_cms.py`:
  - id (UUID PK), site_id (FK), email (str unique por site), name (str nullable)
  - is_active (bool default True), subscribed_at, unsubscribed_at (nullable)
  - source ('form'|'manual'|'import' default 'manual')
- CRUD endpoints bajo `/api/cms/v2/sites/{site_key}/newsletters`
- CRUD endpoints bajo `/api/cms/v2/sites/{site_key}/subscribers`
- Endpoint: `POST /api/cms/v2/public/subscribe` — suscripción pública (guarda subscriber)
- Endpoint: `POST /api/cms/v2/public/unsubscribe?token=X` — desuscripción
- Endpoint: `POST /api/cms/v2/sites/{site_key}/newsletters/{id}/send` — marca como sent, actualiza recipient_count (envío real via SMTP si configurado, si no: mock exitoso)
- Migración Alembic: tablas `cms_newsletters` y `cms_subscribers`

**Frontend** (`frontend/src/app/plataforma/cms/newsletter/page.tsx`):
- Dos tabs: "Campañas" y "Suscriptores"
- **Tab Campañas**: lista de newsletters con estado (badge: Borrador/Programado/Enviado), subject, fecha de envío, destinatarios
  - Crear/editar newsletter con RichEditor para content_html, campo subject, selector de fecha de envío
  - Botón "Enviar ahora" con modal de confirmación mostrando cuántos suscriptores recibirán
  - Badge de estado con colores: draft=gris, scheduled=azul, sent=verde
- **Tab Suscriptores**: tabla con email, nombre, fecha de suscripción, estado activo/inactivo
  - Botón "+ Agregar" para suscriptor manual
  - Botón "Importar CSV" (input file que lee emails del CSV)
  - Toggle activo/inactivo por suscriptor
  - Contador total visible
- Skeleton loaders, estado vacío, toasts, modales de confirmación

**Agregar a CmsModuleNav**: entrada "Newsletter" con ícono `Mail`

### R3. Editor de Imágenes en Media Library

En `frontend/src/app/plataforma/cms/media/[id]/page.tsx`, agregar un panel
"Editar imagen" que aparece cuando el item es una imagen (`mime_type` contiene 'image').

Implementar usando la Web API nativa Canvas (sin librerías externas):
- **Recorte (Crop)**: área seleccionable con handles en las esquinas. Muestra preview del recorte. Botón "Aplicar recorte".
- **Rotación**: botones -90° y +90°. Preview en tiempo real.
- **Brillo/Contraste**: sliders de -100 a +100. Preview en tiempo real usando CSS filter.
- **Voltear (Flip)**: botones horizontal y vertical.
- **Guardar cambios**: `POST /cms/media/{id}/edit` con el canvas resultado como blob (FormData con campo 'file'). Si el endpoint no existe en backend, crearlo en `backend/api/cms_v2/` o `backend/api/cms.py`.
- La edición es **no destructiva**: guarda una copia editada, no sobreescribe el original. Agrega sufijo `_edited` al filename.
- UI: modal de pantalla completa con el canvas en el centro y controles en sidebar derecho.

---

## Acceptance Criteria

### R1 — Formularios
- [ ] `ls frontend/src/app/plataforma/cms/forms/page.tsx` existe
- [ ] `ls backend/api/cms_v2/forms.py` existe
- [ ] `grep 'CmsForm\|cms_forms' backend/models_cms.py` devuelve ≥2 matches
- [ ] `grep 'CmsFormSubmission\|cms_form_submissions' backend/models_cms.py` devuelve ≥1 match
- [ ] `grep 'forms\|Formularios' frontend/src/components/cms/CmsModuleNav.tsx` devuelve ≥1 match
- [ ] `grep 'ClipboardList' frontend/src/components/cms/CmsModuleNav.tsx` devuelve ≥1 match

### R2 — Newsletter
- [ ] `ls frontend/src/app/plataforma/cms/newsletter/page.tsx` existe
- [ ] `ls backend/api/cms_v2/newsletter.py` existe
- [ ] `grep 'CmsNewsletter\|cms_newsletters' backend/models_cms.py` devuelve ≥2 matches
- [ ] `grep 'CmsSubscriber\|cms_subscribers' backend/models_cms.py` devuelve ≥1 match
- [ ] `grep 'newsletter\|Newsletter' frontend/src/components/cms/CmsModuleNav.tsx` devuelve ≥1 match

### R3 — Editor de imágenes
- [ ] `grep -i 'crop\|rotate\|canvas\|brightness\|flip' frontend/src/app/plataforma/cms/media/\[id\]/page.tsx` devuelve ≥5 matches
- [ ] `grep 'cms/media.*edit\|media.*edit' backend/api/cms_v2/*.py backend/api/cms.py 2>/dev/null` devuelve ≥1 match

### Build y Deploy
- [ ] `cd /root/ccf/frontend && npx tsc --noEmit 2>&1 | grep -c 'error TS'` devuelve **0**
- [ ] `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v 2>&1 | tail -3` muestra 'passed'
- [ ] `cd /root/ccf && git log --oneline -1` muestra commit con prefijo `feat(cms):`
- [ ] `cd /root/ccf && git status` muestra 'nothing to commit, working tree clean'

## 2026-07-30T22:07:06Z

Implementar edición WYSIWYG inline en el constructor visual de páginas del CMS de CCF.

Working directory: /root/ccf
Integrity mode: development

## Contexto técnico

- Builder: `frontend/src/app/plataforma/cms/builder/page.tsx`
- Estado del builder: `frontend/src/hooks/usePageBuilder.ts` (841 líneas)
- Canvas: `frontend/src/components/cms/builder/BuilderCanvas.tsx` (212 líneas)
- Preview de sección: `frontend/src/components/cms/builder/SectionPreview.tsx` (317 líneas) — YA usa `PublicSectionRenderer`
- Inspector de propiedades: `frontend/src/components/cms/builder/BuilderSectionInspector.tsx` (1533 líneas)
- Panel derecho: `frontend/src/components/cms/builder/BuilderRightPanel.tsx` (792 líneas)
- Sidebar: `frontend/src/components/cms/builder/BuilderSidebar.tsx` (97 líneas)
- Renderer público: `frontend/src/components/public/cms/PublicSectionRenderer.tsx`
- Secciones públicas en: `frontend/src/components/public/cms/sections/`
- Tipos CMS: `frontend/src/types/cms-v2.ts`
- API de secciones: `frontend/src/lib/cms/v2.ts` — función `updateCmsSectionProps`

El builder YA muestra las secciones con PublicSectionRenderer. Lo que FALTA es edición inline.

## Requirements

### R1. Overlay de controles al hacer hover sobre secciones

En `BuilderCanvas.tsx`, cuando el usuario pasa el ratón sobre una sección en el canvas, mostrar una overlay con:
- Barra superior pegada al borde de la sección con: `⬆ Mover arriba` | `⬇ Mover abajo` | `⧉ Duplicar` | `✕ Eliminar`
- Borde azul/primary de 2px alrededor de la sección al hacer hover
- Cursor `pointer` en toda la sección
- Click en la sección → la selecciona (activa) sin abrir panel derecho todavía
- La overlay no debe aparecer cuando `canvasMode === 'esquema'`

El overlay debe ser `position: absolute` con `pointer-events: none` en el contenedor y `pointer-events: auto` solo en los botones de control, para no bloquear el contenido.

### R2. Modo WYSIWYG con edición de texto inline por doble-click

Agregar un nuevo modo de canvas `'wysiwyg'` al tipo `canvasMode` en `usePageBuilder.ts`.

Cuando `canvasMode === 'wysiwyg'`:

En `SectionPreview.tsx`, al hacer doble-click sobre la sección, activar un panel de edición rápida INLINE que aparece como un overlay flotante encima de la sección con:
- Campos de texto editables para los campos clave según el tipo de sección:
  - `hero`: title, subtitle, cta_text, cta_url
  - `cards`: title, subtitle
  - `rich_text`: title, body (textarea)
  - `cta_banner`: headline, subtext, cta_text, cta_url
  - `stats`: title
  - `team`: title, subtitle
  - `testimonials`: title
  - `faq`: title
  - Cualquier otro tipo: mostrar `title` y `subtitle` si existen en props_json
- Cada campo editable es un `<input>` o `<textarea>` (según longitud) que inicia con el valor actual de `props_json`
- Al escribir, actualiza el estado local inmediatamente
- Al hacer blur o presionar Enter (en inputs de una línea), llama a `updateCmsSectionProps` con los nuevos props
- Botón `✓ Guardar` y `✕ Cerrar` en la esquina superior derecha del overlay
- El overlay tiene fondo semi-transparente (`bg-white/95 dark:bg-gray-900/95`), sombra y border-radius
- Tecla Escape → cierra el overlay sin guardar

### R3. Botón toggle WYSIWYG en toolbar del canvas

En `BuilderCanvas.tsx`, agregar en la barra de herramientas superior un botón:
- `Esquema` → `canvasMode = 'esquema'` (modo lista actual)
- `Render` → `canvasMode = 'render'` (modo renderizado actual)
- `✏ WYSIWYG` → `canvasMode = 'wysiwyg'` (nuevo modo con edición inline)

El botón WYSIWYG debe tener ícono `Pencil` de lucide-react y badge `Nuevo` (pequeño badge verde) la primera vez.

Cuando se activa WYSIWYG:
- El canvas muestra las secciones renderizadas con `PublicSectionRenderer` (igual que modo 'render')
- Un tooltip/banner aparece 1 vez: `"Doble-click en una sección para editar el texto directamente"`
- El panel derecho (BuilderRightPanel) permanece visible para edición avanzada

### R4. Persistencia de cambios inline con debounce

En el panel de edición inline del R2:
- Al modificar un campo, actualizar el estado local del builder inmediatamente (para ver el cambio en tiempo real en la sección renderizada debajo)
- Llamar a `updateCmsSectionProps` con debounce de 800ms para no saturar el API
- Mostrar un indicador pequeño `"Guardando..."` durante el debounce y `"✓ Guardado"` al completar
- Si hay error al guardar, mostrar `toast.error("No se pudo guardar los cambios")`

## Acceptance Criteria

### R1 — Hover overlay
- [ ] `grep -n "hover\|onMouseEnter\|onMouseLeave" frontend/src/components/cms/builder/BuilderCanvas.tsx` devuelve ≥3 matches
- [ ] `grep -n "Mover arriba\|Mover abajo\|Duplicar\|pointer-events" frontend/src/components/cms/builder/BuilderCanvas.tsx` devuelve ≥2 matches

### R2 — Edición inline
- [ ] `grep -n "onDoubleClick\|wysiwyg\|inline.*edit\|InlineEditor\|inlineEdit" frontend/src/components/cms/builder/SectionPreview.tsx` devuelve ≥3 matches
- [ ] `grep -n "wysiwyg" frontend/src/hooks/usePageBuilder.ts` devuelve ≥1 match

### R3 — Toggle WYSIWYG
- [ ] `grep -n "wysiwyg\|WYSIWYG\|Pencil" frontend/src/components/cms/builder/BuilderCanvas.tsx` devuelve ≥2 matches

### R4 — Debounce y guardado
- [ ] `grep -n "debounce\|Guardando\|Guardado" frontend/src/components/cms/builder/SectionPreview.tsx` devuelve ≥2 matches

### Build y Deploy
- [ ] `cd /root/ccf/frontend && npx tsc --noEmit 2>&1 | grep -c 'error TS'` devuelve **0**
- [ ] `cd /root/ccf && PYTHONPATH=. python3 -m pytest tests/test_structural_contracts.py -v 2>&1 | tail -3` muestra 'passed'
- [ ] `cd /root/ccf && git log --oneline -1` muestra commit con prefijo `feat(cms):`
- [ ] `cd /root/ccf && git status` muestra 'nothing to commit, working tree clean'
