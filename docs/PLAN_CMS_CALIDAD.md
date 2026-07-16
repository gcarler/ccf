# Plan de Calidad — Modulo de CMS CCF

> **Objetivo:** operar CMS como modulo editorial propio dentro de la arquitectura modular CCF, separando con claridad admin, preview, render público, multi-tenant y seguridad para evitar regresiones repetitivas.

**Relación con documentos previos.**

- Este es el plan operativo canónico del módulo dentro del esquema modular.
- `docs/PLAN_CMS_100.md` se conserva como plan de auditoría profunda y referencia de cierre exhaustivo; este documento define el orden operativo diario, los gates mínimos y la integración con el resto de la plataforma.

## 1. Regla de trabajo

- No mezclar en un mismo fix problemas de editor, preview, render público, SEO, uploads y multi-tenant si no comparten la misma causa raíz.
- Cada cambio debe mapearse a un ID estable de `docs/ESTADO_CMS.md`.
- Si el bug vive en `site_id`, `sede_id`, storage, auth, permisos o UI base compartida, clasificar primero el owner real antes de editar.
- Todo cambio en publicación, redirects, preview o contenido público debe dejar contrato o regresión automatizada.
- `docs/PLAN_CMS_100.md` sigue siendo la referencia de profundidad; este plan gobierna la ejecución modular repetible.

## 2. Fase 0 — Diagnostico base

**ID:** `CMS-FASE0-DIAG`

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_CMS.md
cat docs/CMS_API_CONTRACTS.md
cat docs/CMS_RBAC_MATRIX.md
cat docs/CMS_QA_CHECKLIST.md
cat docs/PLAN_CMS_100.md
grep -nE "PARCIAL-|PEND-" docs/ESTADO_CMS.md
./venv/bin/python scripts/test_cms_quality.py
```

Validación mínima bruta:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_cms_domain.py \
  tests/test_cms_sede_isolation.py \
  tests/test_cms_upload_and_image_hardening.py \
  tests/test_cms_metrics_sede_isolation.py
```

Criterio de salida:

- El primer fallo real queda clasificado como `contrato API`, `multi-tenant`, `preview/publicado`, `storage`, `SEO`, `render público` o `frontend state`.
- No se toca builder o preview antes de confirmar si la fuga está en backend o datos.

## 3. Fase 1 — Contratos backend y aislamiento

**IDs:** `DONE-GATE-CMS-001`, `DONE-RBAC-V1-HARDENING-CMS-001`, `DONE-RBAC-ENTERPRISE-CMS-001`

Orden:

1. Revalidar scope por `site_id`, `sede_id`, soft delete y status en CMS v1, v2 y enterprise.
2. Confirmar accesos por `id` que puedan saltarse aislamiento o contenido borrado.
3. Verificar uploads, media y optimización de imágenes con la allow-list real.
4. Actualizar `docs/CMS_API_CONTRACTS.md` si cambia un endpoint o payload canónico.

Criterio de salida:

- No quedan lecturas o mutaciones críticas con fuga de scope conocida.
- Las rutas CMS respetan el contrato modular y no dependen de conocimiento implícito.
- La deuda RBAC activa de Enterprise CMS queda trazada explícitamente en el backlog del módulo hasta su cierre.
- El endurecimiento RBAC de CMS v1 queda validado con pruebas focalizadas y preserva `cms:read` para lecturas administrativas.

## 4. Fase 2 — Admin, builder y workflow editorial

**IDs:** `DONE-BUILDER-CMS-001`, `DONE-PREVIEW-PUBLIC-CMS-001`, `DONE-DASHBOARD-CMS-001`

Orden:

1. Verificar dashboard, listado de páginas, builder, versiones, media, temas, menús y sites.
2. Confirmar que la UI no permita estados que el backend no sostenga.
3. Separar validación de preview, workflow y publicación del resto del editor.
4. Documentar cualquier drift entre admin y backend antes de tocar la vista.

Criterio de salida:

- El panel CMS refleja el contrato real del backend.
- Builder y workflow dejan de depender de tolerancias silenciosas.

## 5. Fase 3 — Preview, publicado y render público

**IDs:** `DONE-PREVIEW-PUBLIC-CMS-001`, `DONE-VISUAL-CMS-001`

Orden:

1. Comparar preview con la versión publicada.
2. Comparar render público con la última versión vigente.
3. Revisar slugs, redirects, canonical, sitemap, SEO y fallbacks públicos.
4. Añadir regresión si se corrige contenido “fantasma”, ruta muerta o fallback incorrecto.

Criterio de salida:

- Preview, publicado y público coinciden en los flujos auditados.
- No hay rutas canónicas duplicadas o contenido expuesto por accidente.

## 6. Fase 4 — Smoke modular y profundidad progresiva

**IDs:** `DONE-EXPAND-SMOKE-CMS-001`, `DONE-GATE-CMS-001`, `DONE-CMS-E2E-AUTH-GATE-001`

Comandos actuales:

```bash
cd /root/ccf
./venv/bin/python scripts/test_cms_quality.py

cd /root/ccf/frontend
npm run test:e2e:cms
npm run test:e2e:cms:deep
```

Cobertura complementaria existente:

```bash
cd /root/ccf/frontend
npx vitest run tests/cms-components.test.ts tests/cms-public-fetch.test.ts
npm run test:e2e:cms:public
```

Regla:

- El smoke modular protege tanto la superficie admin como el contrato público; cuando un cambio toque preview/publicado, el checklist visual y el contrato público suben de prioridad.
- La cobertura profunda actual de CMS vive en `frontend/tests/e2e/cms/pages-preview.spec.ts` y debe reutilizar el runner administrado compartido.
- `scripts/test_cms_quality.py` ya es el gate canónico completo: backend CMS, Vitest, smoke E2E autenticado y contrato público.
- El smoke autenticado de CMS requiere `E2E_EMAIL`, `E2E_PASSWORD` y `E2E_API_URL` o `API_BASE_URL` absolutos; si el usuario no existe localmente, sembrarlo con `npm run test:e2e:seed-user` antes del gate.
- Si `npm run test:e2e:cms` cae en `Acceso Restringido` pese a que `/v3/auth/me` devuelve `cms:*`, tratarlo como drift de bootstrap de sesión/AuthContext/ProtectedRoute y no como fallo RBAC backend de CMS.

Criterio de salida:

- Existe una ruta canónica mínima de QA para CMS y una cobertura profunda inicial para `pages` + `preview`.
- El módulo deja de depender de memoria informal para saber qué validar.

## 7. Fase 5 — QA final y release

**ID:** `CMS-FASE5-QA`

Comandos mínimos:

```bash
cd /root/ccf
./venv/bin/python scripts/test_cms_quality.py
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_cms_domain.py \
  tests/test_cms_sede_isolation.py \
  tests/test_cms_upload_and_image_hardening.py \
  tests/test_cms_metrics_sede_isolation.py
```

Si se toca preview, render público o enterprise:

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_enterprise_cms.py \
  tests/test_cms_v2_coverage.py \
  tests/test_cms_v2_deep_coverage.py \
  tests/test_cms_schedule.py \
  tests/test_cms_seo_audit.py
```

Criterio de salida:

- `docs/ESTADO_CMS.md` se actualiza si cambia backlog o estado.
- `docs/CMS_API_CONTRACTS.md` y `docs/CMS_QA_CHECKLIST.md` se sincronizan si cambia el flujo validado.
- Ningún fix de CMS se aprueba si resuelve UI pero deja vivo el problema de aislamiento o publicación.

## 8. Fase 6 — Ruta de cierre a 100%

**ID:** `CMS-FASE6-CIERRE100`

Estado de cierre:

1. El smoke autenticado de CMS entra con sesión real y no cae en `Acceso Restringido`.
2. Enterprise CMS expresa `cms:read` y `cms:manage` en el borde del router.
3. `scripts/test_cms_quality.py` corre backend, unit, smoke E2E autenticado y contrato público.
4. La validación preview/publicado quedó cubierta por `pages-preview.spec.ts` y el contrato público de Playwright.
5. Builder, dashboard y preview dejaron de depender de tolerancias silenciosas y quedaron cubiertos por los gates reproducibles.

Criterio de salida:

- No quedan IDs abiertos para CMS en `docs/ESTADO_CMS.md`.
- El gate canónico y el gate exhaustivo del módulo pasan sin skips silenciosos.
- `docs/ESTADO_CMS.md`, `docs/CMS_API_CONTRACTS.md` y `docs/CMS_QA_CHECKLIST.md` quedan sincronizados con el estado final.
