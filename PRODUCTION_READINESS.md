# Production Readiness CCF

Este documento define el estándar operativo para considerar la plataforma CCF lista para producción real.

## Definición De 100%

La plataforma está al 100% solo cuando el estado actual cumple estos criterios medibles:

- Runtime: backend y frontend online, healthchecks 200, PM2 estable, sin errores críticos recientes.
- Web pública: rutas públicas principales, sitemap, robots y assets críticos responden 200.
- CMS: readiness, builder, APIs públicas, theme, menús y contrato hero/pop-up verificados.
- Plataforma: shell y módulos principales cargan sin errores HTTP.
- Datos y seguridad: migraciones bajo Alembic, pruebas de seguridad/permisos presentes, backup reciente o riesgo documentado.
- Tests: smoke, structural, unit y e2e críticos ejecutables y versionados.
- Deploy: build reproducible, restart posterior al build y smoke post-deploy.

## Gate Ejecutable

Comando recomendado:

```bash
cd /root/ccf
python3 scripts/auditing/production_readiness.py
```

Modo estricto:

```bash
python3 scripts/auditing/production_readiness.py --strict
```

Artefactos generados:

- `test_artifacts/production_readiness.json`
- `test_artifacts/production_readiness.md`

## Módulos Cubiertos

| Módulo | Evidencia |
|---|---|
| Runtime e Infra | Git, PM2, healthchecks, logs recientes |
| Web Pública | Home, nosotros, eventos, favicon, sitemap, robots |
| CMS | Readiness UI, builder UI, APIs públicas, tests hero/pop-up |
| Plataforma | Shell, CRM, Academy, Evangelism, Projects, Finance |
| Datos y Seguridad | Backups, Alembic, pruebas de seguridad/permisos |
| Superficie de Tests | Smoke, auth, CMS, CRM, Academy, frontend y e2e |

## Comandos De Calidad Complementarios

```bash
# Backend smoke + arquitectura
python3 -m pytest tests/test_smoke.py tests/test_structural_contracts.py --override-ini="addopts=-p no:cacheprovider" -q

# Readiness script unitario
python3 -m pytest tests/test_production_readiness.py --override-ini="addopts=-p no:cacheprovider" -q

# Frontend CMS/unit
cd frontend
npx vitest run src/lib/cms/heroPopup.test.ts tests/cms-components.test.ts

# E2E público contra producción
PLAYWRIGHT_BASE_URL=https://elfarocc.tech npx playwright test tests/e2e/cms-public-contract.spec.ts --project=chromium

# Build reproducible
npm run build
```

## Regla Operativa Importante

Después de `npm run build` en producción, reiniciar el frontend PM2 antes de validar con navegador:

```bash
pm2 restart ccf-frontend-staging --update-env
```

Esto evita desfases entre HTML servido y chunks `_next/static`.

## Interpretación Del Resultado

- `OK`: todos los checks del módulo están verdes.
- `WARN`: no bloquea operación inmediata, pero impide afirmar 100% estricto.
- `FAIL`: bloquea la certificación y debe corregirse antes de declarar producción sana.

La meta final es `status=OK` y `score=100%` en `production_readiness.json`.
