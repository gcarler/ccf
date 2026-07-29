# Cobertura de tests del frontend CMS

> ⚠️ **Nota:** este reporte se genera automáticamente. No edites los valores a mano.
> Regenerarlo con: `cd /root/ccf/frontend && npm run test:cms:coverage`

**Fecha:** 2026-07-29 17:52:34 UTC  
**Configuración:** `frontend/vitest.cms.config.ts`  
**Comando para reproducir:**

```bash
cd /root/ccf/frontend
npm run test:cms:coverage
```

## Resumen global

| Métrica     | Porcentaje |
|-------------|------------|
| Statements  | 17.93%     |
| Branches    | 63.44%     |
| Functions   | 25.89%     |
| Lines       | 17.93%     |

> **Nota metodológica:** El reporte no aplica umbrales (thresholds) porque es informativo. La cobertura baja se debe a que gran parte de las páginas administrativas del CMS aún no tienen tests unitarios. El área del builder sí está parcialmente cubierta gracias a los tests recientes.

## Cobertura por área

| Área                              | Stmts | Branch | Funcs | Lines | Estado        |
|-----------------------------------|-------|--------|-------|-------|---------------|
| `app/plataforma/cms/builder`      | 100%  | 82.35% | 100%  | 100%  | ✅ Cubierto   |
| `components/cms/builder`          | 64.08%| 63.15% | 24.47%| 64.08%| ⚠️ Parcial    |
| `lib/cms`                         | 45.26%| 72.39% | 37.5% | 45.26%| ⚠️ Parcial    |
| `app/plataforma/cms/*` (resto)    | 0%    | 0%     | 0%    | 0%    | ❌ Sin tests  |
| `components/cms` (resto)           | 0%    | 0%     | 0%    | 0%    | ❌ Sin tests  |

## Archivos con 0% de cobertura (prioritarios)

### Páginas administrativas (`app/plataforma/cms`)
- `layout.tsx` (1-19)
- `page.tsx` (1-764)
- `audit/page.tsx`
- `branding/page.tsx` (parcial: 66.39%)
- `broken-links/page.tsx`
- `categories/page.tsx`
- `custom-types/page.tsx`
- `glossary/page.tsx`
- `media/page.tsx`, `media-folders/page.tsx`, `media/[id]/page.tsx`
- `menus/page.tsx`
- `notifications/page.tsx`
- `pages/page.tsx`, `pages/[slug]/page.tsx`, `pages/[slug]/versions/*`
- `pastoral-team/page.tsx`
- `posts/page.tsx`
- `preview/page.tsx`
- `readiness/page.tsx`
- `redirects/page.tsx`
- `resources/page.tsx`
- `search-admin/page.tsx`
- `section-types/page.tsx`
- `seo-audit/page.tsx`
- `sessions/page.tsx`
- `sites/page.tsx`
- `tags/page.tsx`
- `testimonials/page.tsx`, `testimonials/[id]/page.tsx`
- `themes/page.tsx`
- `ui-kit/page.tsx`
- `webhooks/page.tsx`

### Componentes y librerías (`components/cms` y `lib/cms`)
- `components/cms/CmsModuleNav.tsx`
- `components/cms/themes/ThemePreview.tsx`
- `components/cms/themes/themeTokens.ts`
- `lib/cms/blocks.ts`
- `lib/cms/preview-sync.ts`
- `lib/cms/sanitize.ts`
- `lib/cms/testimonialMedia.ts`
- `lib/cms/v8-diff.ts`

## Áreas con cobertura parcial y próximos pasos recomendados

### 1. Builder (`components/cms/builder`)
Cobertura general buena pero con oportunidades:

- **BuilderCanvas.tsx** (89.15% stmts, 50% funcs)
  - Cubrir drag-and-drop y reordenamiento de secciones.
  - Cubrir toggles de modo esquema/render y dispositivo.
- **BuilderRightPanel.tsx** (93.93% stmts, 52.5% funcs)
  - Cubrir flujo de analytics con `getPageAnalytics`.
  - Cubrir preview links (`window.open`).
- **BuilderSectionInspector.tsx** (29.63% stmts, 6.21% funcs)
  - Es el archivo más crítico sin cobertura dentro del builder.
  - Cubrir edición de props por tipo de sección y manipulación de arrays.
- **SectionPreview.tsx** (70.83% stmts)
  - Cubrir variantes restantes y error boundary.

### 2. Librerías (`lib/cms`)
- **v2.ts** (29.41% funcs)
  - Múltiples wrappers de API no testeados.
  - Priorizar los métodos usados por el builder y las páginas administrativas.
- **permissions.ts** (76.47% stmts)
  - Completar casos de roles intermedios.
- **versionDiff.ts** (92.81% stmts)
  - Ya casi cubierto; faltan algunas ramas.

## Recomendaciones

1. **No alterar `vitest.config.ts`:** la configuración principal mantiene sus umbrales para el design system. El reporte de CMS usa `vitest.cms.config.ts` y no afecta el gate global.
2. **Priorizar el builder:** mantener la tendencia actual de tests en el builder antes de saltar a las páginas administrativas más aisladas.
3. **Crear tests para `lib/cms/v2.ts`:** encapsular las llamadas a API con mocks de `apiFetch` aumentará la cobertura funcional de forma significativa.
4. **Dado el tamaño del módulo administrativo, considerar tests de integración o E2E para flujos críticos** en lugar de tests unitarios para cada página.

## Cómo regenerar este reporte

```bash
cd /root/ccf/frontend
npm run test:cms:coverage
```

El reporte HTML detallado se genera en `frontend/coverage-cms/`.
