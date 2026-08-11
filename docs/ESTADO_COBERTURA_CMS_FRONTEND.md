# Cobertura de tests del frontend CMS

> ⚠️ **Nota:** este reporte se genera automáticamente a partir de `frontend/coverage-cms/coverage-summary.json`.
> Regenerarlo con: `cd /root/ccf/frontend && npm run test:cms:coverage`

**Fecha:** 2026-08-11 (medición local)
**Configuración:** `frontend/vitest.cms.config.ts`
**Comando para reproducir:**

```bash
cd /root/ccf/frontend
npm run test:cms:coverage
```

## Resumen global

| Métrica     | Porcentaje |
|-------------|------------|
| Statements  | 59.98%     |
| Branches    | 67.89%     |
| Functions   | 38.94%     |
| Lines       | 59.98%     |

> **Nota metodológica:** El reporte no aplica umbrales (thresholds) porque es informativo. La cobertura subió de ~19% → ~49% → **~60%** en statements desde el reporte de 2026-07-29 gracias a los tests agregados para forms, las páginas admin (glossary, newsletter, sessions, broken-links, search-admin, ab-testing, media-folders, popups, comments, sites, categories, tags, pages, posts y themes), el builder y las librerías `lib/cms`. La medición del 2026-08-11 suma **55 tests unitarios nuevos** en las 6 páginas administrativas que estaban al 0% (sites, categories, tags, pages, posts y themes).

## Cobertura por área

| Área                              | Stmts  | Branch | Funcs  | Lines  | Estado        |
|-----------------------------------|--------|--------|--------|--------|---------------|
| `components/cms/forms`            | 82.2%  | 59.5%  | 41.9%  | 82.2%  | ✅ Casi cubierto |
| `components/cms/builder`          | 73.1%  | 68.7%  | 40.4%  | 73.1%  | ✅ Casi cubierto |
| `components/cms/themes`           | 99.0%  | 100.0% | 60.0%  | 99.0%  | ✅ Casi cubierto |
| `components/cms` (resto)          | 87.4%  | 72.0%  | 28.8%  | 87.4%  | ✅ Casi cubierto |
| `lib/cms`                         | 72.3%  | 77.9%  | 49.1%  | 72.3%  | ✅ Casi cubierto |
| `app/plataforma/cms/builder`      | 73.5%  | 88.2%  | 43.9%  | 73.5%  | ✅ Casi cubierto |
| `app/plataforma/cms` (resto)      | 46.7%  | 62.5%  | 37.8%  | 46.7%  | ⚠️ Parcial    |

## Páginas administrativas cubiertas (tests unitarios)

Tests agregados el 2026-08-11 (55 tests en total) para las páginas que estaban al 0%:

| Página                                  | Stmts  | Funcs | Tests |
|-----------------------------------------|--------|-------|-------|
| `sites/page.tsx`                        | 100.0% | 100%  | 7     |
| `categories/page.tsx`                   | 92.5%  | 56.5% | 8     |
| `tags/page.tsx`                         | 93.7%  | 61.9% | 8     |
| `pages/page.tsx`                        | 68.5%  | 43.5% | 12    |
| `posts/page.tsx`                        | 78.0%  | 34.7% | 9     |
| `themes/page.tsx`                       | 90.7%  | 52.9% | 11    |

Flujos cubiertos: render y estados vacíos, búsqueda/filtros, creación vía quick-add con slug derivado, archivar/restaurar con confirmación de modal, edición desde panel lateral, activación de themes, import/export/copy de JSON, publicación de posts desde el editor a pantalla completa, archivo en bloque desde la vista table, navegación a detalle/builder, vista previa y manejo de errores (401).

## Archivos con cobertura 100%

- `app/plataforma/cms/broken-links/page.tsx`
- `app/plataforma/cms/builder-puck/page.tsx`
- `app/plataforma/cms/glossary/page.tsx`
- `app/plataforma/cms/sites/page.tsx`
- `components/cms/builder/BuilderSidebar.tsx`
- `components/cms/builder/MediaPicker.tsx`
- `components/cms/builder/constants.ts`
- `components/cms/themes/ThemePreview.tsx`
- `lib/cms/blocks.ts`
- `lib/cms/media.ts`
- `lib/cms/pageBlocks.ts`
- `lib/cms/permissions.ts`
- `lib/cms/preview-sync.ts`

## Archivos con 0% de cobertura (prioritarios)

> Estas páginas no tienen tests unitarios todavía; los flujos críticos están cubiertos por las suites E2E (`smoke`, `pages-preview`, `builder-flow`, `media-management`, contrato público) y por los tests de integración del backend.

### Páginas administrativas (`app/plataforma/cms`)
- `layout.tsx`
- `announcements/new/page.tsx`
- `audit/page.tsx`
- `custom-types/page.tsx`
- `media/page.tsx`, `media/[id]/page.tsx`
- `notifications/page.tsx`
- `pages/[slug]/page.tsx`, `pages/[slug]/versions/*`
- `pastoral-team/page.tsx`
- `preview/page.tsx`
- `readiness/page.tsx`
- `resources/page.tsx`
- `section-types/page.tsx`
- `seo-audit/page.tsx`
- `testimonials/[slug]/page.tsx`
- `ui-kit/page.tsx`

### Componentes (`components/cms`)
- Ninguno: todos los componentes del módulo CMS tienen cobertura > 0%.

## Áreas con cobertura parcial y próximos pasos recomendados

### 1. Builder (`components/cms/builder`)
Cobertura general buena (~73% stmts) pero con oportunidades:

- **BuilderSectionInspector.tsx**: es el archivo más crítico dentro del builder; seguir cubriendo edición de props por tipo de sección y manipulación de arrays.
- **BuilderCanvas.tsx**: cubrir drag-and-drop, reordenamiento de secciones y toggles de modo esquema/render y dispositivo.
- **BuilderRightPanel.tsx**: cubrir flujo de analytics con `getPageAnalytics` y preview links (`window.open`).

### 2. Librerías (`lib/cms`) — 72.3% stmts
- **v2.ts** (44.08% stmts): los wrappers de API siguen siendo el archivo con más funciones sin cubrir dentro de `lib/cms`; los mocks por página cubren los endpoints usados, pero quedan muchos wrappers sin ejercitar.
- **versionDiff.ts** (92.81% stmts): casi cubierto; faltan ramas menores.

### 3. Páginas administrativas (`app/plataforma/cms`) — 46.7% stmts
- Las 6 páginas principales (`sites`, `categories`, `tags`, `pages`, `posts`, `themes`) ya tienen tests unitarios (68–100% stmts).
- Quedan al 0%: `pages/[slug]/*` (detalle/versiones), `pastoral-team`, `media`, `resources`, `section-types`, `seo-audit`, `custom-types`, `audit`, `readiness`, `notifications`, `preview`, `ui-kit`, `testimonials/[slug]`, `announcements/new` y `layout.tsx`. Próximo paso natural: `pastoral-team` (798 stmts) y `pages/[slug]` (detalle + versions, ~1394 stmts).

## Recomendaciones

1. **No alterar `vitest.config.ts`:** la configuración principal mantiene sus umbrales para el design system. El reporte de CMS usa `vitest.cms.config.ts` y no afecta el gate global.
2. **Priorizar `pages/[slug]/*` y `pastoral-team`:** son las páginas administrativas más grandes que quedan sin cobertura unitaria.
3. **Mantener el patrón de mocks de las 6 páginas nuevas:** mock de `@/context/AuthContext` + `@/lib/cms/v2` (con `importOriginal` para helpers reales) + `sonner`, y stubs para `SidePanel`/`ViewSwitcher`/componentes pesados.
4. **La cobertura de `lib/cms` ya no es un bloqueador:** con 72% de statements y `permissions.ts`/`sanitize.ts`/`media.ts`/`blocks.ts` al 100%, el área de utilidades está en buen estado.

## Cómo regenerar este reporte

```bash
cd /root/ccf/frontend
npm run test:cms:coverage
```

El reporte HTML detallado se genera en `frontend/coverage-cms/` y el resumen JSON en `frontend/coverage-cms/coverage-summary.json`.

> ⚠️ **Nota (2026-08-11):** mientras el workstream de projects (multi-tenant) esté sin commitear, `npm run test:cms:coverage` falla con 6 tests preexistentes de `src/app/plataforma/projects/**` (los componentes `ProjectsListView.tsx`/`ProjectsTableView.tsx` usan `useRouter` sin mock en sus tests) y **vitest no escribe `coverage-summary.json` cuando el run falla**. Para regenerar el reporte en ese estado, excluir los tests de projects (no aportan al alcance de cobertura CMS):

```bash
cd /root/ccf/frontend
npx vitest run -c vitest.cms.config.ts --coverage --exclude 'src/app/plataforma/projects/**/*.test.{ts,tsx}'
```

La medición del 2026-08-11 se generó con este comando (los números solo incluyen el alcance `src/components/cms`, `src/app/plataforma/cms` y `src/lib/cms`).
