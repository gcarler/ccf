# Plan de Calidad — Módulo de Evangelismo CCF

> **Objetivo:** mantener evangelismo como módulo aislado, con validación repetible y backlog realista.
>
> **Actualizado:** 2026-07-17
> **Complementa:** `docs/ESTADO_EVANGELISMO.md`

## 1. Estado operativo actual

Evangelismo ya tiene cerrados los frentes que dominaron la estabilización inicial:

- contratos backend de eventos
- contratos backend de sesiones
- follow-up
- multiplicación
- smoke canónico backend
- smoke frontend
- cobertura profunda frontend
- búsqueda remota de personas
- migración principal de RBAC a `evangelism:*`

La calidad actual del módulo ya no depende de descubrir qué probar; depende de sostener:

- consistencia de permisos por rol
- deuda estructural de la pantalla de estrategia
- alineación documental continua con el código

## 2. Regla de trabajo

- No mezclar fixes de evangelismo con CRM, proyectos, calendario o CMS salvo contrato cruzado real.
- Toda tarea debe mapearse a una superficie concreta:
  - estrategias
  - grupos
  - sesiones
  - asistencia/follow-up
  - eventos
  - multiplicación
  - reportes/rankings/analytics
  - scanner
- Si se toca backend y frontend en la misma unidad, documentar el contrato que une ambas capas.
- Si cambia permiso real, actualizar primero docs de RBAC y contratos.

## 3. Fase 0 — Diagnóstico base

**ID:** `EVANG-FASE0-DIAG`

Meta: confirmar que el módulo sigue sano antes de abrir una nueva unidad.

Comandos:

```bash
cd /root/ccf
cat docs/ESTADO_EVANGELISMO.md
cat docs/EVANGELISMO_API_CONTRACTS.md
cat docs/EVANGELISMO_RBAC_MATRIX.md
cat docs/EVANGELISMO_QA_CHECKLIST.md
./venv/bin/python scripts/test_evangelism_quality.py
```

Criterio de salida:

- estado canónico leído
- contratos leídos
- matriz RBAC leída
- smoke base en verde o primer fallo real identificado

## 4. Fase 1 — QA runtime de permisos

**ID:** `PARCIAL-RUNTIME-AUTH-001`

Problema vigente:

- el backend ya migró en gran parte a `evangelism:read/edit/manage`
- todavía existen rutas contextuales y flujos con `require_active_user`
- el riesgo ahora es el drift UI/rol/guard real, no la ausencia de taxonomía

Orden:

1. Verificar `docs/EVANGELISMO_RBAC_MATRIX.md`
2. Probar al menos:
   - `/plataforma/evangelism`
   - `/plataforma/evangelism/groups`
   - `/plataforma/evangelism/events`
   - `/plataforma/evangelism/rankings`
   - `/plataforma/evangelism/multiplication`
   - `/plataforma/evangelism/scanner`
3. Validar por rol:
   - ADMIN
   - GESTOR o rol granular equivalente
   - COORDINADOR
   - un rol restringido real
4. Si aparece drift:
   - corregir frontend si hace fetch de más
   - corregir backend si el guard es el que quedó mal
5. Actualizar docs si cambia la lectura por rol

Criterio de salida:

- ningún `401/403` estructural inesperado
- toda restricción queda explicada por el guard real
- la UI no dispara requests prohibidas para ese rol/superficie

## 5. Fase 2 — Descomposición de estrategia

**IDs:** `PARCIAL-STRATEGY-PAGE-001`, `PEND-STRATEGY-DECOMPOSE-001`

Este sigue siendo el frente estructural principal del módulo.

Estado actual:

- ya se extrajeron hooks funcionales relevantes
- la page sigue siendo demasiado grande y sensible

Orden recomendado:

1. congelar contrato actual
2. seguir separando lectura, mutaciones y paneles visuales
3. dejar la page como orquestador
4. cubrir cada extracción sensible con prueba o e2e focalizada

Criterio de salida:

- menos lógica de negocio embebida en `strategies/[id]/page.tsx`
- fetches centralizados y cancelables
- cero regresiones de layout, permisos o rutas

## 6. Fase 3 — Validación canónica

**IDs:** `PARCIAL-SMOKE-EVANGELISM-001`, `PEND-EXPAND-SMOKE-EVANGELISM-001`

Estado: cerrado como problema de infraestructura, vigente como disciplina operativa.

Punto de entrada canónico:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py
./venv/bin/python scripts/test_evangelism_quality.py --backend-deep
./venv/bin/python scripts/test_evangelism_quality.py --frontend-smoke
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
./venv/bin/python scripts/test_evangelism_quality.py --expanded
```

Regla:

- el script raíz es la entrada oficial del módulo
- no depender de memoria operativa para elegir suites

## 7. Fase 4 — Cierre por unidad

**ID:** `EVANG-FASE4-CIERRE`

Antes de cerrar una unidad:

1. correr el smoke relevante
2. verificar rutas impactadas
3. confirmar que la consola no tenga errores nuevos
4. actualizar docs si cambió:
   - backlog
   - contrato
   - guard real
   - lectura por rol

Criterio de salida:

- cambio validado en la capa tocada
- documentación alineada con el código real
- commit coherente por unidad

## 8. Backlog vivo

### Activo

- `PARCIAL-RUNTIME-AUTH-001`
- `PARCIAL-STRATEGY-PAGE-001`
- `PEND-STRATEGY-DECOMPOSE-001`

### Cerrado y no reabrir salvo nueva evidencia

- `PEND-PERSONAS-SEARCH-001`
- `PEND-RBAC-EVANGELISM-001`
- `PARCIAL-EVENTS-001`
- `PARCIAL-MULTIPLICATION-001`
- `PARCIAL-FOLLOWUP-001`
- `PEND-EVENTS-CONTRACT-001`
- `PEND-SESSIONS-CONTRACT-001`
- `PEND-FRONTEND-E2E-EVANGELISM-001`
- `PEND-FRONTEND-E2E-EVANGELISM-EVENTS-SCANNER-001`
- `PARCIAL-SMOKE-EVANGELISM-001`
- `PEND-EXPAND-SMOKE-EVANGELISM-001`

## 9. Relación con otros documentos

Usar en este orden:

1. `docs/ESTADO_EVANGELISMO.md`
2. `docs/PLAN_DE_TRABAJO_EVANGELISMO.md`
3. `docs/EVANGELISMO_RBAC_MATRIX.md`
4. `docs/EVANGELISMO_API_CONTRACTS.md`
5. `docs/EVANGELISMO_QA_CHECKLIST.md`

Este archivo no reemplaza el estado canónico. Lo traduce a plan de ejecución y control de calidad.
