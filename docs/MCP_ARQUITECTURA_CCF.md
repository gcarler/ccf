# MCP de la plataforma CCF

**Estado:** catálogo MCP completo para 32 módulos, más gateway de descubrimiento
**Fecha de verificación:** 20 de agosto de 2026
**Fuente de verdad:** `backend/mcp_public.py`, `backend/mcp_auth.py`, `backend/mcp_evangelism.py`, `backend/mcp_crm.py`, `backend/mcp_academy.py` y `backend/mcp_agenda.py`.

## 1. Propósito

CCF expone herramientas mediante **Model Context Protocol (MCP)** para que
clientes compatibles puedan consultar o ejecutar operaciones de la plataforma.
MCP no reemplaza la API REST: es una capa de herramientas para agentes que debe
reutilizar las mismas reglas de identidad, permisos, negocio y multi-sede.

La regla principal es:

```text
MCP = contrato de agente
     + JWT de Auth v3
     + RBAC canónico
     + aislamiento por sede
     + herramientas limitadas al dominio
```

No se debe crear una segunda identidad, una segunda matriz de permisos ni una
consulta MCP que salte los servicios y restricciones del dominio.

## 2. Superficies actuales

| Superficie | Ruta | Autenticación | Alcance |
|---|---|---|---|
| Gateway de módulos | `/mcp/platform` | `Authorization: Bearer <JWT>` | Catálogo y descubrimiento de los 32 módulos |
| Contenido público | `/mcp` | Sin JWT de usuario | Solo CMS publicado; lectura |
| CMS privado | `/mcp/cms` | `Authorization: Bearer <JWT>` | Gestión de páginas, secciones y workflow editorial |
| Evangelismo privado | `/mcp/evangelism` | `Authorization: Bearer <JWT>` | Estrategias, grupos, sesiones, eventos y asistencia de la sede |
| CRM privado | `/mcp/crm` | `Authorization: Bearer <JWT>` | Personas, casos, tareas, pipeline, automatizaciones, eventos y asistencia |
| Academia privada | `/mcp/academy` | `Authorization: Bearer <JWT>` | Cursos, lecciones, inscripciones, estudiantes y asistencia académica |
| Calendario privado | `/mcp/calendar` | `Authorization: Bearer <JWT>` | Eventos de agenda, recursos, participantes y reservas |
| Módulos restantes | `/mcp/{modulo}` | `Authorization: Bearer <JWT>` | Proxy REST allowlisted con RBAC del módulo |

El MCP público no permite mutaciones. Las superficies privadas usan el mismo
middleware JWT/RBAC y sesiones MCP independientes. El gateway genérico no acepta
URLs arbitrarias: cada módulo declara prefijos REST permitidos y el método HTTP
determina si se exige permiso de lectura o escritura.

El catálogo incluye Auth, Proyectos, Kernel, Servicios públicos, Workspace,
Sistema, Agentes, Administración, Finanzas, Suite financiera, Donaciones,
Gobernanza, Chat, Mensajería, Soporte, Base de conocimiento, Vida espiritual,
Graph, Comunidad, Oración, Analítica, Dashboards, Tablas, YouTube, Enterprise
CMS, Wiki, Comentarios, CMS, Evangelismo, CRM, Academia y Calendario.

Los módulos con herramientas especializadas son CMS, Evangelismo, CRM,
Academia y Calendario. Los demás se conectan mediante el contrato estándar de
`backend/mcp_platform.py`, que permite invocar sus endpoints REST canónicos sin
duplicar reglas de dominio.

El montaje privado aparece antes de `/mcp` en `backend/app.py`. Esto es
obligatorio porque el montaje público `/mcp` es un prefijo amplio y, si se
registrara primero, capturaría también `/mcp/evangelism`.

## 3. Autenticación privada

El MCP privado reutiliza el access JWT emitido por Auth v3:

```http
Authorization: Bearer <access_token>
```

`backend/mcp_auth.py` implementa un `TokenVerifier` que:

1. valida la firma y expiración con `SECRET_KEY` y HS256;
2. resuelve `sub` contra `auth_users.id`;
3. exige que el usuario esté activo;
4. calcula sus permisos efectivos con `get_user_effective_permissions`;
5. entrega al SDK MCP scopes derivadas de la taxonomía CCF.

El servidor no usa refresh tokens como credenciales MCP. Cuando el access token
vence, el cliente debe obtener otro mediante el flujo normal de Auth v3.

### 3.1 Scopes y permisos

Las herramientas vuelven a validar el permiso en cada operación:

| Operación | Permiso mínimo |
|---|---|
| Leer estrategias, grupos, sesiones, eventos y personas | `evangelism:read` |
| Crear, editar o archivar estrategias y grupos | `evangelism:manage` |
| Resolver o crear evento de estrategia | `evangelism:manage` |
| Consultar asistencia y reportes | `evangelism:read` |
| Registrar asistencia | `evangelism:edit` |
| Leer personas, casos, tareas, pipeline y eventos CRM | `crm:read` |
| Crear o editar personas, casos, tareas y asistencia CRM | `crm:edit` |
| Gestionar pipeline, etapas y automatizaciones CRM | `crm:manage` |
| Leer cursos y lecciones académicas | `academy:read` |
| Inscribirse y consultar progreso propio | `academy:study` |
| Crear o editar cursos y lecciones | `academy:edit` |
| Archivar cursos y administrar estudiantes/asistencia | `academy:manage` / `academy:edit` |
| Leer agenda, recursos, participantes y reservas | `spiritual_life:read` |
| Crear, editar o archivar agenda y reservas | `spiritual_life:edit` |

La jerarquía sigue la de REST: `manage` incluye `edit` y `read`. Los roles
`admin`/`pastor` conservan el acceso completo a evangelismo y `coordinador`
recibe lectura y operación, pero no gestión salvo permiso explícito.

## 4. Aislamiento por sede

Toda herramienta privada resuelve la sede mediante
`require_user_sede_id(db, user)` y nunca acepta `sede_id` como argumento del
cliente. En eventos masivos se comprueban ambas relaciones:

```text
usuario autenticado → sede del usuario
                         │
                         ├── evento.sede_id
                         └── persona.sede_id
```

Una persona de otra sede no puede ser seleccionada para asistencia. Los eventos
fuera de la sede se comportan como inexistentes para el MCP.

## 5. Contrato de eventos masivos

Los eventos masivos se identifican por el vínculo creado en `settings_json`:

```json
{
  "evangelism_strategy_id": "<uuid>",
  "strategy_typology": "evento_masivo"
}
```

No requieren `GrupoEvangelismo`, `SesionGrupo` ni participantes de grupo. La
asistencia usa la clave única de `EventAttendance`:

```text
(event_id, session_date, persona_id)
```

### Herramientas

#### `list_mass_events`

Lista eventos masivos activos de la sede, con paginación `limit`/`offset`.

#### `ensure_mass_event`

Recibe `strategy_id`, exige `evangelism:manage` y obtiene o crea de forma
perezosa el `CrmEvent` asociado a una estrategia cuya tipología sea exactamente
`evento_masivo`. No crea grupos.

#### `search_mass_event_people`

Recibe `event_id`, texto de búsqueda y límite. Solo devuelve personas de la
sede del evento y campos necesarios para identificar la selección: UUID, nombre,
rol, correo y teléfono.

#### `get_mass_event_attendance`

Recibe `event_id` y `session_date`; devuelve presentes, ausentes y contadores
para esa fecha. Los registros de asistencia ausente se conservan para historial,
pero se reportan como ausentes.

#### `register_mass_event_attendance`

Recibe `event_id`, `session_date` y la lista de `persona_ids` presentes. La
operación sincroniza esa fecha: las filas existentes no incluidas pasan a
`absent` y las seleccionadas a `present`.

Por seguridad de agentes:

- máximo de 2.000 personas por operación;
- una lista vacía requiere `allow_empty=true` explícito;
- personas inexistentes o de otra sede rechazan la operación completa;
- eventos cancelados o con asistencia cerrada rechazan la operación;
- la fuente persistida de esta superficie es `mcp`;
- la operación es idempotente por la restricción única de asistencia.

## 6. Gestión privada del CMS

`/mcp/cms` reutiliza el JWT CCF, el permiso `cms:edit`, el aislamiento de
sitio y las funciones CRUD/workflow del CMS. Sus herramientas permiten listar
páginas por estado, crear borradores, editar metadatos, gestionar secciones y
ejecutar acciones del workflow. Crear siempre produce un borrador. Las acciones
`publish`, `approve`, `unpublish` y `archive` requieren además los roles
publicadores definidos por CMS.

No se acepta un token como argumento de una herramienta: la credencial siempre
viaja en `Authorization: Bearer`.

## 7. Contrato del MCP CRM

`/mcp/crm` es una superficie privada separada de Evangelismo. Sus grupos de
herramientas son:

- **Personas:** búsqueda, lectura no sensible, creación, actualización y archivo
  lógico usando `personas.id`.
- **Casos:** listado, detalle, creación, actualización, archivo e interacciones.
- **Tareas:** creación, consulta y actualización con los catálogos de estado y
  prioridad del CRM.
- **Pipeline:** lectura y administración de pipelines y etapas.
- **Automatizaciones:** creación de flujos y validación de grafos sin ciclos.
- **Eventos:** listado, detalle, creación, actualización, archivo y asistencia.

Las respuestas de personas no incluyen notas pastorales ni datos médicos. Las
operaciones que afectan casos, tareas, pipeline, automatizaciones o eventos
reutilizan los handlers/CRUD existentes cuando el contrato canónico lo permite.
La asistencia de eventos usa `EventAttendance` y el mismo aislamiento por sede;
una selección vacía exige confirmación explícita (`allow_empty=true`).

## 8. Contrato del MCP de Academia

`/mcp/academy` es una superficie privada para la operación formativa. Sus
herramientas cubren:

- **Catálogo:** listar cursos, consultar cursos y listar lecciones.
- **Contenido:** crear, editar y archivar cursos y lecciones de la sede.
- **Estudiantes:** inscribir al usuario autenticado y listar sus inscripciones;
  el listado administrativo no expone notas pastorales ni médicas.
- **Asistencia:** registrar asistencia por inscripción y fecha de forma
  idempotente.

Los cursos globales (`sede_id IS NULL`) son legibles para captación, pero no
pueden ser mutados ni administrados desde una sede. Los cursos creados por MCP
siempre reciben la sede del usuario y nunca aceptan `sede_id` como parámetro.

## 9. Contrato del MCP de Calendario

`/mcp/calendar` expone la operación de Agenda usando sus contratos canónicos:

- **Eventos:** listar, buscar por rango, consultar, crear, editar y archivar.
- **Recursos físicos:** listar, crear y archivar recursos de la sede.
- **Participantes:** listar, añadir personas de la sede y archivar participantes.
- **Reservas:** listar, crear con detección de solapamientos y archivar reservas.

La sede se obtiene del JWT y se verifica tanto en el evento como en el recurso o
persona relacionado. La creación de una reserva rechaza intervalos inválidos o
conflictivos antes de persistirlos.

## 10. Separación entre público y privado

El MCP público de CMS (`backend/mcp_public.py`) no debe reutilizarse para
consultar CRM, personas, borradores, permisos o evangelismo. Su contrato es
intencionalmente de solo lectura y trabaja con una sesión de base de datos
independiente por herramienta. La gestión editorial privada vive en
`cms_admin_mcp` y se monta en `/mcp/cms`
con `authenticated_mcp_app`.


El MCP privado no debe montarse bajo una ruta pública ni aceptar un token en un
parámetro de la herramienta. La credencial siempre viaja en el encabezado HTTP
Bearer y el SDK la valida antes de ejecutar la herramienta.

## 11. Reglas para próximos MCP

Cada nuevo MCP o módulo de herramientas debe:

1. declarar su dominio y si es público o privado;
2. reutilizar `mcp_auth.py` para JWT, usuario y permisos privados;
3. resolver `sede_id` desde el actor, nunca desde un argumento confiado;
4. usar el modelo canónico `personas.id`;
5. separar herramientas de lectura de mutaciones;
6. limitar paginación, tamaño de lote y campos PII;
7. hacer mutaciones idempotentes cuando el dominio lo permita;
8. registrar auditoría cuando la operación ya lo exija en REST;
9. tener pruebas de permiso, sede, entrada inválida y operación repetida;
10. actualizar este documento y el contrato del módulo en español.

## 12. Verificación local

Para revisar la superficie MCP sin iniciar un cliente externo:

```bash
./venv/bin/python -m pytest -q -o addopts='' tests/test_mcp_evangelism.py tests/test_mcp_crm.py tests/test_mcp_academy.py tests/test_mcp_agenda.py
./venv/bin/python -m pytest -q -o addopts='' tests/test_events_participantes_full.py
```

En un ambiente levantado, el cliente debe conectarse a:

```text
http://localhost:8000/mcp             # público, lectura
http://localhost:8000/mcp/platform    # catálogo completo de módulos, Bearer JWT
http://localhost:8000/mcp/evangelism  # privado, requiere Bearer JWT
http://localhost:8000/mcp/crm         # privado, requiere Bearer JWT
http://localhost:8000/mcp/academy     # privado, requiere Bearer JWT
http://localhost:8000/mcp/calendar    # privado, requiere Bearer JWT
```

El host permitido por la protección de transporte del MCP público sigue siendo
el definido en `backend/mcp_public.py`. La protección de identidad del MCP
privado la proporciona el middleware Bearer de `backend/mcp_auth.py`.
