# Plan de deuda - `lint:strict`

Fecha: 2026-04-22
Estado: Abierto
Owner sugerido: Frontend Lead

## Contexto

El gate `lint:strict` presenta deuda historica amplia (`no-unused-vars` y reglas relacionadas) en modulos fuera del alcance critico de salida inmediata. Para no bloquear el ciclo de estabilizacion de staging, el paso en CI fue pasado a modo **advisory** temporal (`continue-on-error: true`).

Workflow afectado:
- `.github/workflows/ci.yml`

## Alcance de remediacion

1. Eliminar imports/variables no usadas en dominios con mayor volumen:
   - `src/app/crm/**`
   - `src/components/crm/**`
   - `src/components/projects/**`
2. Corregir errores puntuales de reglas funcionales (`react/no-unescaped-entities`, `prefer-const`, hooks deps) en rutas publicas y soporte.
3. Volver a habilitar `lint:strict` como bloqueante en CI.

## Criterio de cierre

- `npm run lint:strict` en verde local y en CI.
- Paso `Run strict lint check (advisory)` revertido a bloqueante.
- Evidencia de cierre en PR con salida de comando y referencia de commit.

## Fecha objetivo sugerida

- Objetivo: dentro de 7 dias calendario desde esta fecha.
