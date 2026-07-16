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
npx playwright test tests/e2e/cms-public-contract.spec.ts
```

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
- editar o publicar
- validar preview
- validar publicado

### Public contract

- fetch público CMS
- spec Playwright pública

## 8. Roles mínimos

| Rol | Esperado |
|---|---|
| ADMIN | acceso completo |
| GESTOR/EDITOR | mutación en CMS v2 según permisos efectivos |
| LECTOR | solo lectura deseada; revisar deriva real de CMS v1 |

Notas obligatorias:

- revisar `docs/CMS_RBAC_MATRIX.md` antes de tocar `cms.py`, `cms_v2.py` o `enterprise_cms.py`
- no asumir que v1, v2 y enterprise comparten el mismo gate
- si se toca `cms.py`, revalidar explícitamente la deriva actual de mutaciones con `cms:read`

## 9. Criterio de cierre

Una tarea de CMS queda cerrada cuando:

- smoke backend relevante pasa
- frontend CMS específico pasa si el cambio lo requiere
- preview y publicado se validaron por separado cuando aplica
- si cambia contrato, `CMS_API_CONTRACTS.md` se actualiza
- si cambia estado/backlog, `ESTADO_CMS.md` se actualiza
