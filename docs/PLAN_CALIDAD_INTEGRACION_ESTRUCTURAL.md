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

La suite aún reporta fallos cuando se ejecuta sobre el entorno compartido.
Antes de corregir código, hay que obtener el detalle completo de esos fallos
y clasificarlos como:

1. Contrato roto del módulo.
2. Fixture o seed incompleto.
3. Migración o extensión ausente.
4. API y base desalineadas.

No se debe publicar ignorando esos resultados.

## 3. Arquitectura objetivo

```text
Runner de calidad
       |
       +--> crea DB PostgreSQL temporal por ejecución
       |       +--> habilita extensiones requeridas
       |       +--> ejecuta alembic upgrade head
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
- [ ] Ejecutar `alembic upgrade head` sobre la base nueva.
- [ ] Rechazar bases con `alembic_version` ausente o desactualizada.
- [ ] No usar `Base.metadata.create_all()` como sustituto de migraciones.
- [ ] Destruir la base al finalizar, incluso si una suite falla.

### Fase 3 — Fixtures idempotentes

- [ ] Crear fixtures versionados para identidad, sede, roles y Academia.
- [ ] Usar un `QUALITY_RUN_ID` para aislar registros de cada ejecución.
- [ ] Evitar correos y nombres fijos compartidos entre ejecuciones.
- [ ] Limpiar por `QUALITY_RUN_ID` en un bloque `finally`.
- [ ] No borrar datos que no pertenezcan a la ejecución actual.

### Fase 4 — Runner de integración

- [x] Crear `scripts/run_quality_integration.py` como ejecutor único de suites.
- [ ] Integrar provisionamiento, migración y levantamiento de API en un comando
  orquestado.
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

- [ ] Ejecutar el runner completo sobre la rama temporal basada en el
  `origin/main` más reciente.
- [ ] Ejecutar contrato de rama, lint, pruebas, suites modulares y build.
- [ ] Publicar únicamente la rama temporal.
- [ ] Confirmar el SHA remoto.
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
- **Projects:** validado con PostgreSQL y API coherentes (`48 passed`).
- **Academia:** el runner ahora bloquea ambientes sin contrato; falta ejecutar
  la suite sobre una base temporal provisionada.
- **Push:** bloqueado correctamente por el gate de calidad.
- **Merge a `main`:** pendiente del push validado.

## 7. Regla de trabajo para futuras sesiones

Antes de modificar código, consultar este documento y actualizar la sección
`Estado actual`. Cada fase debe cerrar con evidencia: comando ejecutado,
resultado y artefactos generados.
