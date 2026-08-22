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
PLAYWRIGHT_BASE_URL=https://ministerioselfaro.org npx playwright test tests/e2e/cms-public-contract.spec.ts --project=chromium

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

### Corte global verificado — 2026-08-10

Se verificaron los gates locales de backend y se identificó que el readiness web debe ejecutarse contra el frontend (`127.0.0.1:3000`), mientras el backend API vive en `127.0.0.1:8000`. El dominio canónico de producción es `https://ministerioselfaro.org`.

| Métrica | Resultado | Lectura correcta |
|---|---:|---|
| **Readiness web oficial** | **Pendiente de ejecución final** | El primer intento contra `127.0.0.1:8000` fue inválido: ese puerto sirve API y devuelve 404 para rutas UI. El frontend correcto responde en `127.0.0.1:3000`. |
| **Estado de certificación** | **No certificado todavía** | El quality gate directo del backend está verde, pero falta completar el gate web contra el frontend y validar migraciones contra una base actualizada. |
| Backend health + import | OK | `/api/system/health` HTTP 200, `compileall backend` OK e `import backend.app` OK. |
| Quality gate directo | **OK** | Smoke/Auth 9 passed; Academy/CRM 21 passed; structural/rules 53 passed + 1 skip documentado; índices, vistas y Automation Engine OK. |
| ACAD-TKT-021 | **OK** | `submit_assignment` lee async en chunks de 64 KiB y rechaza >10 MB; pruebas focalizadas verdes. |
| Academy Forum soft-delete | **OK — migración aplicada 2026-08-10** | `ForumThread.deleted_at` + índice aplicados via `alembic upgrade head` (`20260810_0001`); columna verificada en DB, query del modelo OK, backend reiniciado y foro responde 401-auth sin 500. |
| Bandit backend | **OK local** | 0 hallazgos con `.bandit`. |
| datetime.utcnow | **OK local** | 0 llamadas directas detectadas por el gate actualizado. |
| Suite backend completa | **Pendiente** | Los smoke/gates focalizados pasan; la suite completa requiere ejecución separada con timeout controlado. |
| Worktree | **Pendiente** | Hay cambios de trabajo previos y de esta iteración; no se hará commit automático. |
| Runtime web | **Pendiente de validación correcta** | Debe repetirse contra `127.0.0.1:3000`, no contra el backend `8000`. |

**Porcentaje global:** todavía no se comunica como 100%; el readiness web final está pendiente de ejecutarse contra el servicio correcto y el árbol Git no está limpio.

**Siguiente orden de cierre:**

1. ejecutar el gate oficial contra `http://127.0.0.1:3000` con el backend API en `8000`;
2. resolver cualquier asset/ruta web que falle realmente;
3. ejecutar la suite backend completa con timeout y reporte controlado;
4. ✅ **aplicada** la migración canónica `20260810_0001_academy_forum_threads_deleted_at` (2026-08-10): `alembic upgrade head` ejecutado, `alembic current` = head, columna `deleted_at` + índice verificados, query del modelo con filtro soft-delete OK, backend reiniciado sin errores y `GET /api/academy/forum/threads` responde 401-auth (sin 500);
5. separar cambios ajenos y dejar un worktree limpio según el proceso de revisión;
6. volver a ejecutar el gate estricto y comunicar `status=OK`/`score=100%` solo si todos los checks pasan.

La meta final es `status=OK` y `score=100%` en `production_readiness.json`.
