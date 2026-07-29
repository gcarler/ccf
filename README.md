# CCF

[![CCF CI/CD Pipeline](https://github.com/gcarler/ccf/actions/workflows/ci.yml/badge.svg)](https://github.com/gcarler/ccf/actions/workflows/ci.yml)

Plataforma CCF.

## CI/CD

El pipeline de CI/CD está definido en [`.github/workflows/ci.yml`](.github/workflows/ci.yml) y ejecuta:

- Backend quality gate (lint, type check, tests, security scan)
- Frontend quality gate (lint, type check, tests, E2E smoke tests)
- Database migrations check
- CRM functional tests
- Deploy to staging/production

Además, incluye dos jobs temporales `checkout-benchmark` y `checkout-benchmark-report` para medir el impacto del `fetch-depth` en el checkout del repositorio. Estos jobs se eliminarán una vez recolectados los datos.

Haz clic en el badge de arriba para ver las ejecuciones más recientes.
