# QA Checklist — CMS CCF

> **Objetivo:** validar CMS como módulo aislado antes de cerrar una tarea, commit o despliegue.

## 1. Preflight

```bash
cd /root/ccf
git status --short
python3 --version && node --version
grep -nE "PARCIAL-|PEND-" docs/ESTADO_CMS.md
```

Confirmar:

- el problema es admin, preview o público
- si toca uploads, scope o SEO, está identificado
- la matriz RBAC consultada en `docs/CMS_RBAC_MATRIX.md`

## 2. Smoke canónico

```bash
cd /root/ccf
./venv/bin/python scripts/test_cms_quality.py
```

Ese runner ya incluye backend, Vitest, smoke E2E autenticado y contrato público.

## 3. Smoke mínimo bruto

```bash
cd /root/ccf
./venv/bin/python -m pytest -q -o addopts='' \
  tests/test_cms_domain.py \
  tests/test_cms_sede_isolation.py \
  tests/test_cms_upload_and_image_hardening.py \
  tests/test_cms_metrics_sede_isolation.py
```

## 4. Frontend CMS existente

```bash
cd /root/ccf/frontend
npx vitest run tests/cms-components.test.ts tests/cms-public-fetch.test.ts
npm run test:e2e:cms
npm run test:e2e:cms:deep
npm run test:e2e:cms:public
```

Para `npm run test:e2e:cms`:

- exportar `E2E_EMAIL`, `E2E_PASSWORD` y `E2E_API_URL` o `API_BASE_URL` absolutos
- si el usuario no existe localmente, correr antes `npm run test:e2e:seed-user`

## 5. Rutas manuales

Validar con consola abierta:

| Ruta | Validar |
|---|---|
| `/plataforma/cms` | dashboard carga |
| `/plataforma/cms/builder` | editor abre |
| `/plataforma/cms/pages` | listado y detalle |
| `/plataforma/cms/preview` | preview controlado |
| `/plataforma/cms/media` | media y folders |
| `/plataforma/cms/themes` | themes |
| `/plataforma/cms/menus` | menus |
| `/plataforma/cms/readiness` | readiness/SEO/broken links |

## 6. Consola del navegador

No cerrar tarea si aparece:

- `401` o `403` no explicados
- `404` de `_next/static`
- `404` de API conocida
- `500`
- errores de hidratación
- `TypeError` por shape inesperada

## 7. Casos funcionales mínimos

### Media

- upload válido
- upload inválido con MIME/ext conflict
- optimize image

### Páginas

- listar página
- crear/archivar desde pages management
- validar preview
- validar publicado

### Public contract

- fetch público CMS
- spec Playwright pública

## 8. Roles mínimos

| Rol | Esperado |
|---|---|
| ADMINISTRADOR | acceso completo |
| GESTOR/EDITOR | mutación en CMS v2 según permisos efectivos |
| LECTOR | solo lectura deseada; revisar deriva real de CMS v1 |

Notas obligatorias:

- revisar `docs/CMS_RBAC_MATRIX.md` antes de tocar `cms.py`, `cms_v2.py` o `enterprise_cms.py`
- no asumir que v1, v2 y enterprise comparten el mismo gate
- si se toca `cms.py`, revalidar explícitamente que las mutaciones sigan exigiendo `cms:edit` y que la lectura administrativa permanezca en `cms:read`

## 9. Criterio de cierre

Una tarea de CMS queda cerrada cuando:

- smoke backend relevante pasa
- frontend CMS específico pasa si el cambio lo requiere
- preview y publicado se validaron por separado cuando aplica
- si cambia contrato, `CMS_API_CONTRACTS.md` se actualiza
- si cambia estado/backlog, `ESTADO_CMS.md` se actualiza

## 10. Cerrado recientemente

- `DONE-RBAC-V1-HARDENING-CMS-001` cerrado el 2026-07-16 con endurecimiento de mutaciones CMS v1 a `cms:edit` y cobertura focal para `LECTOR`
- `DONE-RBAC-ENTERPRISE-CMS-001` cerrado el 2026-07-16 con guards `cms:read` / `cms:manage` en `backend/api/enterprise_cms.py`
- `DONE-CMS-E2E-AUTH-GATE-001` cerrado el 2026-07-16 con el runner administrado y el bootstrap corregido
- `DONE-EXPAND-SMOKE-CMS-001` cerrado el 2026-07-16 con `scripts/test_cms_quality.py` ampliado
- `DONE-VISUAL-CMS-001` cerrado el 2026-07-16 con `frontend/tests/e2e/cms/pages-preview.spec.ts` y `frontend/tests/e2e/cms-public-contract.spec.ts`
- `DONE-GATE-CMS-001` cerrado el 2026-07-16 con el gate canónico y exhaustivo pasando
- `DONE-FRONTEND-E2E-CMS-001` cerrado el 2026-07-16 con `frontend/tests/e2e/cms/smoke.spec.ts`
- `DONE-FRONTEND-DEEP-CMS-001` cerrado el 2026-07-16 con `frontend/tests/e2e/cms/pages-preview.spec.ts`

## 11. Pendientes QA / backlog

- `PEND-CMS-BUILDER-001` — `/plataforma/cms/builder` reportado como no funcional; revisar sections/global blocks, estado de editor y contratos compartidos del builder.

## 12. Estado operativo

Sin otros pendientes abiertos en CMS al momento de esta lectura.
