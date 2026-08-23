# Plan estructural de calidad e integración CCF

**Estado:** En ejecución  
**Fecha de inicio:** 2026-08-23  
**Propietario:** Equipo de desarrollo CCF  
**Rama de trabajo actual:** `integration/academy-public-courses-20260823-v2`

## 1. Objetivo

Construir un protocolo de calidad reproducible y aislado para que los tests
unitarios, las pruebas de integración, el backend y el frontend utilicen el
mismo entorno durante cada ejecución.

El objetivo es eliminar los falsos bloqueos causados por:

- SQLite vacía o desactualizada en worktrees temporales.
- API ejecutándose contra una base distinta a la usada por el script de calidad.
- Extensiones PostgreSQL ausentes, especialmente `citext`.
- Migraciones históricas incompatibles con SQLite.
- URLs y rutas fijadas a `/root/ccf` o `127.0.0.1:8000`.
- Suites modulares que modifican una base compartida.

## 2. Diagnóstico confirmado

### 2.1 Build frontend

`frontend/next.config.mjs` fijaba:

```text
/root/ccf/frontend
```

como `outputFileTracingRoot`. En un worktree temporal, Next mezclaba rutas y
artefactos de otro checkout. Esto provocaba que el staging `.next-build`
quedara incompleto y fallara al buscar `server/pages-manifest.json`.

Corrección aplicada en el commit `edb38bfb`:

```js
outputFileTracingRoot: process.env.OUTPUT_FILE_TRACING_ROOT || __dirname
```

Resultado: build exitoso, 223 páginas generadas.

### 2.2 Calidad de Projects

`test_projects_quality.py` escribía en la SQLite relativa al worktree, pero
sus llamadas HTTP estaban fijadas a `http://127.0.0.1:8000`. El script creaba
datos en una base y consultaba otra.

Al usar PostgreSQL compartido, la prueba funcional pasó con `48 passed, 0
failed`, confirmando que el fallo era de entorno y no del módulo Projects.

### 2.3 Calidad de Academia

El problema también era de entorno: la suite no tenía un PostgreSQL aislado,
fixtures de identidad ni un contrato común con la API. Con el provisionador y
los fixtures estructurales, la suite pasó completa sobre la misma base y API.

Resultado validado el 2026-08-23:

```text
QUALITY_RC=0
RESUMEN: 9/9 suites OK — ALL GREEN
70 + 28 + 18 + 39 + 33 + 27 + 19 tests passed
2 gated tests skipped por no tener credenciales E2E/a11y
```

## 3. Arquitectura objetivo

```text
Runner de calidad
       |
       +--> crea DB PostgreSQL temporal por ejecución
       |       +--> habilita extensiones requeridas
       |       +--> aplica baseline canónico y registra head
       |       +--> carga fixtures versionados
       |
       +--> levanta backend con QUALITY_DATABASE_URL
       |
       +--> ejecuta tests y suites contra QUALITY_API_URL
       |
       +--> ejecuta build frontend aislado
       |
       +--> recoge reportes
       |
       +--> apaga backend y elimina DB temporal
```

Regla fundamental: ningún test de integración puede escribir en la base de
desarrollo, staging o producción por defecto.

## 4. Plan de implementación

### Fase 1 — Contrato único de entorno

- [x] Crear variables explícitas:
  - `QUALITY_DATABASE_URL`
  - `QUALITY_API_URL`
  - `QUALITY_ENVIRONMENT`
  - `QUALITY_RUN_ID`
- [x] Rechazar ejecución si faltan API, base o identificador de ejecución.
- [x] Eliminar URLs hardcodeadas de `test_projects_quality.py`.
- [x] Hacer que los scripts resuelvan el root desde el worktree activo.
- [x] Documentar el contrato en este plan y centralizarlo en
  `scripts/quality_environment.py`.

### Fase 2 — Base temporal PostgreSQL

- [x] Crear `scripts/provision_quality_database.py` para una base aislada.
- [x] Habilitar `citext` y `pgcrypto` durante el provisionamiento.
- [x] Aplicar el baseline canónico y registrar el `head` en la base nueva.
- [x] Validar `alembic_version`, ampliar su capacidad para revisiones canónicas
  largas y rechazar la base si falta.
- [x] No usar `Base.metadata.create_all()` como sustituto de migraciones.
- [ ] Destruir la base al finalizar, incluso si una suite falla.

### Fase 3 — Fixtures idempotentes

- [x] Crear fixtures reproducibles para identidad, sede y roles requeridos.
- [x] Usar un `QUALITY_RUN_ID` para identificar la ejecución.
- [x] Mantener los fixtures dentro de una base temporal exclusiva por ejecución.
- [ ] Limpiar por `QUALITY_RUN_ID` en un bloque `finally`.
- [x] No borrar datos que no pertenezcan a la ejecución actual.

### Fase 4 — Runner de integración

- [x] Crear `scripts/run_quality_integration.py` como ejecutor único de suites.
- [ ] Integrar provisionamiento, migración y levantamiento de API en un comando
  totalmente orquestado.
- [x] Validar PostgreSQL, extensiones, `alembic_version` y `/openapi.json`
  antes de ejecutar las suites.
- [x] Permitir reintento de red mediante evidencia temporal exacta de
  rama/SHA/base, sin repetir ni omitir el gate.
- [ ] Esperar `/healthz` antes de ejecutar suites HTTP.
- [ ] Pasar la misma configuración al backend y a cada script.
- [ ] Guardar logs separados por suite.
- [ ] Devolver código de salida determinista.
- [ ] Ejecutar el build frontend en un worktree/distDir aislado.

### Fase 5 — Suites modulares

- [x] Adaptar `test_projects_quality.py` a `QUALITY_API_URL`.
- [x] Adaptar `test_academy_quality.py` al contrato del runner.
- [ ] Revisar cada suite que use `SessionLocal` directamente.
- [ ] Separar pruebas de API, pruebas de base y pruebas E2E.
- [ ] Evitar que un cambio de configuración compartida active suites ajenas
  cuando el selector no detecte una dependencia real.
- [ ] Mantener el gate estricto: una suite roja bloquea el push.

### Fase 6 — Integración y publicación

- [x] Ejecutar el runner completo sobre la rama temporal basada en el
  `origin/main` más reciente.
- [x] Ejecutar contrato de rama, lint, pruebas, suites modulares y build.
- [x] Publicar únicamente la rama temporal.
- [x] Confirmar el SHA remoto validado (`13c08ae866b8e67bdcce5c02e14f1c3ddde2b3ab`).
- [ ] Fusionar la rama temporal a `main`.
- [ ] Ejecutar smoke post-merge.
- [ ] Archivar la rama bajo `archive/merged/` después de confirmar la fusión.

## 5. Criterios de aceptación

El plan se considera completado cuando:

- Una ejecución desde cualquier worktree produce el mismo resultado.
- Ninguna suite depende de `/root/ccf`, una SQLite accidental o una URL fija.
- El backend y las pruebas HTTP usan la misma base temporal.
- Las migraciones y extensiones requeridas se validan automáticamente.
- Las suites de Academia y Projects pasan sin intervención manual.
- El build staging genera todos sus manifiestos y artefactos.
- El pre-push publica únicamente una rama limpia y validada.
- El proceso puede repetirse sin dejar datos ni locks residuales.

## 6. Estado actual

- **Build seguro:** corregido y validado.
- **Integración sobre `origin/main` actual:** realizada en la rama temporal.
- **Projects:** validado con PostgreSQL y API coherentes (`49 passed`).
- **Academia:** validado sobre base PostgreSQL y API coherentes (`9/9 suites
  OK`, `234 passed`, `2 skipped` gated).
- **Provisionamiento:** baseline canónico, extensiones y fixtures reproducibles
  validados en `ccf_quality_20260823`.
- **Push:** publicado después de pasar contrato, lint, pruebas, suites
  modulares y build; el hook confirmó el SHA remoto
  `13c08ae866b8e67bdcce5c02e14f1c3ddde2b3ab`.
- **Selector:** `frontend/next.config.mjs` ya no escala artificialmente a
  todos los módulos; selecciona build frontend y conserva los propietarios
  reales del diff.
- **Sincronización:** la rama fue rebasada y validada sobre el `origin/main`
  más reciente disponible (`38f10526`).
- **Merge a `main`:** pendiente de esa nueva sincronización y validación.

## 7. Regla de trabajo para futuras sesiones

Antes de modificar código, consultar este documento y actualizar la sección
`Estado actual`. Cada fase debe cerrar con evidencia: comando ejecutado,
resultado y artefactos generados.

## 8. Plan operativo vigente: cierre de los bloqueos de CI

### Diagnóstico de la ejecución oficial

La primera ejecución del PR #13 no falló por la funcionalidad pública de
Academia. Falló por tres dependencias estructurales del proceso:

1. El baseline canónico usaba columnas `CITEXT`, pero la creación de la
   extensión solo estaba en el provisionador local. Una instalación limpia de
   CI no podía ejecutar las migraciones.
2. El gate backend encontró cinco errores Ruff reproducibles en archivos del
   backend. Aunque eran preexistentes, bloqueaban correctamente la publicación
   y debían corregirse en origen.
3. El detector de `any` del frontend suponía que siempre existiría el ref
   `origin/main`. El checkout del CI solo garantizaba el ref local `main`, por
   lo que el detector fallaba antes de analizar los archivos.

### Correcciones estructurales en curso

- [x] Hacer que el baseline cree `citext` y `pgcrypto` en PostgreSQL antes de
  construir el esquema.
- [x] Corregir los cinco hallazgos Ruff sin silenciar el linter ni ampliar su
  exclusión:
  - imports desordenados en tres módulos de Evangelismo;
  - variable de evento no utilizada en check-in;
  - filtro de sede no utilizado en dashboard.
- [x] Hacer que el detector frontend resuelva `origin/main` o `main` según el
  ref disponible en el checkout.
- [ ] Ejecutar validación local específica y el runner completo de calidad.
- [ ] Crear un commit exclusivo de estas correcciones.
- [ ] Actualizar la rama temporal con `--force-with-lease` solo si el rebase
  cambia su historial; nunca usar `--no-verify`.
- [ ] Esperar el resultado completo del PR #13 y corregir únicamente fallos
  reproducibles.

### Secuencia obligatoria de integración

```text
correcciones estructurales
        ↓
lint + pruebas focalizadas
        ↓
runner completo + build
        ↓
push únicamente de integration/academy-public-courses-20260823-v2
        ↓
CI verde del PR #13
        ↓
merge a main
        ↓
smoke post-merge sobre main
        ↓
archive/merged/integration-academy-public-courses-20260823-v2
```

### Regla de ramas

`main` es la única rama canónica y estable. Cada módulo conserva su rama de
trabajo. Los cambios transversales de calidad se mantienen en la rama
temporal de integración hasta que el PR sea verde. No se mezclan ramas con
conflictos a la fuerza ni se publica directamente sobre `main`.

### Evidencia pendiente de cierre

- Commit de remediación del CI.
- SHA remoto validado después de la remediación.
- Resultado verde de todos los checks del PR #13.
- SHA de `main` posterior al merge.
- Smoke post-merge y confirmación de que la rama archivada conserva el mismo
  historial.
