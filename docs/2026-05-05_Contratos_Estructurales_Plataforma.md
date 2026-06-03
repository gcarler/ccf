# Contratos Estructurales de la Plataforma CCF

Fecha: 2026-05-05
Estado: Vigente
Objetivo: dejar reglas de arquitectura, dominio, contratos de rutas y gates de calidad para que cualquier agente o ingeniero trabaje sin reabrir decisiones ya cerradas.

## 1. Reglas duras

1. La plataforma trabaja con contratos nativos. No se crean aliases, rutas espejo ni capas de compatibilidad salvo instruccion explicita.
2. El frontend consume APIs bajo `/api/...`.
3. El backend expone un solo arbol canónico bajo `/api/...`.
4. `next build` no debe ignorar errores de TypeScript ni ESLint.
5. Produccion no puede arrancar con secretos triviales.
6. Los modulos se separan por dominio, no por conveniencia de pantalla.

## 2. Taxonomia de dominio

### CRM
Nombre funcional: Consolidacion.

Responsabilidad:
- miembros
- contactos/leads
- pipeline de consolidacion
- consejeria
- muro de oracion
- tareas de seguimiento
- mensajeria operativa
- configuracion de cargos de consolidacion

No pertenece a CRM:
- eventos
- estrategia Faro en Casa
- escaner y operacion de evangelismo como dominio principal

### Evangelismo
Responsabilidad:
- eventos
- asistencia persona-evento
- analitica de eventos
- roles operativos de eventos
- Faro en Casa
- temporadas y sesiones de Faro
- monitoreo de asistencia de Faro

### Workspace
Responsabilidad:
- configuracion de experiencia
- feature flags
- auditoria de flags
- incidentes de flags
- compliance de configuracion

Workspace no debe absorber reglas de otros dominios.

## 3. Contrato de rutas

### Backend canónico
- `/api/auth`
- `/api/crm`
- `/api/evangelism`
- `/api/workspace`
- `/api/academy`
- `/api/projects`
- `/api/admin`
- `/api/messaging`
- `/api/governance`

### Reglas
- No usar rutas en raiz tipo `/agents`, `/messaging`, `/governance`, `/auth`.
- Si una pantalla consume una ruta vieja, se corrige la pantalla o el test. No se reintroduce el alias.

## 4. Mapa estructural backend

### Ensamblaje
Archivo: [backend/app.py](</D:/ccf/backend/app.py>)

Regla:
- `backend/app.py` solo ensambla routers y middleware.
- El registro de routers vive en `ROUTER_REGISTRY`.
- No volver a registrar routers manualmente en bloques repetidos.

### Evangelismo
Archivos:
- [backend/api/evangelism.py](</D:/ccf/backend/api/evangelism.py>)
- [backend/api/evangelism_events.py](</D:/ccf/backend/api/evangelism_events.py>)
- [backend/api/evangelism_faro.py](</D:/ccf/backend/api/evangelism_faro.py>)
- [backend/api/evangelism_shared.py](</D:/ccf/backend/api/evangelism_shared.py>)

Contrato:
- `evangelism.py` es ensamblador del dominio y contiene solo los subdominios que aun no fueron extraidos.
- `evangelism_events.py` es la fuente de verdad para eventos, asistencia, roles, analytics y exportes.
- `evangelism_faro.py` es la fuente de verdad para casas, temporadas, sesiones, asistencia y monitoreo de Faro.
- `evangelism_shared.py` contiene helpers compartidos del dominio.

No duplicar helpers de audiencia, fechas o asistencia entre archivos.

### Workspace
Archivo actual:
- [backend/api/workspace.py](</D:/ccf/backend/api/workspace.py>)

Estado:
- sigue siendo un modulo concentrado.

Regla:
- cualquier trabajo nuevo debe tender a separarlo por subdominios:
  - config
  - flags
  - audit
  - incidents
  - compliance

No agregar nuevas responsabilidades fuera de esos subdominios.

## 5. Mapa estructural frontend

### Layout global
Archivo:
- [frontend/src/components/WorkspaceLayout.tsx](</D:/ccf/frontend/src/components/WorkspaceLayout.tsx>)

Regla:
- `WorkspaceLayout` contiene logica visual y de capa.
- no debe volver a contener el mapa completo de navegacion de modulos.

### Topologia de modulos
Archivo:
- [frontend/src/components/workspace/moduleConfigs.ts](</D:/ccf/frontend/src/components/workspace/moduleConfigs.ts>)

Contrato:
- este archivo es la fuente de verdad de la navegacion modular del sidebar principal.
- si se agrega un modulo o se cambia la taxonomia del sidebar, el cambio debe caer aqui.
- `WorkspaceLayout` solo importa y consume esta configuracion.

## 6. Contrato de datos ya fijado

### Persona y consolidacion
La persona base es `Member`.

Relaciones historicas ya introducidas:
- `positions`
- `member_positions`
- `consolidation_cases`
- `consolidation_assignments`
- `consolidation_interactions`
- `consolidation_follow_up_tasks`

Regla:
- no crear una entidad `Persona` paralela.
- la identidad base sigue siendo `Member`.

### Persona y evento
La relacion canonica es `event_attendances`.

Debe resolver:
- persona -> eventos
- evento -> personas

### Faro en Casa
El dominio Faro se apoya en:
- `grupos_evangelismo`
- `grupo_participantes`
- `sesiones_grupo`
- `asistencias`
- `faro_seasons`

Regla:
- un Faro puede existir con informacion parcial.
- lider, colider, anfitrion y miembros pueden completarse despues.

## 7. Contrato operativo de calidad

### Frontend
Deben pasar:
- `npm run typecheck`
- `npm run lint:strict`

`next.config.mjs` no debe usar:
- `ignoreDuringBuilds: true`
- `ignoreBuildErrors: true`

### Backend
Debe pasar:
- `python -m pytest -q`

### CI/CD
Los workflows deben dispararse cuando cambian:
- backend
- frontend
- workflows
- `alembic/`
- `alembic.ini`
- `requirements.txt`

## 8. Contrato de entorno

### Configuracion
Archivo:
- [backend/core/config.py](</D:/ccf/backend/core/config.py>)

Reglas:
- `environment` es el nombre canónico.
- `ENV` se acepta solo como alias de entrada.
- en `production`, `prod` o `staging`, `SECRET_KEY` debil debe fallar al iniciar.

### Docker compose
Archivo:
- [docker-compose.yml](</D:/ccf/docker-compose.yml>)

Reglas:
- no dejar secretos hardcodeados.
- usar variables obligatorias para `SECRET_KEY`, `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`.
- no usar `ENV: production`; usar `environment: production` dentro del bloque de variables del servicio backend.

## 9. Reglas para futuros cambios

1. Si un archivo de API supera de nuevo un umbral incomodo, extraer submodulo antes de seguir agregando endpoints.
2. Si una decision cambia taxonomia de dominio, actualizar este documento y `moduleConfigs.ts` en la misma entrega.
3. Si se crea una ruta nueva, debe entrar bajo `/api/<dominio>/...`.
4. Si un test depende de una ruta vieja, se corrige el test; no se recrea el alias.
5. Si un cambio toca despliegue o DB, revisar tambien:
   - [backend/core/config.py](</D:/ccf/backend/core/config.py>)
   - [docker-compose.yml](</D:/ccf/docker-compose.yml>)
   - [alembic/versions](</D:/ccf/alembic/versions>)

## 10. Deuda estructural pendiente

Pendiente principal:
- partir [backend/api/workspace.py](</D:/ccf/backend/api/workspace.py>) por subdominios reales.

Pendiente secundaria:
- seguir separando [backend/models.py](</D:/ccf/backend/models.py>) por ownership de dominio.
- revisar sidebars paralelos o duplicados en frontend y converger a una sola topologia por modulo donde aplique.

## 11. Regla de lectura para otro agente

Si otro agente entra al repo, debe leer primero:
1. este documento
2. [backend/app.py](</D:/ccf/backend/app.py>)
3. [frontend/src/components/workspace/moduleConfigs.ts](</D:/ccf/frontend/src/components/workspace/moduleConfigs.ts>)
4. [backend/core/config.py](</D:/ccf/backend/core/config.py>)

Con eso ya tiene el contrato base de dominio, rutas, estructura y despliegue.
