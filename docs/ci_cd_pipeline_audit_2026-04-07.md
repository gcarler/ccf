# Auditoria CI/CD - Plataforma CCF

Fecha: 2026-04-07
Auditor: OpenCode
Alcance: pipelines detectados en GitHub Actions (`.github/workflows/ci.yml`, `.github/workflows/deploy.yml`)

## 1) Inventario y mapa de flujo

### 1.1 Pipelines activos
- CI: `.github/workflows/ci.yml`
- Deploy: `.github/workflows/deploy.yml`

No se detectaron pipelines en CircleCI, GitLab CI, Jenkins, Azure Pipelines ni Bitbucket Pipelines.

### 1.2 Flujo operativo actual
- `push` a `main/master` o `pull_request` ejecuta CI.
- `push` a `main` ejecuta Deploy.
- Deploy construye/pushea dos imagenes (`backend` y `frontend`) y luego hace `helm upgrade --install`.

## 2) Matriz de control (0-3)

Escala: 0 ausente, 1 debil, 2 aceptable, 3 maduro.

| Dominio | Control | Puntaje | Evidencia | Resultado |
|---|---|---:|---|---|
| Seguridad | Secretos hardcodeados | 1 | `.github/workflows/ci.yml:13` | `SECRET_KEY` hardcodeado en CI |
| Seguridad | Principio de minimo privilegio en workflows | 1 | `.github/workflows/ci.yml` | CI no define bloque `permissions` |
| Seguridad | Acciones pinneadas por SHA | 1 | `.github/workflows/*.yml` | Se usan tags mayores (`@v4`, `@v5`, `@v6`) |
| Seguridad | Seguridad de contenedores en runtime | 1 | `backend.Dockerfile`, `frontend/Dockerfile` | Contenedores corren como root |
| Seguridad | Hardening Kubernetes (securityContext) | 0 | `deploy/helm/ccf/templates/*deployment.yaml` | No `securityContext` de pod/contenedor |
| Calidad | Cobertura de gates de frontend | 2 | `.github/workflows/ci.yml:49-66` | Lint + typecheck + test + e2e + quality gate |
| Calidad | Cobertura de gates de backend | 2 | `.github/workflows/ci.yml:27-33` | pre-commit + pytest + alembic |
| Calidad | Reproducibilidad dependencias frontend | 2 | `.github/workflows/ci.yml:48` | Usa `npm ci` en CI |
| Calidad | Reproducibilidad dependencias backend | 1 | `.github/workflows/ci.yml:24-26` | `pip install -r requirements.txt` sin lockfile |
| Release safety | Bloqueo explicito CI->CD | 1 | `.github/workflows/deploy.yml` | No gate explicito; depende de branch protection externa |
| Release safety | Concurrency/cancelacion de despliegues | 0 | `.github/workflows/deploy.yml` | No `concurrency` |
| Release safety | Despliegue atomico y espera de salud | 1 | `.github/workflows/deploy.yml:69-73` | `helm upgrade` sin `--atomic --wait --timeout` |
| Release safety | Probe de readiness backend valida | 0 | `deploy/helm/ccf/templates/backend-deployment.yaml:37`, `backend/api/system.py:82` | Probe apunta a `/healthz`, endpoint real es `/api/system/health` |
| Operacion | Artefactos de diagnostico | 2 | `.github/workflows/ci.yml:75-88` | Upload de Playwright report y Storybook |
| Operacion | Timeouts por job | 0 | `.github/workflows/*.yml` | No `timeout-minutes` |
| Operacion | Alerting/notificaciones de fallo | 0 | `.github/workflows/*.yml` | No integracion Slack/Teams/email |
| Costo | Caching backend pip | 0 | `.github/workflows/ci.yml` | No cache pip |
| Costo | Caching Docker buildx | 0 | `.github/workflows/deploy.yml` | No `cache-from/cache-to` |
| Costo | Filtros por paths en deploy | 0 | `.github/workflows/deploy.yml` | Cualquier cambio en `main` dispara deploy |

Puntaje global estimado: 16/57 (~28%).

## 3) Hallazgos priorizados

### Criticos
1. Readiness probe de backend inconsistente
   - Evidencia: `deploy/helm/ccf/templates/backend-deployment.yaml:37` usa `/healthz`.
   - Endpoint real observado: `backend/api/system.py:82` define `/health`, expuesto bajo prefijo `/api/system`.
   - Riesgo: pods no listos, rollout fallido o trafico inestable.

### Altos
1. Deploy sin control de concurrencia
   - Evidencia: `.github/workflows/deploy.yml` sin `concurrency`.
   - Riesgo: despliegues solapados con pushes consecutivos.
2. Falta de gate explicito CI->CD
   - Evidencia: Deploy se dispara por `push` a `main` sin check de workflow previo.
   - Riesgo: despliegue de commits con calidad no validada si branch protection no esta estricta.
3. Helm upgrade sin atomicidad ni espera
   - Evidencia: `.github/workflows/deploy.yml:69-73`.
   - Riesgo: releases parcialmente aplicadas y rollback manual mas complejo.
4. Endurecimiento de seguridad incompleto en Kubernetes
   - Evidencia: templates de deployment sin `securityContext`.
   - Riesgo: mayor superficie de ataque en runtime.

### Medios
1. Secreto hardcodeado en CI
   - Evidencia: `.github/workflows/ci.yml:13` (`SECRET_KEY: super-secret`).
2. CI sin permisos explicitos
   - Evidencia: `.github/workflows/ci.yml` sin bloque `permissions`.
3. Acciones no pinneadas por SHA
   - Evidencia: uso de `@v4/@v5/@v6`.
4. Deploy sin filtros por rutas
   - Evidencia: `.github/workflows/deploy.yml`.
5. Sin timeouts por job
   - Evidencia: `.github/workflows/*.yml`.
6. Imagenes sin tags operativos (solo SHA)
   - Evidencia: `.github/workflows/deploy.yml:39,47`.

### Bajos
1. Documentacion de deploy desalineada con workflow
   - Evidencia: `deploy/README.md:39-42` menciona `GHCR_USERNAME`, `GHCR_TOKEN`, `HELM_ARGS`; workflow usa `GITHUB_TOKEN` y `HELM_EXTRA_ARGS`.
2. Herramientas de validacion de workflows no instaladas localmente
   - Evidencia: `actionlint` no disponible en entorno de auditoria.

## 4) Validaciones ejecutadas

- Confirmacion de pipelines existentes via inventario de archivos.
- Reconciliacion de scripts/artefactos referenciados por workflows (archivos existen).
- Verificacion de disponibilidad local de herramientas de chequeo:
  - `kubectl`: disponible.
  - `helm`: no disponible en este entorno local.
  - `actionlint`: no disponible en este entorno local.
- Verificacion de endpoints/probes en codigo backend y chart Helm.

## 5) Plan de remediacion en 3 olas

### Ola 1 (1-3 dias, alto impacto)
1. Corregir readiness probe backend a `/api/system/health`.
2. Agregar `concurrency` en deploy (grupo por branch/entorno).
3. Endurecer `helm upgrade` con `--atomic --wait --timeout`.
4. Eliminar secreto hardcodeado de CI (`SECRET_KEY`) y usar variable de test no sensible.
5. Agregar `permissions: contents: read` en CI y permisos minimos por job.

### Ola 2 (1-3 semanas, robustez)
1. Agregar filtros por `paths` en deploy para evitar despliegues por cambios no relevantes.
2. Incorporar cache pip en CI backend y cache buildx para Docker.
3. Agregar `timeout-minutes` por job.
4. Agregar smoke post-deploy (HTTP checks y/o e2e minimo contra endpoint real).
5. Alinear `deploy/README.md` con secretos reales del workflow.

### Ola 3 (trimestre, madurez)
1. Pinning de acciones por SHA + politica de renovacion controlada.
2. Firma de imagenes/SBOM/provenance y escaneo de vulnerabilidades en pipeline.
3. Hardening Kubernetes completo (`securityContext`, `runAsNonRoot`, `readOnlyRootFilesystem`).
4. Alertas operativas (Slack/Teams) con runbooks de recuperacion.

## 6) Checklist operativa recurrente (por sprint)

1. Triggers
   - Validar que CI cubre PR y que CD no se dispara sin gate de calidad.
2. Seguridad
   - Confirmar ausencia de secretos hardcodeados y permisos minimos.
3. Calidad
   - Verificar lint/typecheck/test/e2e y estabilidad de suites.
4. Despliegue
   - Confirmar `concurrency`, `--atomic --wait`, y probes validas.
5. Operacion
   - Confirmar artefactos de debug, timeouts y notificaciones.
6. Costo
   - Revisar cache efectiva y jobs caros.
7. Trazabilidad
   - Validar mapping commit -> imagen -> release y evidencia de ejecucion.

## 7) KPI sugeridos para seguimiento

- Tasa de exito CI (% ejecuciones verdes).
- Lead time de pipeline (p50/p95).
- Frecuencia de despliegue exitoso.
- MTTR por fallo de pipeline.
- Porcentaje de despliegues con rollback.
- Costo promedio por ejecucion y por release.

## 8) Estado de cierre de auditoria

- Auditoria ejecutada y documentada.
- Requiere aprobacion de backlog de remediacion para fase de implementacion.
