# Production Readiness CCF

Este documento define el estándar operativo para considerar la plataforma CCF lista para producción real.

## Definición De 100%

La plataforma está al 100% solo cuando el estado actual cumple estos criterios medibles:

- Runtime: backend y frontend online, healthchecks 200, supervisor de procesos coherente con el despliegue real, sin errores críticos recientes.
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
| Runtime e Infra | Git, supervisión de procesos, healthchecks, logs recientes |
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

Después de `npm run build` en producción, reiniciar el frontend usando el supervisor real de la instancia antes de validar con navegador:

```bash
# Esta instancia usa PM2
pm2 restart ccf-frontend-staging --update-env

# No mezclar PM2 con `./startccf` o `npm run start` manual en la misma máquina.
```

Esto evita desfases entre HTML servido y chunks `_next/static`.
El `build` del frontend además debe preservar el último `.next` sano si la compilación falla o se interrumpe.

## Interpretación Del Resultado

- `OK`: todos los checks del módulo están verdes.
- `WARN`: no bloquea operación inmediata, pero impide afirmar 100% estricto.
- `FAIL`: bloquea la certificación y debe corregirse antes de declarar producción sana.

El `score` es un porcentaje de evidencia operativa, no una aprobación automática: un
solo `FAIL` mantiene el estado global en `FAIL`, aunque los demás módulos estén
verdes. La certificación requiere simultáneamente `status=OK`, `score=100%`, CI
verde y un árbol Git limpio.

### Corte global posterior al commit CMS — 2026-08-09

Se ejecutó `scripts/auditing/production_readiness.py` contra
`https://elfarocc.tech` después de `86431155` (`fix(cms): align v1 v2 routes and RBAC contracts`).

| Métrica | Resultado | Lectura correcta |
|---|---:|---|
| **Readiness operativo oficial** | **95%** | Score calculado por el gate: módulos `85/100/100/86/100/100`, redondeado a 95. |
| **Estado de certificación** | **FAIL / no listo** | Hay fallos críticos aunque el score agregado sea alto. |
| Backend health + PM2 | OK | Backend online, 2 reinicios; healthcheck local HTTP 200. |
| Ruff backend/tests | OK | 0 errores. |
| mypy backend | OK | 0 errores en 286 archivos con `--ignore-missing-imports`. |
| Compilación backend | OK | `compileall` sin errores. |
| CI principal | **FAIL** | Falla el test estructural de Academy `ACAD-TKT-021`: `submit_assignment` usa `file.file.read()` y no satisface la evidencia exigida por el backlog (`await file.read()`). |
| Quality gate directo | **FAIL** | Tests core/dominio/estructurales e índices/vistas pasan; falla la regla por 4 usos de `datetime.utcnow()`. |
| Bandit backend | **FAIL** | 43 hallazgos: 4 altos B324, 38 medios B608 y 1 bajo B105; requieren clasificación/corrección antes de una certificación estricta. |
| Suite backend completa | **NO CONCLUYENTE** | `pytest tests/ --no-cov` superó 600 s; no se cuenta como verde. |
| Worktree | **FAIL** | Quedan cambios ajenos de Evangelismo/frontend sin commit; no se incluyeron en el commit CMS. |
| Runtime web | **FAIL parcial** | El gate detecta dos referencias CSS de Evangelismo con HTTP 404, aunque las páginas principales responden HTTP 200. |

**Porcentaje real que debe comunicarse:** **95% de readiness operativa medida**.
La **certificación estricta está bloqueada/no es certificable** hasta cerrar los
`FAIL` anteriores. “Bloqueada” no es un porcentaje producido por el gate: es la
aplicación binaria del contrato de certificación cuando existe un bloqueo crítico,
sin negar que la plataforma esté operativa.

**Siguiente orden de cierre:**

1. corregir o actualizar con evidencia válida `ACAD-TKT-021`;
2. revisar los 4 usos de `datetime.utcnow()` detectados por el quality gate;
3. clasificar/corregir Bandit B324/B608/B105, sin ocultarlos con `|| true`;
4. resolver los assets CSS 404 de Evangelismo;
5. repetir CI y la suite backend completa con un timeout y reporte de fallos controlado;
6. dejar el worktree limpio y volver a ejecutar el gate estricto.

La meta final es `status=OK` y `score=100%` en `production_readiness.json`.
