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
