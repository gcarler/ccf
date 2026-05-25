# CMS Enterprise Roadmap — Plan Completo de Desarrollo

**Fecha:** 2026-05-25  
**Objetivo:** Llevar el CMS v2 de nivel "pro" a "enterprise-grade"  
**Autonomía:** Total — pruebas, calidad, sin atajos  
**Página de pruebas:** `/test` (pública, gestionada desde el CMS)

---

## Fase 1 — Document Upload Real (3.5h)
**Objetivo:** La sección `document_upload` sube archivos REALES a SeaweedFS

- [ ] 1.1 Endpoint `POST /api/public/documents` en backend
- [ ] 1.2 Upload a SeaweedFS con validación (tipo, tamaño)
- [ ] 1.3 Registrar en DB (`cms_media_items` o tabla dedicada)
- [ ] 1.4 Vincular sección frontend al endpoint real
- [ ] 1.5 Mostrar progreso de subida
- [ ] 1.6 Lista de documentos subidos con descarga/eliminar
- [ ] 1.7 Test: subir PDF, imagen, doc → verificar en SeaweedFS

## Fase 2 — Schema Validation por Tipo (4h)
**Objetivo:** Validar props_json contra esquemas Pydantic por tipo de sección

- [ ] 2.1 Crear schemas Pydantic para cada tipo de sección (30 tipos)
- [ ] 2.2 Validación en `create_cms_section` y `update_cms_section`
- [ ] 2.3 Mensajes de error claros en builder UI
- [ ] 2.4 Tipado TypeScript para props de cada sección
- [ ] 2.5 Test: intentar crear sección con props inválidos → debe rechazar
- [ ] 2.6 Test: crear sección con props válidos → debe aceptar

## Fase 3 — Reusable/Global Blocks (4.5h)
**Objetivo:** Bloques reutilizables que se pueden insertar en múltiples páginas

- [ ] 3.1 Modelo `cms_global_blocks` (id, key, title, type, props_json)
- [ ] 3.2 Migración Alembic
- [ ] 3.3 CRUD API para global blocks
- [ ] 3.4 UI en builder: panel "Bloques Globales"
- [ ] 3.5 Insertar bloque global en una página (referencia, no copia)
- [ ] 3.6 Renderer: resolver bloques globales al renderizar
- [ ] 3.7 Editar bloque global → se actualiza en TODAS las páginas
- [ ] 3.8 Test: crear bloque → insertar en 2 páginas → editar → verificar ambas

## Fase 4 — Scheduled Publishing (3.5h)
**Objetivo:** Programar publicación para fecha/hora específica

- [ ] 4.1 Campo `scheduled_at` en `cms_pages` (DateTime, nullable)
- [ ] 4.2 Migración Alembic
- [ ] 4.3 UI en builder: "Programar publicación" con datetime picker
- [ ] 4.4 Scheduler que verifica páginas pendientes cada minuto
- [ ] 4.5 Auto-publish cuando llega `scheduled_at`
- [ ] 4.6 Cancelar publicación programada
- [ ] 4.7 Test: programar → esperar → verificar que se publica sola

## Fase 5 — Preview Mejorada / Casi-WYSIWYG (6h)
**Objetivo:** Preview en tiempo real dentro del builder

- [ ] 5.1 Preview en iframe dentro del builder (split view)
- [ ] 5.2 Endpoint `/cms/v2/preview/{page_id}` (auth required)
- [ ] 5.3 Live update: cambios en props se reflejan en preview
- [ ] 5.4 Toggle: editor / preview / split
- [ ] 5.5 Preview mobile / tablet / desktop
- [ ] 5.6 Test: editar texto → ver cambio en preview en <1s

## Fase 6 — Analytics Integrado (6h)
**Objetivo:** Dashboard de visitas y métricas por página

- [ ] 6.1 Modelo `cms_page_views` (page_id, ip, user_agent, referrer, created_at)
- [ ] 6.2 Migración Alembic
- [ ] 6.3 Tracking endpoint `POST /cms/v2/track/{page_key}` (no auth)
- [ ] 6.4 Insertar tracking en páginas públicas (script o API call)
- [ ] 6.5 Dashboard analytics en builder: visitas, tiempo, top páginas
- [ ] 6.6 Gráficas: visitas por día, por hora, por dispositivo
- [ ] 6.7 Índice en `cms_page_views(created_at, page_id)`
- [ ] 6.8 Test: visitar página → verificar conteo en dashboard

## Fase 7 — Image Optimization (5h)
**Objetivo:** Resize automático, thumbnails, lazy loading

- [ ] 7.1 Endpoint de resize: `GET /api/cms/images/{id}/{width}x{height}`
- [ ] 7.2 Usar Pillow para resize/crop
- [ ] 7.3 Cache de imágenes redimensionadas en SeaweedFS
- [ ] 7.4 Generar thumbnails al subir imagen
- [ ] 7.5 `next/image` en frontend con src optimizado
- [ ] 7.6 Lazy loading en todas las imágenes del renderer
- [ ] 7.7 Test: subir imagen 5MB → verificar thumbnail <100KB

## Fase 8 — Multi-language / i18n (5.5h)
**Objetivo:** Páginas en múltiples idiomas con fallback

- [ ] 8.1 Campo `locale` en `cms_pages` y `cms_sections`
- [ ] 8.2 Migración Alembic
- [ ] 8.3 Configurar Next.js i18n (es, en, pt)
- [ ] 8.4 Selector de idioma en builder
- [ ] 8.5 Duplicar página para otro idioma
- [ ] 8.6 Fallback: si no hay traducción, mostrar idioma default
- [ ] 8.7 Rutas: `/es/nosotros`, `/en/about`, `/pt/sobre`
- [ ] 8.8 Test: crear página ES → duplicar EN → verificar ambas rutas

---

## Página de Pruebas: `/test`

**Propósito:** Página pública donde se insertan TODOS los tipos de sección para validar visual y funcionalmente.

**Contenido:** Una sección de cada tipo (30 + 11 nuevas = 41 secciones), cada una con datos de prueba.

**Se genera automáticamente** vía script que:
1. Crea página "CMS Test" en el CMS v2
2. Agrega una sección de cada tipo con datos de prueba
3. Publica la página
4. URL: `/test`

---

## Criterios de Aceptación por Fase

Cada fase DEBE cumplir:
- ✅ Build frontend OK
- ✅ Backend health OK
- ✅ Tests smoke passing
- ✅ Pre-push validation 7/7
- ✅ Push a origin/main
- ✅ Verificación manual en `/test`

---

## Orden de Ejecución

1. → **Script de página /test** (se hace primero para tener dónde probar)
2. → **Fase 1** (Document Upload Real) — crítico, roto ahora
3. → **Fase 2** (Schema Validation) — evita corrupción de datos
4. → **Fase 3** (Reusable Blocks) — mejora productividad
5. → **Fase 4** (Scheduled Publishing) — feature enterprise
6. → **Fase 5** (Preview Mejorada) — mejora UX del editor
7. → **Fase 6** (Analytics) — métricas de impacto
8. → **Fase 7** (Image Optimization) — performance
9. → **Fase 8** (Multi-language) — escalabilidad

**Total estimado: ~38 horas**
