# Plan De Superestructura Rigurosa - CCF

Fecha: 2026-05-01
Base analizada: `D:\ccf`
Objetivo: estabilizar, ordenar y endurecer la plataforma CCF hasta dejarla en una condicion operable de produccion, con arquitectura mantenible, controles verificables y deuda tecnica bajo gobierno.

## 1. Dictamen Base

CCF ya tiene una base tecnica seria:

- Frontend `Next.js 15` + `TypeScript` + `Tailwind` + `Storybook` + `Playwright`.
- Backend `FastAPI` + `SQLAlchemy` + `Alembic`.
- Infraestructura definida con `Postgres`, `Redis`, `Redpanda`, `MinIO`, backend y frontend en Docker.
- Cobertura de pruebas backend y frontend ya existente.

CCF no esta estructuralmente listo para considerarse estable por estas razones:

- `frontend` no pasa `typecheck`.
- `frontend` tiene un `lint` inutilizable por mezcla de deuda real con artefactos generados.
- `pytest` queda en `24 passed, 1 error`, con fallo operativo en temporales/cache.
- El repo mezcla codigo fuente con logs, backups, bases de datos, builds y reportes.
- El backend concentra demasiado montaje y responsabilidad en archivos raiz.
- Persisten configuraciones inseguras para un entorno no local.

## 2. Principios De Ejecucion

1. No mezclar estabilizacion con expansion funcional.
2. No atacar deuda masiva sin antes separar ruido de deuda real.
3. Cada fase debe cerrar con evidencia ejecutable.
4. Ninguna refactorizacion estructural se hace si el baseline no esta verde.
5. Todo cambio de arquitectura debe dejar una frontera de dominio mas clara que la anterior.

## 3. Criterios De Exito Final

La fase de superestructura se considera cerrada cuando se cumplan todos estos puntos:

- `frontend`: `typecheck`, `lint`, `build`, `test` en verde.
- `backend`: `pytest` en verde sin hacks manuales fuera del repo.
- CI reproducible con gates bloqueantes coherentes.
- `.gitignore` y estructura del repo limpios de artefactos operativos.
- Dominios backend y frontend con ownership mas claro.
- Seguridad minima endurecida: secretos, CORS, errores, expiraciones, defaults.
- Documentacion operativa actualizada con runbooks y politica de calidad.

## 4. Secuencia Maestra

La ejecucion correcta es esta y no otra:

1. Baseline y congelamiento.
2. Estabilizacion critica del frontend.
3. Estabilizacion operativa del backend.
4. Limpieza de repo y herramientas.
5. Modularizacion backend.
6. Modularizacion frontend.
7. Hardening de seguridad e infraestructura.
8. Cierre de CI/CD y gobernanza.

## 5. Fase 0 - Baseline Y Congelamiento

Duracion objetivo: 0.5 a 1 dia.

### Objetivo

Congelar el punto de partida, distinguir cambios funcionales del usuario frente a cambios de estabilizacion y fijar el contrato de salida.

### Entregables

- Snapshot del estado actual de git.
- Registro de fallos actuales en `typecheck`, `lint`, `pytest`.
- Lista de archivos sucios fuera del scope de estabilizacion.
- Documento de baseline con fecha.

### Tareas

- Registrar `git status --short`.
- Registrar comandos base y resultados.
- Identificar archivos modificados por el usuario que no deben tocarse.
- Abrir rama de trabajo de estabilizacion.

### Gate de salida

- Baseline guardado.
- Scope tecnico separado de cambios funcionales en curso.

## 6. Fase 1 - Estabilizacion Critica Del Frontend

Duracion objetivo: 1 a 2 dias.
Prioridad: maxima.

### Objetivo

Recuperar la capacidad de compilar el frontend y convertir el lint en una señal util.

### Entregables

- `npm.cmd run typecheck` en verde.
- `eslint` apuntando solo a codigo fuente relevante.
- inventario de deuda real de lint por modulo.

### Tareas

#### 1. TypeScript

- Corregir el fallo actual en [page.tsx](</D:/ccf/frontend/src/app/(public)/faro/eventos/page.tsx:430>).
- Revisar si el error proviene de union types mal inferidos o de datos heterogeneos sin contrato tipado.
- Formalizar tipos para calendarios, eventos y vistas FARO publicas.

#### 2. Higiene de lint

- Excluir de ESLint:
  - `storybook-static`
  - `.next`
  - `playwright-report`
  - `test-results`
  - `*.bak`
  - `*.tsbuildinfo`
  - scripts de parche temporal
- Revisar [tsconfig.json](</D:/ccf/frontend/tsconfig.json>) para que el alcance de lint y typecheck no arrastre basura de tooling.
- Crear baseline de deuda real por carpeta:
  - `src/app`
  - `src/components`
  - `src/lib`
  - `tests`

#### 3. Deuda real

- Eliminar errores triviales:
  - imports no usados
  - variables muertas
  - hooks condicionales
- Clasificar deuda restante:
  - bloqueante
  - importante
  - cosmética

### Gate de salida

- `npm.cmd run typecheck` pasa.
- `npm.cmd run lint` ejecuta solo sobre codigo objetivo.
- deuda de lint clasificada por modulo.

## 7. Fase 2 - Estabilizacion Operativa Del Backend

Duracion objetivo: 1 a 2 dias.
Prioridad: maxima.

### Objetivo

Dejar el backend verificable, con pruebas reproducibles y sin dependencias de comportamiento accidental del entorno Windows.

### Entregables

- `pytest` en verde.
- politica estable de temporales/cache.
- estrategia clara de startup y migraciones.

### Tareas

#### 1. Pytest y filesystem

- Corregir el fallo de permisos en carpetas temporales.
- Configurar `basetemp` controlado dentro del workspace o ruta segura.
- Limpiar conflictos en `.pytest_cache`.

#### 2. Ciclo de vida FastAPI

- Migrar `@app.on_event("startup")` y `@app.on_event("shutdown")` a lifespan.
- Mantener semantica actual de inicializacion sin romper arranque.

#### 3. Migraciones

- Revisar superposicion entre Alembic y `_run_startup_migrations()` en [app.py](</D:/ccf/backend/app.py:57>).
- Decidir politica:
  - opcion A: Alembic como unica fuente de verdad.
  - opcion B: startup migrations limitadas y documentadas para bootstrap no destructivo.
- Recomendada: Alembic como fuente principal, startup migrations solo para bootstraps idempotentes de contenido tecnico.

### Gate de salida

- `python -m pytest` pasa limpio.
- arranque backend sin deprecations criticas pendientes.
- migraciones con criterio unico documentado.

## 8. Fase 3 - Limpieza Del Repositorio Y Herramientas

Duracion objetivo: 1 dia.

### Objetivo

Separar claramente codigo fuente de residuos operativos y evitar que tooling, git y CI analicen archivos incorrectos.

### Entregables

- `.gitignore` raiz saneado.
- `.gitignore` frontend saneado.
- artefactos fuera del scope del control de cambios.

### Tareas

- Ignorar o mover:
  - `*.db`
  - `*.db.bak`
  - `*_BACKUP.db`
  - `*.log`
  - `*.tsbuildinfo`
  - `__pycache__`
  - `.pytest_cache`
  - `storybook-static`
  - `playwright-report`
  - `test-results`
  - reportes de lighthouse/eslint temporales
- Revisar archivos como:
  - `frontend/src/app/admin/settings/system/page.tsx.bak`
  - `frontend/src/components/WorkspaceMainSidebar.tsx.bak`
  - scripts tipo `patch_nav.js`, `patch_popup.js`

### Gate de salida

- `git status` deja de mezclar fuentes con residuos.
- lint, tests y CI no inspeccionan salidas generadas.

## 9. Fase 4 - Modularizacion Del Backend

Duracion objetivo: 3 a 5 dias.
Prioridad: alta.

### Objetivo

Reducir concentracion estructural, mover responsabilidades a dominios y preparar el backend para crecimiento controlado.

### Problemas actuales

- [app.py](</D:/ccf/backend/app.py>) monta demasiados routers y contiene logica operativa.
- [crud.py](</D:/ccf/backend/crud.py>) concentra demasiada logica transversal.
- [models.py](</D:/ccf/backend/models.py>) crece como archivo monolitico.

### Entregables

- bootstrap backend mas delgado.
- servicios y CRUD por dominio.
- boundaries backend documentadas.

### Propuesta

Estructura objetivo:

- `backend/domains/auth`
- `backend/domains/academy`
- `backend/domains/crm`
- `backend/domains/cms`
- `backend/domains/finance`
- `backend/domains/governance`
- `backend/domains/messaging`
- `backend/domains/support`
- `backend/domains/spiritual_life`
- `backend/platform`

### Tareas

- Extraer router registration a un modulo central.
- Dividir `crud.py` por dominio, empezando por los mas grandes.
- Mover servicios compartidos reales a `platform` o `core`, no a `crud`.
- Reducir dependencia circular entre modelos.

### Gate de salida

- `app.py` queda como bootstrap, no como centro de negocio.
- `crud.py` deja de ser archivo tractor.
- dominio critico extraido sin regresion de pruebas.

## 10. Fase 5 - Modularizacion Del Frontend

Duracion objetivo: 3 a 5 dias.
Prioridad: alta.

### Objetivo

Separar verticalmente experiencia publica FARO, workspace interno y modulos funcionales, reduciendo paginas gigantes y acoplamientos difusos.

### Problemas actuales

- App Router con muchas rutas, pero sin feature boundaries suficientemente explicitas.
- componentes y paginas grandes mezclan layout, data access y rendering.
- coexistencia de experiencia publica, CMS y workspace interno dentro del mismo arbol sin disciplina fuerte de ownership.

### Entregables

- frontend orientado a features.
- componentes de presentacion mas puros.
- data fetching y UI desacoplados.

### Propuesta

Estructura objetivo:

- `src/features/public-site`
- `src/features/cms`
- `src/features/academy`
- `src/features/crm`
- `src/features/projects`
- `src/features/finance`
- `src/features/workspace`
- `src/shared/ui`
- `src/shared/lib`

### Tareas

- extraer paginas de alto tamano a componentes por seccion.
- mover acceso a datos a servicios o hooks por feature.
- consolidar componentes compartidos en `shared/ui`.
- preservar `WorkspaceLayout` como contrato de shell interno.

### Gate de salida

- las paginas grandes quedan troceadas sin cambio de comportamiento.
- ownership frontend por feature queda evidente.

## 11. Fase 6 - Seguridad E Infraestructura

Duracion objetivo: 2 a 3 dias.
Prioridad: alta.

### Objetivo

Cerrar defaults inseguros y alinear configuracion local, staging y produccion con un minimo serio de seguridad operativa.

### Hallazgos a cerrar

- secretos por defecto (`changeme`, `change-me`, credenciales triviales).
- CORS abierto en [app.py](</D:/ccf/backend/app.py:43>).
- trazas expuestas en respuesta 500.
- expiraciones de tokens demasiado largas en [config.py](</D:/ccf/backend/core/config.py:13>).

### Entregables

- configuracion segura por entorno.
- fallos 500 sin detalles internos al cliente.
- CORS parametrizado.
- secretos obligatorios en staging/produccion.

### Tareas

- endurecer `Settings`.
- exigir `SECRET_KEY` real fuera de local.
- mover origins permitidos a config por entorno.
- eliminar `trace` del payload de error al cliente.
- revisar cookies, expiraciones y refresh policy.

### Gate de salida

- staging y prod no arrancan con defaults inseguros.
- backend no expone detalles internos en errores.

## 12. Fase 7 - CI/CD Y Quality Gates

Duracion objetivo: 2 a 3 dias.

### Objetivo

Convertir el pipeline en un filtro real de calidad y no solo en una secuencia de comandos.

### Entregables

- pipeline coherente con el estado real del repo.
- gates bloqueantes y gates advisory bien definidos.
- evidencia automatizada de build, pruebas y calidad.

### Gates propuestos

- bloqueantes:
  - `frontend typecheck`
  - `frontend build`
  - `backend pytest`
  - `frontend lint` sobre scope saneado
- advisory:
  - `lint:strict` mientras se cierra deuda historica
  - Lighthouse comparativo
  - reportes de cobertura visual

### Tareas

- alinear workflow de CI con scripts finales.
- publicar artefactos utiles, no basura.
- separar pipeline de estabilizacion y pipeline de producto si hace falta.

### Gate de salida

- CI falla por problemas reales, no por configuracion defectuosa.

## 13. Fase 8 - Gobernanza Tecnica

Duracion objetivo: continua.

### Objetivo

Evitar recaida del repo y establecer disciplina minima de evolucion.

### Entregables

- politica de carpetas temporales y artefactos.
- politica de naming y ownership por feature.
- checklist de PR tecnico.
- runbook de salida a staging.

### Reglas propuestas

- no versionar bases, logs, reportes o caches.
- no introducir scripts de parche temporal en la raiz sin clasificacion.
- todo modulo nuevo debe nacer con:
  - contrato de datos
  - test minimo
  - ubicacion de ownership
- toda vista grande debe separar:
  - shell
  - data
  - rendering

## 14. Riesgos Reales

### Riesgos tecnicos

- refactorizacion simultanea de frontend y backend puede bloquear release si se hace en paralelo.
- mezcla de cambios funcionales con cambios estructurales puede generar conflictos de git innecesarios.
- mantener SQLite y Postgres a la vez sin una politica clara puede introducir comportamiento divergente.

### Riesgos operativos

- lint estricto total antes de limpiar scope solo produce ruido y fatiga.
- migraciones de backend sin disciplina unica pueden romper staging silenciosamente.

### Mitigacion

- avanzar en ramas cortas por fase.
- validar cada fase con comandos repetibles.
- no tocar dominios no estabilizados durante el baseline.

## 15. KPIs De Seguimiento

- `frontend typecheck`: 0 errores.
- `frontend lint`: 0 errores dentro del scope saneado.
- `backend pytest`: 100% verde.
- tiempo medio de CI: menor a 12 minutos.
- numero de artefactos versionados indebidos: 0.
- numero de archivos monoliticos prioritarios reducidos:
  - `crud.py`
  - `models.py`
  - paginas frontend > 800 lineas.

## 16. Orden De Ejecucion Inmediato Recomendado

Sprint 1:

1. Corregir `typecheck` frontend.
2. Sanear scope de ESLint.
3. Hacer pasar `pytest`.
4. Limpiar `.gitignore` y artefactos.

Sprint 2:

1. endurecer configuracion backend.
2. modularizar bootstrap backend.
3. extraer primer dominio de `crud.py`.

Sprint 3:

1. modularizar paginas grandes del frontend.
2. consolidar `shared/ui` y features.
3. cerrar gates definitivos de CI.

## 17. Decision Ejecutiva

La mejor ruta no es expandir nuevas vistas ahora. La mejor ruta es estabilizar la superestructura primero, porque el proyecto ya tiene suficiente masa critica como para que cada nueva funcionalidad aumente la deuda estructural de forma no lineal.

Si esta hoja de ruta se sigue en orden, CCF puede pasar de plataforma funcional con deuda visible a plataforma gobernable, verificable y preparada para escalar.
