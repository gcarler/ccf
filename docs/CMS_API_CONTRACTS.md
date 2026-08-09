# Contratos API — CMS CCF

> **Objetivo:** fijar el contrato operativo del CMS entre admin, preview, render público y pruebas.

## 1. Reglas generales

- Prefijos backend: `/api/cms` y `/api/cms/v2`
- Admin CMS y render público no se validan igual
- Contenido público aprobado/publicado puede ser global por diseño editorial
- `site_id`, `sede_id`, `status`, `deleted_at`, `published_at` y `slug` son claves del contrato

Referencia RBAC:

- `docs/CMS_RBAC_MATRIX.md`

## 2. CMS v1 — `backend/api/cms/v1.py` (compatibilidad de media)

La superficie v1 actualmente montada conserva únicamente media y métricas. Los
feeds administrativos legacy de testimonios/anuncios no son rutas activas; el
contenido editorial nuevo usa CMS v2 con categorías `testimonials` y
`announcements`.

Rutas efectivamente montadas:

| Método | Ruta |
|---|---|
| `GET/POST` | `/cms/media` |
| `GET/PATCH/DELETE` | `/cms/media/{item_id}` |
| `POST` | `/cms/media/upload` |
| `POST` | `/cms/media/{item_id}/edit` |
| `POST` | `/cms/media/{item_id}/optimize` |
| `POST` | `/cms/media/cleanup` |
| `GET` | `/cms/metrics` |

Reglas:

- lecturas requieren `cms:read` y respetan el scope por sede
- mutaciones de media requieren `cms:edit` y un rol de `CMS_EDITOR_ROLES`
- soft-delete de media requiere un rol editorial; hard-delete (`permanent=true`) y cleanup de media huérfana requieren `CMS_PUBLISHER_ROLES`
- uploads deben pasar por allow-list y alineación MIME/extension

## 3. CMS v2 — `backend/api/cms_v2/` (paquete modular)

Áreas:

- section types
- sites
- themes
- menus y items
- pages y sections
- versions
- preview
- workflow
- global blocks
- categories y tags
- posts
- analytics
- schedule
- image optimize

Rutas clave:

| Area | Rutas |
|---|---|
| Section types | `/cms/v2/section-types*` |
| Sites | `/cms/v2/sites*` |
| Themes | `/cms/v2/sites/{site_key}/themes*` |
| Menus | `/cms/v2/sites/{site_key}/menus*` |
| Pages | `/cms/v2/sites/{site_key}/pages*` |
| Sections | `/cms/v2/sites/{site_key}/pages/{slug}/sections*` |
| Preview | `/cms/v2/sites/{site_key}/pages/{slug}/preview` |
| Workflow | `/cms/v2/sites/{site_key}/pages/{slug}/workflow` |
| Versions | `/cms/v2/sites/{site_key}/pages/{slug}/versions*` |
| Global blocks | `/cms/v2/global-blocks*` |
| Categories / Tags | `/cms/v2/sites/{site_key}/categories*`, `/tags*` |
| Posts | `/cms/v2/sites/{site_key}/posts*` |
| Analytics | `/cms/v2/analytics/{page_key}` |
| Schedule | `/cms/v2/pages/{page_id}/schedule` |
| Images | `/cms/v2/images/optimize` |

Reglas:

- no resolver por `id` sin scope contextual válido
- preview y publicado son contratos distintos
- section types globales se desactivan por soft behavior, no hard delete destructivo

## 4. Enterprise CMS — `backend/api/enterprise_cms.py`

Áreas:

- audit logs
- content permissions
- notifications
- webhooks
- custom types / entries
- glossary
- search
- search promotions
- sessions
- media folders
- redirects
- broken links

Rutas clave:

| Area | Rutas |
|---|---|
| Audit logs | `/cms/v2/audit-logs` |
| Content permissions | `/cms/v2/content-permissions*` |
| Notifications | `/cms/v2/notifications*` |
| Webhooks | `/cms/v2/webhooks*`, `/cms/v2/webhooks/{hook_id}/deliveries` |
| Custom types | `/cms/v2/custom-types*` |
| Custom entries | `/cms/v2/custom-entries*`, `/cms/v2/custom-entries/{entry_id}/versions`, `/cms/v2/custom-entries/{entry_id}/rollback/{version_id}` |
| Glossary | `/cms/v2/glossary*` |
| Search | `/cms/v2/search`, `/cms/v2/search/promotions*` |
| Sessions | `/cms/v2/sessions*`, `/cms/v2/sessions/revoke-all` |
| Media folders | `/cms/v2/media-folders*` |
| Redirects | `/cms/v2/redirects*` |
| Broken links | `/cms/v2/broken-links*`, `/cms/v2/broken-links/{check_id}/resolve` |

Reglas:

- tratar estas superficies como CMS enterprise, no como parte menor del editor
- no asumir que autenticación simple equivale a autorización CMS correcta
- en CMS v1, las mutaciones de media exigen `cms:edit` más rol editorial; cleanup exige rol publisher
- Enterprise CMS se valida como superficie separada, con `cms:read` para lectura y `cms:manage` para mutación

## 5. Modelos y scope

Puntos de contrato:

- `CmsMediaItem.sede_id`
- `CmsSite.sede_id`
- `CmsPage.site_id`
- `CmsPage.slug`
- `CmsPage.publish_at` / `expires_at`
- `CmsSection.deleted_at`

## 6. Preview, publicado y público

Hay tres contratos diferentes:

1. **Admin draft**
2. **Preview**
3. **Render público publicado**

No asumir que un fix en uno corrige automáticamente los otros dos.

## 7. Upload hardening

Reglas confirmadas por tests:

- allow-list de extensiones
- `sanitize_filename`
- `validate_mime_extension_alignment`
- rechazo de MIME spoofed
- media archivado no debe reaparecer por endpoints derivados

## 8. Códigos esperados

| Codigo | Uso |
|---|---|
| `200/201/204` | operación exitosa |
| `400` | input inválido, mismatch MIME/ext, flujo inválido |
| `401` | sin autenticación |
| `403` | autenticado sin permiso |
| `404` | recurso inexistente o fuera de scope |

## 9. Validación mínima

```bash
cd /root/ccf
./venv/bin/python scripts/test_cms_quality.py
```

Frontend específico:

```bash
cd /root/ccf/frontend
npx vitest run tests/cms-components.test.ts tests/cms-public-fetch.test.ts
npm run test:e2e:cms
npm run test:e2e:cms:public
```

## 10. Notas RBAC actuales

- `cms/v1.py` conserva media/métricas y separa lectura (`cms:read`) de mutación (`cms:edit` + rol editorial).
- `cms_v2/` separa lectura (`cms:read`) de mutación (`cms:edit`) y reserva las operaciones publisher para roles autorizados.
- `enterprise_cms.py` ahora expresa lectura con `cms:read` y mutación con `cms:manage` en la firma.
- ver `CMS_RBAC_MATRIX.md` para la matriz completa y el contrato RBAC vigente.

---

## 11. Ejemplos de Request/Response — Endpoints Clave

### 11.1 `GET /api/cms/v2/public/sites/{site_key}/pages/{slug}` — Página Pública

**Sin auth requerida.** Devuelve la versión publicada de una página con sus secciones.

**Request:**
```http
GET /api/cms/v2/public/sites/faro/pages/home
```

**Response (200):**
```json
{
  "site_key": "faro",
  "slug": "home",
  "title": "Inicio — Faro CCF",
  "seo_json": {
    "meta_title": "Inicio | Centro Cristiano Faro",
    "meta_description": "Bienvenidos a nuestra iglesia...",
    "og_image": "https://cdn.ccf.com/og-home.jpg"
  },
  "canonical_url": "https://faro.ccf.com/home",
  "sections": [
    {
      "id": "section-uuid",
      "section_key": "hero-main",
      "type": "hero",
      "props_json": {
        "title": "Bienvenidos a Faro",
        "subtitle": "Una comunidad de fe",
        "cta_text": "Conócenos",
        "cta_link": "/pastores",
        "image_url": "https://cdn.ccf.com/hero.jpg"
      },
      "sort_order": 1,
      "is_visible": true
    }
  ]
}
```

**Errores:**
- `404` — Sitio o página no encontrados, o página no publicada.

---

### 11.2 `GET /api/cms/v2/public/sites/{site_key}/posts` — Lista de Posts Públicos

**Sin auth requerida.** Devuelve posts publicados con paginación, filtro por categoría/tag.

**Request:**
```http
GET /api/cms/v2/public/sites/faro/posts?page=1&page_size=10&category=anuncios
```

**Response (200):**
```json
{
  "items": [
    {
      "id": "post-uuid",
      "slug": "campamento-2026",
      "title": "Campamento Juvenil 2026",
      "excerpt": "Este verano viviremos una experiencia única...",
      "cover_image_url": "https://cdn.ccf.com/campamento.jpg",
      "published_at": "2026-07-15T10:00:00Z",
      "author": {
        "id": "persona-uuid",
        "display_name": "Juan Pérez",
        "avatar_url": null
      },
      "categories": [{ "id": "cat-uuid", "name": "Anuncios", "slug": "anuncios" }],
      "tags": [{ "id": "tag-uuid", "name": "juventud" }]
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 10,
  "pages": 5
}
```

**Errores:**
- `404` — Sitio no encontrado.

---

### 11.3 `PATCH /api/cms/v2/sites/{site_key}/pages/{slug}/sections/{section_key}` — Editar Sección

**Auth requerida:** rol `CMS_EDITOR` o `CMS_PUBLISHER`. La sección debe pertenecer a una página del sitio de la sede del actor.

**Request:**
```http
PATCH /api/cms/v2/sites/faro/pages/home/sections/hero-main
Authorization: Bearer <token>
Content-Type: application/json

{
  "props_json": {
    "title": "Bienvenidos — Iglesia Faro",
    "subtitle": "Una comunidad de fe y amor",
    "cta_text": "Únete a nosotros",
    "cta_link": "/contacto"
  },
  "is_visible": true
}
```

**Response (200):**
```json
{
  "id": "section-uuid",
  "page_id": "page-uuid",
  "section_key": "hero-main",
  "type": "hero",
  "props_json": {
    "title": "Bienvenidos — Iglesia Faro",
    "subtitle": "Una comunidad de fe y amor",
    "cta_text": "Únete a nosotros",
    "cta_link": "/contacto"
  },
  "sort_order": 1,
  "is_visible": true,
  "status": "active",
  "updated_at": "2026-07-31T00:00:00Z"
}
```

**Errores:**
- `403` — Sin permisos de editor en el sitio.
- `404` — Sitio, página o sección no encontrada.
- `409` — Conflicto al guardar (IntegrityError).
- `422` — `props_json` no cumple el schema del tipo de sección.

---

### 11.4 `POST /api/cms/v2/sites/{site_key}/pages/{slug}/workflow` — Transición de Estado

**Auth requerida:** rol `CMS_PUBLISHER` para publicar; `CMS_EDITOR` para otras transiciones.

**Transiciones válidas:**
- `draft` → `review` → `approved` → `published`
- `published` → `draft` (unpublish)

**Request (publicar):**
```http
POST /api/cms/v2/sites/faro/pages/home/workflow
Authorization: Bearer <token>
Content-Type: application/json

{
  "action": "publish",
  "comment": "Aprobado para publicación — revisión editorial completada"
}
```

**Response (200):**
```json
{
  "id": "page-uuid",
  "slug": "home",
  "title": "Inicio",
  "status": "published",
  "published_version_id": "version-uuid",
  "publish_at": null,
  "expires_at": null,
  "updated_at": "2026-07-31T00:00:00Z"
}
```

**Errores:**
- `400` — Acción inválida o transición de estado no permitida.
- `403` — Sin permiso de publicación.
- `404` — Sitio o página no encontrada.
- `409` — Conflicto de versión.

**Nota sobre `publish_at` programado:**
```json
// POST con publicación futura:
{
  "action": "schedule",
  "publish_at": "2026-08-01T10:00:00Z"
}
```
