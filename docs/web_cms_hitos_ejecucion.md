# Integracion Web FARO + CRM/CMS por Hitos

## Hito 0 - Alineacion de alcance
- Web publica: `frontend/src/app/(public)/faro/*`
- CMS editorial: `frontend/src/app/cms/*`
- Plataforma interna: `frontend/src/app/admin/*` y modulos operativos
- Regla de producto: CMS gestiona contenido, la interfaz publica renderiza con componentes y estilos de la plataforma.

Estado: completado.

## Hito 1 - Modelo de contenido
Se normalizan bloques editables para FARO en:
- `frontend/src/lib/cms/blocks.ts`

Bloques definidos:
- `faro_home_hero`
- `faro_events_hero`
- `faro_testimonios_hero`
- `faro_sermons_hero`
- `faro_courses_hero`
- `faro_discover_hero`
- `faro_about_hero`
- `faro_locations_hero`
- `faro_media_gallery`
- `faro_public_events`

Estado: completado.

## Hito 2 - Base CMS operativa
Se crean rutas faltantes del CMS:
- `frontend/src/app/cms/content/page.tsx`
- `frontend/src/app/cms/media/page.tsx`
- `frontend/src/app/cms/events/page.tsx`

Se corrige enlace admin faltante:
- `frontend/src/app/admin/cms/page.tsx` (redireccion a `/cms`)

Se habilitan endpoints backend para persistencia editorial:
- `backend/api/content.py`
- `backend/api/cms.py`

Endpoints nuevos:
- `GET/PUT/PATCH/POST /api/content/{page_key}`
- `GET /api/content/{page_key}/versions`
- `GET /api/cms/testimonials`, `POST /api/cms/testimonials`
- `GET /api/testimonials`, `POST /api/testimonials`
- `GET /api/admin/testimonials`, `PATCH /api/admin/testimonials/{id}`
- `GET /api/cms/announcements`, `POST /api/cms/announcements`
- `GET /api/announcements`, `GET /api/admin/announcements`

Estado: completado.

## Hito 3 - Integracion FARO prioritaria
Se conecta contenido dinamico (hero) en paginas prioritarias:
- `frontend/src/app/(public)/faro/page.tsx`
- `frontend/src/app/(public)/faro/eventos/page.tsx`
- `frontend/src/app/(public)/faro/testimonios/page.tsx`

Estado: completado.

## Hito 4 - Integracion FARO extendida
Se conecta contenido dinamico (hero) en:
- `frontend/src/app/(public)/faro/predicas/page.tsx`
- `frontend/src/app/(public)/faro/cursos/page.tsx`
- `frontend/src/app/(public)/faro/conocer-a-jesus/page.tsx`
- `frontend/src/app/(public)/faro/nosotros/page.tsx`
- `frontend/src/app/(public)/faro/sedes/page.tsx`

Estado: completado.

## Hito 5 - Operacion editorial
Capacidades entregadas:
- Edicion de bloques JSON por llave y pagina.
- Edicion de galeria de medios por URLs.
- Edicion de agenda publica en bloque de eventos.
- Preview de estructura JSON en editor de contenido.
- Moderacion basica de testimonios persistida en backend JSON.
- Publicacion de anuncios via endpoint CMS persistido.
- Workflow editorial por bloque (`draft`, `in_review`, `approved`, `published`, `archived`).
- Programacion opcional (`publish_at`, `expire_at`) y acciones de transicion.
- Rollback por version en editor de contenido.
- Auditoria de cambios y transiciones en `admin_audit_logs`.
- Media manager robusto con CRUD, filtros y carga de archivos (`/cms/media/upload`).
- Metricas CMS en endpoint dedicado (`/api/cms/metrics`).

Estado: en progreso.

Estado actual: completado para MVP robusto de integracion Web+CMS.

## Hito 6 - Calidad y verificacion
Validaciones ejecutadas:
- Lint sobre archivos modificados: ok.
- Sintaxis backend (`py_compile`) en archivos tocados: ok.
- Smoke API con `fastapi.testclient`:
  - `GET /api/content/faro_home_hero` -> 200
  - `GET /api/cms/testimonials` -> 200
  - `GET /api/testimonials` -> 200
  - `GET /api/cms/announcements` -> 200
  - `GET /api/announcements` -> 200
  - `GET /api/admin/testimonials` sin token -> 401
  - `GET /api/content/faro_home_hero/versions` sin token -> 401
- Typecheck global frontend: falla por errores preexistentes fuera de este alcance (`admin/settings/system` y `academy/course/[id]`).

Estado: en progreso (bloqueado por deuda tecnica previa).

## Checklist operativo de calidad (Go-Live)
- Confirmar login editor/admin y permisos de escritura sobre `/cms`.
- Editar `faro_home_hero` en CMS y validar reflejo en `/faro`.
- Editar `faro_events_hero` y `faro_public_events` y validar `/faro/eventos`.
- Publicar testimonio desde `/community/testimonies/publish` y moderar en `/admin/testimonials`.
- Crear anuncio en `/admin/announcements/new` y validar `/community/announcements`.
- Verificar navbar FARO editable en bloque `faro_nav_items`.
- QA responsive en mobile/desktop para `/faro`, `/faro/eventos`, `/faro/testimonios`.
- Revisar logs de API y auditoria en primer ciclo editorial.

## Comandos de calidad sugeridos
- Backend smoke (sin credenciales): `python scripts/web_cms_smoke.py --base-url http://localhost:8000`
- Backend smoke (con credenciales de editor/admin): `python scripts/web_cms_smoke.py --base-url http://localhost:8000 --username <user> --password <pass>`
- Frontend lint por alcance CMS/FARO: `npm run lint -- --file "src/app/cms/page.tsx" --file "src/app/cms/testimonials/page.tsx" --file "src/components/public/FaroNavbar.tsx" --file "src/app/(public)/faro/eventos/page.tsx"`
