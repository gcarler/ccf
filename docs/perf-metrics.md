# Metricas de Rendimiento (TTFB/LCP/FCP)

## Objetivo
- Medir el impacto de la migracion a SSR/streaming en rutas clave: `/crm`, `/projects`, `/academy`.
- Mantener una linea base historica para comparar cada iteracion de optimizacion.
- Registrar Web Vitals reales (TTFB/LCP/FCP) desde cliente hacia un endpoint interno para seguimiento continuo.

## Instrumentacion actual
- **Cliente (Web Vitals):** `frontend/src/app/(analytics)/WebVitalsReporter.tsx`.
- **Callback de captura:** `frontend/src/app/reportWebVitals.ts` (filtra `TTFB`, `LCP`, `FCP`).
- **Envio de payload:** `frontend/src/lib/vitals.ts` con `sendBeacon` a `/api/analytics/web-vitals`.
- **Endpoint receptor:** `frontend/src/app/api/analytics/web-vitals/route.ts` (registro por `console.info`).
- **Persistencia local:** `frontend/src/lib/server/webVitalsStore.ts` (append en `frontend/analytics/web-vitals.ndjson`).
- **Dashboard interno:** `frontend/src/app/admin/analytics/web-vitals/page.tsx`.

Formato del payload (actual):
- `id`, `name`, `value`, `label`, `page`, `path`, `timestamp`.

Consulta del endpoint:
- `GET /api/analytics/web-vitals?limit=500`
- Filtros opcionales: `name=TTFB|FCP|LCP`, `path=/academy`
- Respuesta: `records` + `summary` (p50, p75, latest por metrica).

## Baseline Lighthouse (actual)
Fuente: artefactos JSON en `frontend/analytics/` generados con `frontend/scripts/run-lighthouse.mjs`.

| Ruta | Performance | TTFB | FCP | LCP | Estado |
|---|---:|---:|---:|---:|---|
| `/crm` | 0.71 | 56 ms | 1055 ms | 3061 ms | OK |
| `/projects` | 0.80 | 51 ms | 1057 ms | 2857 ms | OK |
| `/academy` | 0.82 | 43 ms | 1054 ms | 2717 ms | OK |

Notas:
- Se amplio `maxWaitForLoad` a `90000` ms en `frontend/scripts/run-lighthouse.mjs` para capturar de forma estable la ruta `/academy`.
- Para comparativas de SSR, tomar como referencia minima estas tres rutas con el mismo perfil de Lighthouse.

## Como volver a medir
1. Levantar app en modo product build (`next build` + `next start`) o usar el script que la levanta automaticamente.
2. Ejecutar:

```bash
cd frontend
npm run perf:lighthouse
```

3. Revisar resultados en:
- `frontend/analytics/crm-lh.json`
- `frontend/analytics/projects-lh.json`
- `frontend/analytics/academy-lh.json`

## Resultados esperados post-SSR
- Reducir `TTFB` en dashboards pesados (meta inicial: >= 20-30% vs baseline valido).
- Mantener `FCP` alrededor de ~1.1s o mejor en perfil mobile Lighthouse.
- Bajar `LCP` en `/crm` y `/projects` por debajo de 2.5s en iteraciones siguientes.
- Obtener corrida valida de `/academy` para habilitar comparativa real.
