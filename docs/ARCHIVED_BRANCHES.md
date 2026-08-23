# Registro de ramas archivadas

Este registro es la fuente visible para ramas retiradas del flujo activo.

**Estado obligatorio:** `ARCHIVADA - NO REACTIVAR`

Una rama listada aqui no debe reutilizarse, hacer push ni fusionarse de nuevo por su nombre original. Si una idea sigue siendo necesaria, debe rescatarse mediante una rama nueva creada desde el `main` actual, revisando el cambio de forma selectiva.

## Ramas archivadas

| Estado | Rama original | Categoria | SHA conservado | Motivo |
|---|---|---|---|---|
| ARCHIVADA - NO REACTIVAR | `feat/contextual-roles-recovery` | stale | `41407b58691cf45f5065e31daa25dc67f8d982cf` | La expiracion QR contextual ya esta absorbida en `main`. |
| ARCHIVADA - NO REACTIVAR | `feature/frontend-ui` | stale | `32d4511fb4c358ca4d5f582b9e9ca4a7e44c846b` | La UI y el ajuste de `DSMetric` ya estan representados en `main`. |
| ARCHIVADA - NO REACTIVAR | `feature/security-hardening` | stale | `9cf48b7c6b2a0d4242a5f8e7d93c1b9479e220ff` | El hardening de CSV, URL publica y validaciones ya esta absorbido en `main`. |
| ARCHIVADA - NO REACTIVAR | `feature/modulo-estructural` | stale | `41f735fd195831cd0be72fab900b91d16553693c` | Divergencia historica masiva; `main` es la version vigente. |
| ARCHIVADA - NO REACTIVAR | `integration/modulo-estructural-to-main-20260823` | merged | `396acb467c369d92745522c9e34e4b3f9011f045` | Integracion antigua ya contenida en `main`; se conserva como evidencia. |

## Fuera de este archivo

`feature/projects-whiteboard` y `fix/color-palette-regression` permanecen activas para rescatar selectivamente los cambios que aun puedan ser utiles. No se deben fusionar completas sobre `main`.

## Regla de reactivacion

No se reactiva una rama archivada. El trabajo futuro debe empezar desde el `main` mas reciente con una rama propietaria nueva y un objetivo delimitado.
