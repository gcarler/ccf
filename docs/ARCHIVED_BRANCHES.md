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
| ARCHIVADA - NO REACTIVAR | `integration/archive-policy-20260823` | merged | `aad2a46871585d5c13f4d37298091de1c921b4e8` | Integracion de la politica de archivo ya publicada en `main`; se conserva como evidencia. |
| ARCHIVADA - NO REACTIVAR | `integration/archive-policy-consistency-20260823` | stale | `bfd4bbdf016cad1eefabe63a93311efdba09343c` | Integracion supersedida por la version v2 basada en el `main` mas reciente. |
| ARCHIVADA - NO REACTIVAR | `integration/archive-policy-consistency-20260823-v2` | merged | `a1320ba1b2044896f5239565d30de0e0d379af63` | Version v2 integrada en `main`; se conserva como evidencia. |

| ARCHIVADA - NO REACTIVAR | `feature/projects-whiteboard` | stale | `8e0159d34b124d58b3a4671f2002849f0bae1363` | Whiteboard y WebSocket ya estan absorbidos en `main`; la rama conserva una version historica que no debe fusionarse completa. |
| ARCHIVADA - NO REACTIVAR | `fix/color-palette-regression` | stale | `9e42a2a742188ed3653026bade99d040cd2b76dc` | Rama historica basada en un arbol antiguo; su correccion de paleta fue rescatada selectivamente desde el `main` actual. |
| ARCHIVADA - NO REACTIVAR | `feature/frontend-color-palette-main-20260823` | merged | `68131cbfda3e3d4edd02d9449c18b36a067dbb9d` | Rescate selectivo de tokens de paleta prohibidos, integrado en `main`; se conserva como evidencia. |
| ARCHIVADA - NO REACTIVAR | `integration/frontend-color-palette-main-20260823-v2` | merged | `add3e318365c00d80b4c7ba4cb7bae68e83e02d8` | Integracion v2 basada en el `main` mas reciente, ya absorbida en `main`; se conserva como evidencia. |
| ARCHIVADA - NO REACTIVAR | `docs/archive-color-palette-20260823` | stale | `f83376adbb4943b59aa25a82dc86a6bfc0bd5b5b` | Rama documental supersedida por la integracion final del registro; se conserva como evidencia. |
| ARCHIVADA - NO REACTIVAR | `integration/archive-color-palette-20260823` | stale | `7ad336e12be7f28674837f4c93208d2a4976420a` | Integracion supersedida cuando `main` avanzo con cambios concurrentes. |
| ARCHIVADA - NO REACTIVAR | `integration/archive-color-palette-20260823-v2` | stale | `53c982af2050340ff829a5c3e18b562b8dd0310f` | Integracion supersedida por la v3 basada en un `main` mas reciente. |
| ARCHIVADA - NO REACTIVAR | `integration/archive-color-palette-20260823-v3` | merged | `81c6807314044b9c91c824ed90f225c726e8eff4` | Integracion final del registro, absorbida en `main`; se conserva como evidencia. |

## Fuera de este archivo

La correccion de paleta ya fue rescatada selectivamente en `feature/frontend-color-palette-main-20260823` y publicada en `main`. La rama historica y las ramas temporales del proceso no deben reactivarse ni fusionarse por su nombre original.

## Regla de reactivacion

No se reactiva una rama archivada. El trabajo futuro debe empezar desde el `main` mas reciente con una rama propietaria nueva y un objetivo delimitado.
