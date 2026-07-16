# Contratos API — CMS CCF

> **Objetivo:** fijar el contrato operativo del CMS entre admin, preview, render público y pruebas.

## 1. Reglas generales

- Prefijos backend: `/api/cms` y `/api/cms/v2`
- Admin CMS y render público no se validan igual
- Contenido público aprobado/publicado puede ser global por diseño editorial
- `site_id`, `sede_id`, `status`, `deleted_at`, `published_at` y `slug` son claves del contrato

Referencia RBAC:

- `docs/CMS_RBAC_MATRIX.md`

## 2. CMS v1 — `backend/api/cms.py`

Áreas:

- testimonials
- announcements
- media
- metrics

Rutas clave:

| Metodo | Ruta |
|---|---|
| `GET/POST` | `/cms/testimonials` |
| `GET/PATCH/DELETE` | `/admin/testimonials/{testimonial_id}` |
| `GET/POST` | `/cms/announcements` |
| `GET/PATCH/DELETE` | `/admin/announcements/{announcement_id}` |
| `GET/POST` | `/cms/media`, `/cms/media/upload` |
| `GET/PATCH/DELETE` | `/cms/media/{item_id}` |
| `POST` | `/cms/media/{item_id}/optimize` |
| `GET` | `/cms/metrics` |

Reglas:

- feeds públicos siguen reglas de publicación/aprobación
- admin se filtra por sede donde aplica
- uploads deben pasar por allow-list y alineación MIME/extension

## 3. CMS v2 — `backend/api/cms_v2.py`

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

Regla:

- tratar estas superficies como CMS enterprise, no como parte menor del editor

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
npx playwright test tests/e2e/cms-public-contract.spec.ts
```

## 10. Notas RBAC actuales

- `cms.py` v1 tiene mutaciones protegidas solo con `cms:read`.
- `cms_v2.py` sí separa mejor lectura (`cms:read`) y mutación (`cms:edit`).
- `enterprise_cms.py` expone muchas rutas con `get_current_user` en vez de `require_module_access("cms", ...)` en la firma.
- ver `CMS_RBAC_MATRIX.md` para la matriz completa y los drift activos.
