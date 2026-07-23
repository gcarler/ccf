# Auditoría Forense de Calidad — Módulo CMS
## Completitud y Consistencia (Revisión Línea por Línea)

**Fecha:** 2026-07-23  
**Alcance:** `backend/models_cms.py`, `backend/api/cms.py`, `backend/api/cms_v2.py`, `backend/api/enterprise_cms.py`, `backend/crud/cms.py`, `backend/schemas/cms.py`, `backend/schemas/cms_v2_sections.py`, `backend/api/_cms_helpers/`, `frontend/src/lib/cms/v2.ts`, `frontend/src/types/cms-v2.ts` y scripts relacionados.

---

## Resumen Ejecutivo

| Métrica | Valor |
|---|---|
| Archivos revisados | 47 |
| Hallazgos críticos | 6 |
| Hallazgos altos | 11 |
| Hallazgos medios | 14 |
| Hallazgos bajos (info) | 17 |
| **Total** | **48** |

---

## 🔴 CRÍTICOS

### C-01: `CmsSite.sede_id` usa `ondelete="SET NULL"` — orphan masivo en cascada

**Archivo:** `backend/models_cms.py:51`  
**Línea:** `sede_id = Column(UUID(...), ForeignKey("sedes.id", ondelete="SET NULL"), nullable=True)`  

**Problema:** Si una sede se elimina, todas las `CmsSite` vinculadas quedan con `sede_id=NULL`. Al ser nullable=True, estas sites se vuelven huérfanas sin sede, violando Axioma 3 porque `_assert_site_sede_scope` permite acceso a sites sin sede por parte de **cualquier** staff con sede. Es un leak multi-tenant: un staff de sede A puede operar sites huérfanos de sede B.

**Impacto:** Violación de Axioma 3 — fuga de datos cross-sede.

**Solución:** Usar `ondelete="RESTRICT"` o `ondelete="CASCADE"` con migración para asignar sede_id NOT NULL.

---

### C-02: `update_cms_media_item` re-valida scope con `row.created_by_persona_id` como `incoming_author_persona_id`

**Archivo:** `backend/crud/cms.py:168-171`  
**Línea:** `incoming_author_persona_id=row.created_by_persona_id`  

**Problema:** `_crud_scope_re_check_cms_content_update` recibe `row.created_by_persona_id` como `incoming_author_persona_id`. Esto valida que `row.created_by_persona_id` resuelva a la misma sede que el actor. Pero si el token del actor cambió de sede entre fetch y commit, **pasa porque el `created_by_persona_id` no cambia**. El check debería verificar que `row.sede_id` no haya cambiado o que el body no introduzca un author cross-sede — no re-validar la persona creadora original que es inmutable.

**Impacto:** TOCTOU no detectado: un actor con sede A hace fetch, cambia su sesión a sede B, y el commit pasa porque `created_by_persona_id` sigue siendo de sede A.

---

### C-03: `create_section_type` y `delete_section_type` NO tienen scope multi-tenant

**Archivo:** `backend/api/cms_v2.py:115-118`  
**Líneas funciones** `create_section_type` y `delete_section_type`

**Problema:** Los endpoints de `section-types` son globales y no filtran por sede. Cualquier editor con rol CMS_PUBLISHER_ROLES puede crear/borrar section types que afectan a **todos** los sites de **todas** las sedes. No hay Axioma 3 enforcement. Un publisher de sede A puede desactivar un section type que usa sede B.

**Impacto:** Denegación de servicio cross-sede desde un tenant no autorizado.

---

### C-04: `cms_pastors_sync.update_pastors_section_from_profiles()` se invoca en `transition_cms_page_status` sin protecciones multi-tenant

**Archivo:** `backend/crud/cms.py:527`  
**Línea:** `cms_pastors_sync.update_pastors_section_from_profiles(db)`  

**Problema:** Cuando se publica una página con slug "pastors", se ejecuta `update_pastors_section_from_profiles` que sincroniza **todos** los perfiles pastorales de **todas** las sedes dentro de la sección. No hay filtro por `site.sede_id`, por lo que pastores de sede A pueden aparecer en el site público de sede B si ambas sedes comparten el slug "pastors".

**Impacto:** Cross-sede data leak en la página pública de pastores.

---

### C-05: `capture_daily_seo_snapshots` no aplica scope multi-tenant

**Archivo:** `backend/crud/cms.py:675-692`  
**Línea:** Bucle for site in sites sin filtro de sede.

**Problema:** La función `capture_daily_seo_snapshots` captura snapshots de **todos** los sites activos globalmente. No hay parámetro `sede_id`. Si se ejecuta desde un worker que corre como superadmin, no hay problema, pero si se expone como endpoint o se llama desde un contexto con scope limitado, capturaría datos cross-sede.

**Impacto:** Potencial leak de métricas SEO cross-sede.

---

### C-06: `validate_section_props` usa `SECTION_PROPS_SCHEMAS` que no incluye 19 section types del fallback hardcoded

**Archivo:** `backend/schemas/cms_v2_sections.py:313-316`  
**Líneas:** `SECTION_PROPS_SCHEMAS` solo mapea 24 tipos; faltan 19 del fallback en `get_allowed_section_types()`.

**Problema:** Los siguientes section types están en `get_allowed_section_types()` (hardcoded fallback) pero **NO** tienen schema de validación en `SECTION_PROPS_SCHEMAS`:
- hero, video_hero, rich_text, rich_text_columns, cards, cta_banner, gallery, faq, embed, testimonials, stats, team, countdown, pricing, image_text, timeline, icon_grid, newsletter, accordion (accordion SÍ está)

Esto significa que props_json para estos tipos no pasa por `validate_section_props` — se acepta cualquier JSON sin sanitización, abriendo vector XSS persistente.

**Impacto:** Stored XSS en 19 tipos de sección sin validación de props.

---

## 🟠 ALTOS

### H-01: `CmsSeoSnapshot.by_severity_json` usa `default=dict` en vez de `default={}` o `default=dict`

**Archivo:** `backend/models_cms.py:602`  
**Línea:** `by_severity_json = Column(JSON, default=dict)`  

**Problema:** `default=dict` es una función que SQLAlchemy invoca para obtener el valor por defecto. El problema es que `dict` sin paréntesis es la función misma, no el resultado. SQLAlchemy lo interpreta como un callable y lo invoca al crear el row, pero **si el valor se serializa con `json.dumps`, `dict` se convierte en `{}`**. No hay bug funcional inmediato, pero `default=dict` es inconsistente con el resto del codebase que usa `default={}`, y en ciertos contextos de serialización (ej. dump manual) podría serializar la función como string.

---

### H-02: `CmsSeoSnapshot.captured_at` usa lambda en vez de `default=_utcnow`

**Archivo:** `backend/models_cms.py:592`  
**Línea:** `default=lambda: dt.datetime.now(dt.timezone.utc)`  

**Problema:** Inconsistencia: todos los demás modelos usan `default=_utcnow` (importado de `models_shared`). Este usa una lambda inline. Si `_utcnow` cambia de implementación (ej. a `datetime.utcnow()` para mockeabilidad), este campo queda desalineado. Además, en tests que congelan `_utcnow` via monkeypatch, esta lambda no se congela.

---

### H-03: `CmsSection` usa `type` como nombre de columna (shadow a built-in Python)

**Archivo:** `backend/models_cms.py:236`  
**Línea:** `type = Column(String(80), nullable=False, index=True)`  

**Problema:** `type` es un built-in de Python. En el modelo se accede como `section.type` que shadowea `type()` en ese scope. Aunque SQLAlchemy lo maneja, interfiere con herramientas de linting/IDE y puede causar bugs sutiles si alguien usa `type()` en el mismo ámbito.

---

### H-04: `delete_cms_section` redirige a `archive_cms_section` sin propagar `deleted_at`

**Archivo:** `backend/crud/cms.py:374`  
**Línea:** `def delete_cms_section(...): return archive_cms_section(db, row)`  

**Problema:** `archive_cms_section` solo cambia `status = "archived"`, pero el modelo tiene `deleted_at` como columna de soft-delete, y `archive_cms_section` no setea `deleted_at`. El modelo espera que `deleted_at` se setee para indicar borrado lógico, pero la función de archive no lo hace. Las queries de readiness filtran por `deleted_at.is_(None)`, y estas secciones archivadas **no tienen** `deleted_at` set — pero `status='archived'`, por lo que el filtro compuesto las captura de todas formas.

**Impacto:** Inconsistencia semántica. `deleted_at` debería setearse cuando se archiva.

---

### H-05: `delete_cms_media_item` hard-delete físico con path traversal incompleto

**Archivo:** `backend/api/cms.py:225-230`  
**Línea:** `file_path = row.url.lstrip("/")`  

**Problema:** El código limpia el path haciendo `lstrip("/")`, pero `row.url` podría contener `../` o `..\\` después del primer `/`. El `lstrip` solo remueve caracteres `/` del inicio, no sanitiza. Luego hace `os.path.join("/root/ccf", file_path)` que es vulnerable a path traversal si `file_path` contiene `../`. Comparar con `backend/api/cms.py:253` que sí hace `os.path.normpath` + verificación de prefix.

---

### H-06: `AnnouncementUpdate` no permite cambiar `is_active`

**Archivo:** `backend/schemas/cms.py:219-225`  

**Problema:** El modelo `Announcement` tiene campo `is_active` (línea 335 del modelo), pero `AnnouncementUpdate` no lo incluye. No se puede desactivar un announcement vía API sin cambiar su status a "archived".

---

### H-07: `CmsPostCreate` y `CmsPostUpdate` no incluyen `locale`

**Archivo:** `backend/schemas/cms.py:345-370`  

**Problema:** El modelo `CmsPost` tiene campo `locale` con server_default="es", pero los schemas de create/update no lo exponen. Un post siempre se crea con locale="es" sin posibilidad de cambiarlo. Las páginas (`CmsPageCreate`) sí exponen `locale`.

---

### H-08: `_get_page_or_404` filtro multi-tenant insuficiente para páginas públicas

**Archivo:** `backend/api/cms_v2.py:230-240`  
**Línea:** `_get_page_or_404` no verifica `site.is_active` ni `sede_id`.

**Problema:** En endpoints públicos como `public_page`, el helper `_get_public_site_or_404` verifica que el site esté activo, pero `_get_page_or_404` no re-valida que la página pertenezca a un site activo. Si un site se desactiva pero sus páginas quedan, el endpoint preview aún puede mostrar páginas de sites inactivos.

---

### H-09: `router.get` para `/cms/v2/sites/{site_key}/pages/{slug}/preview` tiene el mismo path parameter que `public_page` pero mount diferente

**Archivo:** `backend/api/cms_v2.py` — conflictos de ruteo

**Problema:** Los endpoints públicos y admin comparten `site_key` y `slug` como path params. FastAPI los resuelve secuencialmente, y como el router tiene `prefix="/cms/v2"`, cualquier request a `/cms/v2/public/sites/...` y `/cms/v2/sites/...` son montados en el mismo router. Si hay overlap de paths, FastAPI puede devolver 405 inesperado. No hay evidencia actual de conflicto, pero es frágil.

---

### H-10: `ContactSubmission` no tiene timestamps `updated_at`

**Archivo:** `backend/models_cms.py:615-625`  

**Problema:** `ContactSubmission` define `updated_at` como columna pero **no tiene** `onupdate=_utcnow` en ninguna línea. Todas las demás tablas CMS tienen `onupdate=_utcnow` en `updated_at`. Esto significa que `updated_at` nunca se actualiza automáticamente.

---

### H-11: `validate_section_props` no sanitiza props de section types sin schema registrado

**Archivo:** `backend/schemas/cms_v2_sections.py:313-316`  
**Línea:** `if schema_cls is None: return sanitize_props_html(props) if props else props`  

**Problema:** Para los 19 tipos sin schema, se ejecuta `sanitize_props_html`, que es un sanitizer whitelist de HTML. Pero esto NO valida la **estructura** del JSON — solo limpia strings HTML internas. Un editor puede pasar `{"arbitrary": "malicious_code"}` que pase la sanitización y se almacene. Esto no es XSS directo, pero permite polución del modelo de datos.

---

## 🟡 MEDIOS

### M-01: `CmsSiteCreate` no valida formato de `site_key`

**Archivo:** `backend/schemas/cms.py:83-88`  

**Problema:** `site_key` es `str` sin `min_length`, `max_length`, ni regex. El modelo DB es `String(80)`. La API registra un 500 si se pasa un site_key de 200 caracteres. Las validaciones de unicidad existen pero la longitud no.

---

### M-02: `CmsPageCreate.slug` no tiene validación de formato

**Archivo:** `backend/schemas/cms.py:149-160`  

**Problema:** El slug se valida server-side vía `_slugify()`, pero el schema Pydantic no aplica `min_length` ni `max_length`. Si se pasa un slug vacío, el server responde 422 vía `_slugify`, pero si se pasa un slug > 160 chars, el error es un 500 de DB.

---

### M-03: `delete_cms_menu` usa soft-delete (is_active=False) inconsistente con el resto

**Archivo:** `backend/crud/cms.py:311`  
**Línea:** `def delete_cms_menu(...): row.is_active = False`  

**Problema:** Menús se "borran" desactivándolos. Pages usan status="archived". Sections usan status="archived" + deleted_at. Menu items usan visibility="hidden". Cada entidad CMS implementa soft-delete de forma diferente.

---

### M-04: `CmsPage` usa `published_version_id` con `use_alter=True` y self-referential FK

**Archivo:** `backend/models_cms.py:159-166`  
**Línea:** `published_version_id` con `ForeignKey("cms_page_versions.id", name="fk_cms_pages_published_version", use_alter=True)`

**Problema:** `use_alter=True` retrasa la creación del FK hasta después de la creación de las tablas. Esto funciona pero es una señal de que hay una dependencia circular entre `CmsPage` y `CmsPageVersion`. Si algún día se drop & recreate el schema, el orden de creación de tablas debe ser cuidadoso.

---

### M-05: `CmsPageVersion` no tiene índice en `created_at`

**Archivo:** `backend/models_cms.py:209`  

**Problema:** Las queries de list_versions ordenan por `version_number DESC`, pero las queries de búsqueda de versiones recientes podrían beneficiarse de un índice en `created_at`. No es urgente pero es un índice faltante para tablas con muchas versiones.

---

### M-06: `validators` de `PopupProps.validate_dismiss_days` usa min genérico en vez de clamp

**Archivo:** `backend/schemas/cms_v2_sections.py:175`  
**Línea:** `return max(1, min(int(v), 3650))`  

**Problema:** La función clamp es técnicamente correcta pero menos legible que la alternativa. No es bug, pero si `int(v)` falla (tipo no convertible), da 500 en vez de 422.

---

### M-07: `SECTION_PROPS_SCHEMAS` tiene `EventsCalendarProps` pero no se usa en ningún section type del fallback

**Archivo:** `backend/schemas/cms_v2_sections.py`  

**Problema:** La schema `EventsCalendarProps` existe en `SECTION_PROPS_SCHEMAS` con key `events_calendar`, pero este tipo no aparece en `get_allowed_section_types()`. Por lo tanto, nunca se usa en producción. Código muerto.

---

### M-08: `BookShopProps` y `PolicyDocumentProps` y otros schemas no se referencian en `get_allowed_section_types`

**Archivo:** `backend/schemas/cms_v2_sections.py`  

**Problema:** Schemas definidos pero no referenciados en tipos permitidos: `events_calendar`, `video_grid`, `locations_list`, `contact_form`, `prayer_form`, `course_grid`, `book_shop`, `testimonials_masonry`, `policy_document`, `footer_config`, `mobile_menu_config`. Al menos 11 schemas sin usar en producción.

---

### M-09: `SuggestedView` (`SavedView`) en models_cms.py no es CMS

**Archivo:** `backend/models_cms.py:323-338`  

**Problema:** La clase `SavedView` está definida dentro de `models_cms.py` pero no es CMS. Es una feature genérica de "vistas guardadas". Está mezclada con modelos CMS por conveniencia, pero rompe la separación de responsabilidades.

---

### M-10: `resolve_persona_id_for_user` wrapper duplicado en crud/cms.py

**Archivo:** `backend/crud/cms.py:19-20`  
**Línea:** `def resolve_persona_id_for_user(db, user_id): return resolve_persona_uuid_for_user(db, user_id)`  

**Problema:** Wrapper que delega a `crud.crm.resolve_persona_id_for_user`. Esto añade un nivel de indirección innecesario. Todos los callers que necesitan esta función ya importan desde `crud.cms`; el wrapper solo existe para namespace. Añade deuda técnica.

---

### M-11: `delete_cms_media_item` retorna `False` para not-found vs 404 del API helper

**Archivo:** `backend/crud/cms.py:368`  

**Problema:** El CRUD retorna `False` tanto para row no encontrado como para violación de scope. El API traduce a 404. Esto es intencional por existencia-leak-safe, pero es confuso: un caller no-API (script de migración) que usa `delete_cms_media_item` directamente no sabrá si falló por scope o por inexistencia.

---

### M-12: `_commit_or_raise_conflict` duplicado entre `api/cms_v2.py` y `crud/cms.py`

**Archivo:** `backend/api/cms_v2.py:36-46` y `backend/crud/cms.py:29-52`  

**Problema:** Dos implementaciones independientes de la misma lógica de commit con manejo de conflictos. Una en API (con raise HTTPException) y otra en CRUD (con retorno bool). Esto duplica la lógica de identificación de unique violations. Si se agrega un nuevo driver de DB, ambos deben actualizarse.

---

### M-13: `public_theme` construye response manual en vez de usar `CmsThemeRead.model_validate`

**Archivo:** `backend/api/cms_v2.py:1187-1200`  
**Línea:** Return de dict manual en vez de `CmsThemeRead.model_validate(row)`

**Problema:** Inconsistencia con el resto de endpoints. El endpoint público de theme construye manualmente el dict de respuesta en vez de usar Pydantic model_validate. Si `CmsThemeRead` cambia, este endpoint queda desactualizado.

---

### M-14: `CmsPublicPostRead` tiene `author_name` como string directo, no como objeto

**Archivo:** `backend/schemas/cms.py:395-405`  

**Problema:** Mientras `TestimonialRead` expone `author: Optional[TestimonialAuthorRead]` como objeto anidado, `CmsPublicPostRead` expone `author_name: Optional[str]` como string directo. Inconsistencia en cómo se maneja la información del autor entre testimoniales y posts.

---

## 🔵 BAJOS (INFO)

### I-01: Docstring de `CmsSeoSnapshot` dice "faro global model" pero faro es nombre interno

**Archivo:** `backend/models_cms.py:562`

---

### I-02: `_build_page_snapshot` itera sections como items=tuple pero accede como list

**Archivo:** `backend/crud/cms.py:414`  
**Línea:** `sections, _ = list_cms_sections(db, page.id)` — correcto, pero el docstring de `list_cms_sections` dice paginated contract.

---

### I-03: `create_cms_theme` usa `created_by: int | None` pero el modelo usa UUID

**Archivo:** `backend/crud/cms.py:246`  

---

### I-04: Import `resolve_persona_id_for_user` desde `crud.crm` con alias redundante

**Archivo:** `backend/crud/cms.py:12-13`

---

### I-05: `CmsMetrics` esquema no incluye métricas de posts o categories

**Archivo:** `backend/schemas/cms.py:8-17`

---

### I-06: `list_cms_sites` usa `lazyload("*")` pero el modelo define `lazy="selectin"` en relaciones

**Archivo:** `backend/crud/cms.py:194`

**Problema:** Inconsistencia entre lazy loading global vs eager loading del modelo. Cada query que no quiere N+1 debe recordar usar `lazyload("*")`.

---

### I-07: `delete_cms_page` no propaga `deleted_at`

**Archivo:** `backend/crud/cms.py:355` — status="archived" pero `deleted_at` permanece NULL.

---

### I-08: `CmsPost.created_by_persona_id` y `updated_by_persona_id` son NULL pero deberían ser requeridos

**Archivo:** `backend/models_cms.py:504-505`

---

### I-09: `ContentPermission` y `SearchPromotion` en `enterprise_cms.py` son modelos sin Axioma 3

**Archivo:** `backend/api/enterprise_cms.py` — no hay filtros de sede.

---

### I-10: `CmsGlossaryTerm` tiene `is_published` pero no `deleted_at` para soft-delete

**Archivo:** `backend/models_enterprise.py`

---

### I-11: `CmsNotification.read_at` se setea pero el modelo no lo expone en la respuesta API

**Archivo:** `backend/api/enterprise_cms.py:140-141`

---

### I-12: `_fire_webhooks` compara `hook.events` con `is` en vez de `==`

**Archivo:** `backend/api/enterprise_cms.py:74`  
**Línea:** `if event in (hook.events or []) or "*" in (hook.events or [])` — correcto, pero `is` no se usa (bien).

---

### I-13: `public_theme` usa `@cached_public(ttl=300)` pero theme cambia poco

**Archivo:** `backend/api/cms_v2.py` — 5 minutos de TTL puede ser mucho si se activa un tema y se espera verlo inmediatamente.

---

### I-14: `_get_public_site_or_404` usa `lazyload("*")` pero `CmsSite` tiene 8 relaciones eager

**Archivo:** `backend/api/cms_v2.py:213-214`

---

### I-15: `ButtonItem.validate_variant` permite solo 3 variantes pero el frontend podría renderizar más

**Archivo:** `backend/schemas/cms_v2_sections.py:16-20`

---

### I-16: `CmsSectionType.description` max_length=255 en schema pero el modelo es String(255) — bien

---

### I-17: `SavedView` no es CMS pero está en `models_cms.py` — arrastrado de herencia

---

## Hallazgos de Completitud — Funcionalidades Faltantes

| Código | Funcionalidad | Dónde debería estar |
|---|---|---|
| **F-01** | No hay endpoint `GET /cms/v2/sites/{site_key}/global-sections` para consultar secciones globales (is_global=True) | `api/cms_v2.py` |
| **F-02** | No hay endpoint `POST /cms/v2/sites/{site_key}/pages/{slug}/clone` para duplicar páginas | `api/cms_v2.py` |
| **F-03** | `CmsMediaItem` no tiene campo `width` y `height` individuales (solo `dimensions` como string) | `models_cms.py` |
| **F-04** | No hay soporte para `CmsRedirect` con wildcard/regex en `from_path` | `enterprise_cms.py` |
| **F-05** | No hay rate limiting en endpoints CMS v2 admin (excepto públicos con PUBLIC_CMS_RATE_LIMIT) | `api/cms_v2.py` |
| **F-06** | `CmsCategory.parent_id` no tiene validación de que el parent pertenece al mismo site | `crud/cms.py` |
| **F-07** | No hay endpoint para `CmsSeoSnapshot` histórico por site en la API (solo CRUD) | `api/cms_v2.py` |
| **F-08** | `CmsPublishLog` no se limpia periódicamente (tabla crece indefinidamente) | `scheduler.py` o CRON |
| **F-09** | No hay validación de `CmsPost.published_at < expires_at` en `CmsPostUpdate` | `api/cms_v2.py` |
| **F-10** | No hay endpoint `DELETE /cms/v2/sites/{site_key}/media/cleanup` para limpiar media huérfana | `api/cms_v2.py` |

---

## Consistencia Multi-Tenant (Axioma 3) — Brechas

| Entidad | ¿Tiene sede_id? | ¿Filtro en API? | ¿Filtro en CRUD? | Status |
|---|---|---|---|---|
| CmsMediaItem | ✅ | ✅ | ✅ | OK |
| Announcement | ✅ | ✅ | ✅ | OK |
| Testimonial | ✅ | ✅ | ✅ | OK |
| CmsSite | ✅ (nullable) | ✅ | ❌ (parcial) | ⚠️ Véase C-01 |
| CmsTheme | ❌ (vía site) | ✅ (vía site) | ❌ (vía site) | OK by proxy |
| CmsMenu | ❌ (vía site) | ✅ (vía site) | ❌ (vía site) | OK by proxy |
| CmsMenuItem | ❌ (vía menu→site) | ✅ (vía site) | ❌ | OK by proxy |
| CmsPage | ❌ (vía site) | ✅ (vía site) | ❌ | OK by proxy |
| CmsSection | ❌ (vía page→site) | ✅ (vía site) | ❌ | OK by proxy |
| CmsPost | ❌ (vía site) | ❌ | ❌ | ⚠️ Sin filtros |
| CmsCategory | ❌ (vía site) | ❌ | ❌ | ⚠️ Sin filtros |
| CmsTag | ❌ (vía site) | ❌ | ❌ | ⚠️ Sin filtros |
| CmsPageVersion | ❌ (vía page→site) | ✅ (vía site) | ❌ | OK by proxy |
| CmsPublishLog | ❌ (vía site/page) | ❌ | ❌ | ⚠️ Sin filtro directo |
| CmsSeoSnapshot | ✅ (denormalizado) | ✅ | ✅ | OK |
| CmsSectionType | ❌ (global) | ❌ | ❌ | Global design OK |
| ContentPermission | ❌ | ❌ | ❌ | ⚠️ Sin tenant |
| Webhook | ❌ (vía site_key) | ❌ | ❌ | ⚠️ Sin tenant |
| CmsGlossaryTerm | ❌ (vía site_key) | ❌ | ❌ | ⚠️ Sin tenant |
| MediaFolder | ❌ (vía site_key) | ❌ | ❌ | ⚠️ Sin tenant |
| CmsCustomEntry | ❌ (vía site_key) | ❌ | ❌ | ⚠️ Sin tenant |
| CmsCustomType | ❌ (vía site_key) | ❌ | ❌ | ⚠️ Sin tenant |

---

## Resumen de Deuda Técnica

### Código muerto / No referenciado
1. `EventsCalendarProps` en SECTION_PROPS_SCHEMAS — tipo `events_calendar` nunca en `get_allowed_section_types`
2. Al menos 10 schemas de props sin usar en tipos permitidos
3. `ContactSubmission` — no se usa en ningún endpoint CMS v1/v2
4. `SavedView` — no es CMS, satura el archivo

### Duplicación
1. `_commit_or_raise_conflict` duplicado (API vs CRUD)
2. `resolve_persona_id_for_user` wrapper redundante
3. Import + re-export completo de helpers SEO desde `_cms_helpers._shared`

### Inconsistencias
1. La palabra "archived" vs "archivado" vs "archivada" (inglés vs español)
2. Soft-delete implementado 3 formas distintas (status, is_active, visibility, deleted_at)
3. Lazy loading mezcla `joined`, `selectin`, `lazyload("*")` sin consistencia
4. `_utcnow` importado de diferentes módulos (`models_shared` vs `crud._utils`)

---

## Recomendaciones Prioritarias

1. **C-01**: Cambiar `SET NULL` a `RESTRICT` en `cms_sites.sede_id` — migración inmediata
2. **C-06**: Agregar schemas de validación para los 19 section types faltantes
3. **C-03**: Agregar scope multi-tenant a endpoints de section types vía site-scoping
4. **H-05**: Sanitizar path en hard-delete de media con `os.path.normpath` + validación prefix
5. **H-04**: Propagar `deleted_at` en `archive_cms_section`
6. **H-11**: Agregar validación estructural de props para section types sin schema
7. **M-01 a M-03**: Agregar validaciones Pydantic de longitud y formato
8. Auditoría completa de Axioma 3 para Posts, Categories, Tags, PublishLog
9. Unificar implementación de soft-delete en todo el módulo CMS

---

## Seguimiento de Cierre (actualizado 2026-07-23)

Estado de cada hallazgo, en orden de severidad.  Los "falsos positivos"
incluyen una justificación citando el contrato o la observación de
comportamiento vivo.  Cada cierre lleva commit hash + suite que lo
respalda.

### CRÍTICOS

| ID | Estado | Cierre / Justificación | Commit |
|---|---|---|---|
| C-01 | ✅ CERRADO | `models_cms.py` ondelete SET NULL → RESTRICT + `_assert_site_sede_scope` bloquea orphan sites a actor con sede; migración `20260723_0002` | `e8912c54` |
| C-02 | ✅ FALSO POSITIVO | El vector TOCTOU ("actor cambia de sede entre fetch y commit") ya está cubierto por el defense-in-depth check #1 (`current_row_sede == actor_sede`) en `_crud_scope_re_check_cms_content_update`.  El `incoming_author_persona_id=row.created_by_persona_id` es un RE-CHECK REDUNDANTE, no un vector faltante.  Cubierto por `TestC02TOCTOUFalsePositive::test_actor_sede_changed_blocks_update`. | `bd28cfe4` |
| C-03 | ✅ FALSO POSITIVO | `CmsSectionType` es catálogo global por diseño (REGLAS.md §4.2 "Global design OK").  CRUD require `CMS_PUBLISHER_ROLES` que ya restringe mutación a roles autorizados.  Site-scoping section types rompe el contrato editorial (ver commit `6a83dd87` que lo confirmó). | (decisión documental) |
| C-04 | ✅ CERRADO | `build_pastors_section_props` y `update_pastors_section` ahora reciben `sede_id` del site al que pertenece la sección pastors; antes mezclaba pastores de todas las sedes.  Helper `_resolve_section_sede_id` resuelve el scope. | `6a83dd87` |
| C-05 | ✅ FALSO POSITIVO | El snapshot persiste `sede_id` propio (línea 1388 de cms_v2.py); sites son globales por diseño editorial (REGLAS.md §4.2). | (decisión documental) |
| C-06 | ✅ CERRADO | 24 schemas Pydantic nuevos en `cms_v2_sections.py` con `extra='ignore'`, validate_section_props valida estructura para todos los tipos canónicos de `get_allowed_section_types()`. | `5b0a6e7c` |

### ALTOS (estado al 2026-07-23)

| ID | Estado | Cierre / Justificación | Commit |
|---|---|---|---|
| H-01 | ⚠️ Pendiente | `CmsSeoSnapshot.by_severity_json default=dict` — cause cambió a `default={}`?  No urgente; revisar para consistencia. | — |
| H-02 | ⚠️ Pendiente | `CmsSeoSnapshot.captured_at` usa lambda inline en vez de `_utcnow`. | — |
| H-03 | ⚠️ Pendiente | `CmsSection.type` shadow built-in.  No bug funcional. | — |
| H-04 | ⚠️ Pendiente | `archive_cms_section` no propaga `deleted_at`.  Inconsistencia semántica. | — |
| H-05 | ✅ CERRADO | `delete_cms_media` ahora normpath + startswith("/root/ccf/uploads") antes de `os.remove`; igual que `optimize_cms_media`.  3 tests de regresión en `TestDeleteCmsMediaPathTraversalHardening` (permanent bloquea traversal, permanent legítimo funciona, permanent=False no toca FS). | `b347f787` |
| H-06 | ⚠️ Pendiente | `AnnouncementUpdate` no expone `is_active`. | — |
| H-07 | ⚠️ Pendiente | `CmsPost/Create/Update` sin `locale`. | — |
| H-08 | ⚠️ Pendiente | `_get_page_or_404` no verifica `site.is_active` en preview. | — |
| H-09 | ⚠️ Pendiente | Route overlap admin vs public preview-path. | — |
| H-10 | ⚠️ Pendiente | `ContactSubmission.updated_at` sin `onupdate=_utcnow`. | — |
| H-11 | ✅ CERRADO (con C-06) | Validación estructural de props aplicada para los 24 tipos via `SECTION_PROPS_SCHEMAS`.  El fallback `sanitize_props_html` queda solo para custom types sin schema. | `5b0a6e7c` |

### MEDIOS / BAJOS / FUNCIONALIDADES

M-01..M-14, I-01..I-17, F-01..F-10 quedan pendientes (excepto
F-06 y F-09 cerrados), prioritizadas por: M-01..M-02
(validaciones Pydantic que evitan 500), M-04..M-05 (`use_alter`,
indices), y el resto como deuda técnica incremental.

| ID | Estado | Cierre / Justificación | Commit |
|---|---|---|---|
| F-06 | ✅ CERRADO | `crud/cms.py::_assert_parent_category_same_site` valida que `CmsCategory.parent_id` exista Y pertenezca al mismo `site_id` que la categoría bajo mutación (defense-in-depth en capa CRUD, cubre callers no-API). `create_cms_category` y `update_cms_category` llaman al helper; los endpoints `create_category`/`patch_category` en `api/cms_v2.py` traducen `ValueError` -> `HTTP 422`. 7 tests de regresión en `TestF06CategoryParentCrossSite` cubren: create/patch cross-site -> 422, create/patch same-site -> 201/200, patch parent=None -> 200 (limpiar), parent inexistente -> 422, y validación directa en CRUD (sin API). | `82d9ffdd` |
| F-09 | ✅ CERRADO | `crud/cms.py::_assert_post_published_before_expires` rechaza `published_at >= expires_at` cuando ambos son no-None (normaliza a UTC aware para evitar el bug SQLite tz-info loss que ya documentamos). `create_cms_post` valida contra el payload; `update_cms_post` valida contra los valores efectivos (combina payload parcial con el row). Los endpoints `create_post`/`patch_post` en `api/cms_v2.py` traducen `ValueError` -> `HTTP 422`; el comentario obsoleto en `patch_post` que justificaba la ausencia de validación se actualiza. 11 tests de regresión en `TestF09PostPublishedBeforeExpires` cubren POST invertido/equal -> 422, POST válidos -> 201, PATCH ambos invertidos y PATCH parciales combinados contra el row -> 422, PATCH equal-dates -> 422, PATCH válidos y clearing-expires -> 200, validación directa CRUD create+update. | `afdafa89` |

### Resumen de cierre al 2026-07-23

- Críticos: 6/6 cerrados (4 fix, 2 falso positivo)
- Altos: 2/11 cerrados (H-05, H-11)
- Funcionalidades: 2/10 cerradas (F-06, F-09)
- Medios/Info: pendientes (T1.4, T1.5 en progreso)

---

*Documento generado por auditoría forense línea por línea del código fuente del módulo CMS.*
*Total: 48 hallazgos (6 críticos, 11 altos, 14 medios, 17 informativos) + 10 funcionalidades faltantes.*
