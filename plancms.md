# Plan de Trabajo — Mejora Integral del Módulo CMS

**Proyecto:** CCF (Centro Cristiano Faro)  
**Módulo:** CMS v2  
**Fecha:** 2026-07-22  
**Estado:** En producción  

---

## 1. Contexto

El módulo CMS v2 de CCF gestiona sites, páginas, secciones, menús, temas, posts, categorías, tags y medios. La auditoría de calidad más reciente identificó puntos fuertes (tests backend estables, contrato API/TS sólido) pero también riesgos en seguridad, rendimiento, deuda técnica frontend y a11y/SEO.

Este plan busca **atacar todos los frentes** de forma ordenada, priorizando la estabilidad en producción sin bloquear el desarrollo de nuevas funciones.

---

## 2. Objetivos Generales

1. **Eliminar los riesgos de seguridad críticos y altos** (tenant isolation, XSS, IDOR).
2. **Mejorar el rendimiento** de endpoints públicos y del builder.
3. **Reducir la deuda técnica** del frontend y backend.
4. **Alinear contratos** frontend/backend con tipos estrictos.
5. **Cerrar el gap de tests E2E** para el CMS.
6. **Mejorar accesibilidad y SEO** del sitio público.

---

## 3. Fases de Trabajo

### Fase 0 — Preparación y línea base (1-2 días)

- [ ] Tomar snapshot de cobertura de tests actual.
- [ ] Configurar variables E2E (`E2E_EMAIL`, `E2E_PASSWORD`, `E2E_API_URL`).
- [ ] Documentar endpoints críticos y flujos de datos.
- [ ] Crear branch `feat/cms-quality-improvements`.

**Entregable:** Branch base configurada y variables E2E listas.

---

### Fase 1 — Seguridad (5-7 días)

#### 1.1 Tenant isolation robusta
- [ ] Revisar `_assert_site_sede_scope` en `backend/api/cms_v2.py`.
- [ ] Agregar doble validación: si `actor_sede is None`, verificar rol explícito global/superadmin.
- [ ] Auditar `patch_menu_item`, `delete_menu_item`, `patch_section`, `delete_section` para confirmar scope en el WHERE del CRUD.
- [ ] Escribir tests de regresión para IDOR cross-sede.

#### 1.2 Sanitización y validación de `props_json`
- [ ] Implementar validador de esquema por tipo de sección en backend.
- [ ] Sanitizar HTML en `rich_text`, `collapsible`, `embed` antes de guardar.
- [ ] Auditar `sanitizeCmsHtml` en frontend y fortalecer whitelist.

#### 1.3 Race conditions en creación
- [ ] Envolver `create_section_type`, `create_site`, `create_menu` en `try/except` ante `IntegrityError`.
- [ ] Retornar `409 Conflict` controlado en lugar de `500`.

**Entregable:** Tests de seguridad pasan, sin regresiones.

---

### Fase 2 — Estabilidad Frontend (4-6 días)

#### 2.1 Resolver warnings `react-hooks/exhaustive-deps`
- [ ] Listar los 17 archivos afectados.
- [ ] Refactorizar a `useCallback`/`useMemo` con dependencias correctas.
- [ ] Priorizar `BuilderSidebar.tsx`, `usePageBuilder.ts` y páginas del CMS.

#### 2.2 Tipado estricto de secciones
- [ ] Definir tipos discriminados en `frontend/src/types/cms-v2.ts`.
- [ ] Refactorizar `PublicSectionRenderer.tsx` para evitar `Record<string, unknown>`.
- [ ] Validar con `zod` o similar en el cliente.

**Entregable:** `npm run lint -- --max-warnings=0` pasa; typecheck pasa.

---

### Fase 3 — Rendimiento Backend (5-7 días)

#### 3.1 Eliminar N+1 en endpoints públicos
- [ ] Auditar `public_page`, `public_post`, `public_menu`, `public_theme`.
- [ ] Reemplazar `lazyload("*")` por `selectinload` explícito donde se necesiten relaciones.
- [ ] Medir con SQL logging antes/después.

#### 3.2 Cache centralizado
- [ ] Evaluar si conviene Redis para `_system_var_cache`.
- [ ] Implementar TTL e invalidación centralizada.
- [ ] Alternativa low-effort: reducir TTL y agregar header de invalidación.

#### 3.3 Paginación por cursor
- [ ] Agregar paginación cursor-based a `publish_logs`, `page_views` y media library.

**Entregable:** Métricas de query reducidas; tests de carga básicos.

---

### Fase 4 — Refactor y Calidad de Código Backend (6-8 días)

#### 4.1 Dividir `backend/api/cms_v2.py`
- [ ] `admin/pages.py` — CRUD de páginas y secciones.
- [ ] `admin/menus.py`, `admin/themes.py`, `admin/sites.py`.
- [ ] `public/pages.py`, `public/menus.py`, `public/posts.py`.
- [ ] `seo.py`, `workflow.py`, `section_types.py`.

#### 4.2 Centralizar workflow de páginas
- [ ] Crear servicio `PageWorkflowService`.
- [ ] Eliminar mutación implícita de `status` en `patch_page`.

#### 4.3 Mejorar manejo de errores
- [ ] Definir excepciones de dominio propias (`CmsNotFound`, `CmsPermissionDenied`).
- [ ] Mapear a códigos HTTP consistentes.

**Entregable:** `backend/api/cms_v2.py` < 800 líneas; tests backend pasan.

---

### Fase 5 — Tests E2E y Cobertura (5-7 días)

- [ ] Configurar Playwright para CMS con variables E2E.
- [ ] Crear flujos E2E críticos:
  - Login → crear página → agregar sección → publicar → ver en sitio público.
  - Editar menú y ver cambios en navbar.
  - Subir imagen y verificar alt text.
  - Probar aislamiento cross-sede.
- [ ] Integrar en CI (`scripts/test_cms_quality.py`).

**Entregable:** Suite E2E del CMS corriendo en CI.

---

### Fase 6 — a11y y SEO (3-5 días)

- [ ] Forzar `alt` explícito en todas las imágenes del CMS.
- [ ] Agregar `aria-hidden` en imágenes decorativas.
- [ ] Alinear `canonical_url` y breadcrumbs con configuración de Next.js.
- [ ] Validar contraste de colores y navegación por teclado en `PublicSectionRenderer`.
- [ ] Generar sitemap dinámico con páginas publicadas.

**Entregable:** Lighthouse a11y/SEO ≥ 90 en páginas CMS principales.

---

### Fase 7 — Documentación y Cierre (2-3 días)

- [ ] Actualizar `docs/` con nuevo diagrama de arquitectura del CMS.
- [ ] Documentar contratos API con ejemplos.
- [ ] Escribir runbook para deploy y rollback.
- [ ] Hacer merge a `main` y monitorear métricas en producción.

**Entregable:** PR final mergeado, documentación actualizada.

---

## 4. Priorización de Items

| Prioridad | Item | Fase | Razón |
|-----------|------|------|-------|
| 🔴 Crítica | Tenant isolation doble check | 1 | Riesgo de data leak en producción |
| 🔴 Crítica | Sanitización `props_json` | 1 | Riesgo de XSS en sitio público |
| 🔴 Crítica | Resolver `exhaustive-deps` | 2 | Pérdida de datos en builder |
| 🟠 Alta | N+1 queries endpoints públicos | 3 | Escalabilidad |
| 🟠 Alta | Tests E2E del CMS | 5 | Confianza en releases |
| 🟡 Media | Refactor `cms_v2.py` | 4 | Mantenibilidad |
| 🟡 Media | Tipos discriminados de secciones | 2 | Robustez del frontend |
| 🟢 Baja | Cache centralizado | 3 | Optimización avanzada |
| 🟢 Baja | Mejoras a11y/SEO | 6 | Calidad de producto |

---

## 5. Criterios de Aceptación Generales

- [ ] Todos los tests backend existentes siguen pasando.
- [ ] `npm run lint -- --max-warnings=0` y `npx tsc --noEmit` pasan.
- [ ] Nuevos tests de seguridad cubren IDOR, XSS y race conditions.
- [ ] Tests E2E del CMS pasan en CI.
- [ ] No regresiones en métricas de Lighthouse.
- [ ] Documentación actualizada.

---

## 6. Validación Continua

| Checkpoint | Comando / Acción | Frecuencia |
|------------|------------------|------------|
| Tests backend | `python scripts/test_cms_quality.py` | Cada PR |
| Typecheck frontend | `cd frontend && npx tsc --noEmit` | Cada PR |
| Lint frontend | `cd frontend && npm run lint -- --max-warnings=0` | Cada PR |
| Tests E2E | `npm run test:e2e:cms` | Cada PR + nightly |
| Lighthouse | `npm run lighthouse:ci` | Nightly |

---

## 7. Riesgos y Mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Cambios en tenant isolation rompen flujo de superadmin | Alto | Tests exhaustivos de roles antes de mergear |
| Refactor de `cms_v2.py` introduce regresiones | Alto | Hacerlo por etapas; mantener tests existentes |
| Sanitización HTML rompe contenido existente | Medio | Validar contra snapshot de datos reales en staging |
| Tests E2E son flaky | Medio | Aislar estado, limpiar DB entre tests |
| Cambios de tipos frontend rompen build | Medio | Typecheck en CI antes de mergear |

---

## 8. Estimación Total

| Fase | Días estimados |
|------|----------------|
| Fase 0 — Preparación | 1-2 |
| Fase 1 — Seguridad | 5-7 |
| Fase 2 — Estabilidad Frontend | 4-6 |
| Fase 3 — Rendimiento Backend | 5-7 |
| Fase 4 — Refactor Backend | 6-8 |
| Fase 5 — Tests E2E | 5-7 |
| Fase 6 — a11y / SEO | 3-5 |
| Fase 7 — Documentación y Cierre | 2-3 |
| **Total** | **31-46 días** |

> Nota: la estimación es orientativa. Se recomienda trabajar en iteraciones de 1 semana y revisar prioridades al final de cada sprint.

---

## 9. Próximos Pasos Sugeridos

1. **Aprobar y afinar prioridades** de este plan.
2. **Crear sub-tareas en el issue tracker** por fase.
3. **Comenzar por la Fase 1 (Seguridad)**, ya que reduce riesgo operativo inmediato.

---

*Documento generado a partir de la auditoría de calidad del módulo CMS v2 de CCF.*
