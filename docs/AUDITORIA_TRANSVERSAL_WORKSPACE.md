# Auditoría Transversal del Workspace

## Objetivo

Auditar el workspace completo de CCF y cerrar discrepancias entre módulos para dejar:

- backend alineado con frontend y base de datos
- frontend alineado con contratos reales de API y CMS
- base de datos alineada con modelos y migraciones
- scripts y tooling alineados con el runtime real
- pruebas y gates capaces de detectar regresiones

## Principios

- Un cambio por capa cuando sea posible.
- Primero contratos y esquema, luego UI.
- Migraciones reversibles.
- No introducir compatibilidad nueva si el contrato canónico ya existe.
- Cada discrepancia debe cerrar con evidencia: test, audit, e2e o schema check.

## Fase 0. Inventario Base

### Tareas

- Levantar `git status --short`.
- Enumerar rutas, módulos, scripts, migraciones, tests y docs operativas.
- Identificar puntos de acoplamiento entre frontend, backend, DB y scripts.
- Revisar los gates existentes:
  - `scripts/auditing/production_readiness.py`
  - `scripts/audit_backend_schema.py`
  - tests de contrato y e2e críticos

### Entregables

- Mapa del workspace.
- Lista de módulos vivos.
- Lista de contratos que gobiernan el sistema.

## Fase 1. Mapa de Discrepancias

### Tareas

- Comparar frontend vs backend:
  - tipos TS vs schemas Pydantic
  - nombres de campos
  - slugs y rutas
  - estados y enums
- Comparar backend vs base de datos:
  - modelos vs esquema real
  - tablas legacy
  - índices, constraints y relaciones
- Comparar frontend vs runtime:
  - páginas públicas
  - CMS
  - hooks compartidos
  - parseos frágiles
- Comparar scripts vs estado operativo:
  - seeds
  - audits
  - readiness
  - deploy helpers

### Entregables

- Registro de discrepancias priorizado por severidad.
- Asignación por capa: backend, frontend, DB o tooling.

## Fase 2. Auditoría de Base de Datos

### Tareas

- Validar esquema real vs modelos.
- Detectar tablas legacy, columnas huérfanas y relaciones inconsistentes.
- Revisar constraints e índices.
- Confirmar que las migraciones sean reversibles.
- Confirmar que no haya tablas extra fuera de lo permitido.

### Criterios de cierre

- `scripts/audit_backend_schema.py` sin diferencias relevantes.
- Migraciones aplicadas y reversibles.
- No hay tablas legacy vivas.

## Fase 3. Auditoría de Backend

### Tareas

- Revisar routers y contratos públicos.
- Revisar CRUD, services y schemas.
- Revisar aislamiento por sede.
- Revisar soft deletes y timestamps.
- Revisar wrappers legacy y compatibilidad.
- Revisar cobertura de tests por módulo.

### Criterios de cierre

- Endpoints coherentes con schemas.
- CRUD y permisos alineados con contratos.
- Tests backend críticos verdes.

## Fase 4. Auditoría de Frontend

### Tareas

- Revisar rutas públicas.
- Revisar CMS y páginas públicas.
- Revisar hooks compartidos y tipos.
- Revisar parsing de contenido.
- Revisar componentes compartidos.
- Revisar e2e de rutas y contratos.

### Criterios de cierre

- Typecheck sin errores.
- E2E críticos verdes.
- Contratos públicos tipados.

## Fase 5. Auditoría de Scripts y Tooling

### Tareas

- Revisar seeds.
- Revisar audits.
- Revisar readiness.
- Revisar scripts de mantenimiento.
- Revisar helpers de deploy y backup.

### Criterios de cierre

- Scripts documentados y ejecutables.
- Gates alineados con el runtime real.
- No hay utilidades huérfanas o engañosas.

## Fase 6. Cierre de Discrepancias

### Orden recomendado

1. Corregir base de datos si el problema nace en el esquema.
2. Corregir backend si el problema nace en el contrato o la lógica.
3. Corregir frontend si el problema nace en consumo o renderizado.
4. Corregir scripts si el problema está en la operación o validación.

### Regla de ejecución

- Mantener cambios pequeños y reversibles.
- Agregar prueba o audit que pruebe la corrección.
- No mezclar capas innecesariamente.

## Fase 7. Validación Final

### Comandos de verificación

- `python3 -m pytest -q -o addopts='' ...` para backend y contratos.
- `cd frontend && npm run typecheck`.
- `cd frontend && vitest run ...` para contratos compartidos.
- `cd frontend && playwright test ...` para e2e críticos.
- `ENV_FILE=backend/.env python3 scripts/audit_backend_schema.py`.
- `python3 scripts/auditing/production_readiness.py`.

### Criterios de cierre

- Backend verde.
- Frontend verde.
- DB verde.
- Readiness en 100%.
- `git status --short` limpio.

## Fase 8. Documentación Final

### Entregables

- Resumen de hallazgos.
- Lista de correcciones aplicadas.
- Riesgos residuales.
- Pruebas ejecutadas.
- Estado final del workspace.

## Prompt de arranque para otro Codex

> Ejecuta la auditoría transversal del workspace de CCF siguiendo este orden:
> 1. inventario base
> 2. mapa de discrepancias
> 3. auditoría de base de datos
> 4. auditoría de backend
> 5. auditoría de frontend
> 6. auditoría de scripts y tooling
> 7. cierre de discrepancias por capa
> 8. validación final
> 9. documentación y cierre limpio
>
> Reglas:
> - No mezclar capas si se puede evitar.
> - Corregir con cambios pequeños y reversibles.
> - Cada corrección debe cerrar con test, audit o e2e.
> - No declarar éxito sin evidencia.

