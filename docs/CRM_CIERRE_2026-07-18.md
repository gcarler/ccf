# Cierre de Certificación CRM — 2026-07-18

## Veredicto

El módulo **CRM** quedó **cerrado al 100% para el alcance vigente del plan de calidad** el **18 de julio de 2026**.

El cierre se sostiene sobre evidencia reproducible en cuatro frentes:

- completitud funcional end-to-end del módulo
- consistencia estructural entre frontend, backend y contratos
- regresión profunda de rutas críticas y bordes
- auditoría de permisos, filtros, integridad y escenarios adversariales

## Hallazgos estructurales cerrados

### 1. Wiki colaborativa del pipeline CRM rompía runtime por contrato incompleto

Síntoma real:

- `npm run test:e2e:crm` fallaba en `/plataforma/crm/pipeline`
- el runtime emitía `404 /api/wiki/pages/crm_pipeline_wiki_notes`

Raíz:

- `useWikiDocument` asumía que la página existía o que podía persistir con `POST` ciego
- `GET /api/wiki/pages/{page_key}` devolvía `404` para documentos colaborativos ausentes

Cierre aplicado:

- `frontend/src/hooks/useWikiDocument.ts`
  - diferencia `404` de error real
  - deja de asumir páginas presembradas
  - corrige persistencia `create/update` de forma coherente
- `backend/api/wiki.py`
  - devuelve documento virtual vacío para páginas colaborativas aún no materializadas
- `tests/test_crm_domain.py`
  - fija el contrato del wiki lazy para `crm_pipeline_wiki_notes`

Resultado:

- desapareció la regresión runtime del pipeline CRM
- el módulo ya no depende de llaves wiki precreadas para cargar vistas críticas

### 2. Suites profundas del CRM quedaron desalineadas con el endurecimiento real de permisos

Síntoma real:

- las suites adversariales y visuales del backend fallaban con `401`
- los tests seguían llamando endpoints protegidos de `automations` sin autenticación

Raíz:

- deuda histórica de pruebas frente al contrato vivo de RBAC del módulo

Cierre aplicado:

- `tests/test_crm_concurrency_adversarial.py`
- `tests/test_crm_visual.py`
- `tests/test_crm_challenger_stress.py`

Se normalizaron con helpers administrativos para validar el contrato real del CRM, sin relajar seguridad del backend.

Resultado:

- la evidencia profunda quedó alineada con la seguridad vigente del módulo
- no se abrió el backend para acomodar tests obsoletos

## Evidencia ejecutada

### Backend

- `./venv/bin/python scripts/test_crm_quality.py`
  - `47 passed` smoke mínimo CRM
  - `31 passed` RBAC HTTP
- `./venv/bin/python scripts/test_crm_quality.py --backend-deep --pipeline --concurrency`
  - `24 passed` cobertura amplia backend CRM
  - `99 passed` pipeline visual y adversarial
  - `21 passed` concurrencia y stress CRM
  - resumen: `5 passed, 0 failed, 5 total suites`

### Frontend

- `npm run test:e2e:crm`
  - smoke crítico autenticado + dashboard/groups admin
  - `14 passed`
- `npm run test:e2e:crm:deep`
  - dashboard
  - groups admin bridge
  - persona detail
  - messaging
  - resources
  - pipeline deep
  - `17 passed`

## Estado final

El CRM queda certificado para el alcance actual porque cumple simultáneamente esto:

- rutas críticas cargan sin errores API/runtime
- contratos UI/API quedan consistentes en el flujo crítico detectado
- wiki compartida del módulo ya no depende de preseed manual
- backend protegido mantiene RBAC y aislamiento sin ceder por presión de tests
- suites profundas del módulo quedan verdes con el contrato vivo

## Archivos tocados en este cierre

- `backend/api/wiki.py`
- `frontend/src/hooks/useWikiDocument.ts`
- `tests/test_crm_domain.py`
- `tests/test_crm_concurrency_adversarial.py`
- `tests/test_crm_visual.py`
- `tests/test_crm_challenger_stress.py`

## Nota operativa

Para que la evidencia E2E reflejara el código actual, fue necesario recargar el runtime canónico:

- `pm2 restart ccf-backend-staging --update-env`

Después del reinicio, el backend quedó sano y la regresión CRM pasó contra runtime real.
