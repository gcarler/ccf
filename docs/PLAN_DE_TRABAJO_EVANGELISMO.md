# Plan de Trabajo — Evangelismo

> **Origen:** auditoría forense del 2026-07-17
> **Documento base:** [AUDITORIA_FORENSE_EVANGELISMO_2026-07-17.md](/root/ccf/docs/AUDITORIA_FORENSE_EVANGELISMO_2026-07-17.md)
> **Propósito:** convertir hallazgos en un orden de ejecución realista para una nueva sesión de trabajo.

## 1. Principios de ejecución

- No tocar varias capas a ciegas en la misma fase.
- Cada fase debe cerrar una contradicción estructural, no solo un síntoma.
- No actualizar `ESTADO_EVANGELISMO.md` como “cerrado” hasta que la fase correspondiente quede verificada.
- Si una fase cambia permisos o contratos, actualizar:
  - `docs/EVANGELISMO_RBAC_MATRIX.md`
  - `docs/EVANGELISMO_API_CONTRACTS.md`
  - `docs/EVANGELISMO_QA_CHECKLIST.md`

## 2. Orden de ataque recomendado

### Fase A — Definir el modelo real de acceso del módulo

Objetivo:

- decidir y documentar qué superficies deben gobernarse por:
  - `evangelism:read`
  - `evangelism:edit`
  - `evangelism:manage`
  - acceso contextual
  - `require_active_user`

Trabajo:

1. inventariar rutas de eventos que hoy usan `require_active_user`
2. decidir cuáles son intencionalmente contextuales
3. decidir si `GET /events/` es `read` real o `manage` encubierto
4. fijar la matriz final por superficie

Salida esperada:

- decisión explícita de arquitectura sobre RBAC de eventos
- checklist clara para backend y frontend

Bloqueadores resueltos:

- evita seguir corrigiendo UI con una semántica de permisos indefinida

### Fase B — Corregir incoherencias backend de permisos

Objetivo:

- eliminar contradicciones entre dependencia declarada y chequeo real

Trabajo mínimo:

1. corregir `backend/api/evangelism_events/events_main.py`
   - `GET /events/`
   - mensaje y lógica de permiso
2. revisar si otras rutas de eventos mezclan guard canónico + filtro manual de rol
3. validar que la semántica final coincida con Fase A

Salida esperada:

- backend sin rutas que anuncien `read` y ejecuten `manage`

### Fase C — Alinear frontend con `evangelism:*` y con el modelo real del backend

Objetivo:

- sacar al frontend del modelo legacy “pastoral o administrativo”

Trabajo:

1. refactorizar `EvangelismShell`
2. refactorizar `EvangelismClient`
3. revisar gating en:
   - `strategies/[id]/page.tsx`
   - `groups/page.tsx`
   - `groups/[id]/page.tsx`
   - otras vistas con listas cerradas de roles
4. basar visibilidad y fetches en:
   - `hasModuleAccess(...)`
   - capacidades reales de la superficie
   - ownership/contexto cuando aplique

Salida esperada:

- usuarios con permisos granulares válidos no quedan falsamente bloqueados
- `coordinador` deja de depender de hacks de UI

### Fase D — Blindar QA de permisos por rol

Objetivo:

- que la migración RBAC deje de depender de pruebas con `admin`

Trabajo:

1. agregar matriz de tests backend por rol:
   - admin
   - coordinador
   - lector granular
   - editor granular
   - gestor granular
2. cubrir especialmente:
   - estrategias
   - eventos
   - grupos
   - scanner
   - asistencia contextual
3. agregar o extender e2e mínimo para un rol no-admin

Salida esperada:

- regresiones RBAC detectables automáticamente

### Fase E — Reparar el gate canónico frontend profundo

Objetivo:

- recuperar confiabilidad operativa del QA frontend del módulo

Trabajo:

1. aislar por qué `playwright.config.ts` + `run-managed-playwright.mjs` dependen de `next dev -H 0.0.0.0`
2. determinar si el fallo `EPERM` es:
   - del entorno
   - del host bind
   - del webServer config
3. dejar un camino reproducible para:
   - `npm run test:e2e:evangelism`
   - `npm run test:e2e:evangelism:deep`
   - `scripts/test_evangelism_quality.py --frontend-deep`

Salida esperada:

- gate frontend profundo funcional o causa raíz documentada con workaround oficial

### Fase F — Endurecer la suite de analytics y coverage auxiliar

Objetivo:

- que la cobertura auxiliar deje de aceptar fallos internos como señal válida

Trabajo:

1. corregir `_ok(status)` en `tests/test_evangelism_analytics_coverage.py`
2. revisar otras suites “coverage” que toleren demasiado
3. separar claramente:
   - tests de cobertura de líneas
   - tests de contrato/estabilidad

Salida esperada:

- una suite que falla cuando analytics devuelve `500`

### Fase G — Continuar la descomposición estructural del frontend

Objetivo:

- bajar el riesgo sistémico de las pantallas grandes del módulo

Superficies prioritarias:

1. `strategies/[id]/page.tsx`
2. `events/page.tsx`
3. `groups/[id]/page.tsx`

Trabajo:

1. seguir extrayendo hooks y paneles
2. reducir `any`
3. añadir `AbortController` y cleanup donde falte
4. consolidar tipos compartidos

Salida esperada:

- menos superficie de regresión
- mejor mantenibilidad
- contratos UI más fuertes

## 3. Backlog priorizado

### P0 — Crítico

- Reconciliar RBAC real del módulo entre backend, frontend y docs

### P1 — Alto

- Corregir `GET /events/`
- Alinear gating frontend con `evangelism:*`
- Restaurar gate `--frontend-deep`

### P2 — Medio

- Cobertura de permisos por rol no-admin
- Endurecer suites de analytics
- Seguir descomposición de pantallas grandes

## 4. Definición de cierre por fase

Una fase se considera cerrada solo si:

1. el cambio de código existe
2. la suite relevante pasa
3. la documentación contractual quedó alineada
4. el hallazgo correspondiente deja de reproducirse

## 5. Comandos sugeridos para la próxima sesión

Diagnóstico rápido:

```bash
cd /root/ccf
./venv/bin/python scripts/test_evangelism_quality.py --backend-deep
./venv/bin/python scripts/test_evangelism_quality.py --frontend-deep
```

Lectura obligatoria:

```bash
cat docs/AUDITORIA_FORENSE_EVANGELISMO_2026-07-17.md
cat docs/PLAN_DE_TRABAJO_EVANGELISMO.md
cat docs/ESTADO_EVANGELISMO.md
cat docs/EVANGELISMO_RBAC_MATRIX.md
cat docs/EVANGELISMO_API_CONTRACTS.md
```
