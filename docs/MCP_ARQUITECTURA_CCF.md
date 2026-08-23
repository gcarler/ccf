# MCP de la plataforma CCF

**Estado:** catálogo MCP completo para 32 módulos, más gateway de descubrimiento
**Fecha de verificación:** 21 de agosto de 2026
**Fuente de verdad:** `backend/mcp_public.py`, `backend/mcp_auth.py`, `backend/mcp_evangelism.py`, `backend/mcp_crm.py`, `backend/mcp_academy.py`, `backend/mcp_agenda.py` y `backend/core/permissions.py` (matriz RBAC).

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

La jerarquía sigue la de REST: `manage` incluye `edit` y `read`. Cada
herramienta vuelve a resolver el permiso con `require_mcp_permission`,
que aplica exactamente la misma resolución que el guard REST
`require_permission` (ver §3.2).

### 3.2 Matriz RBAC compartida (REST ↔ MCP)

La matriz de permisos **por rol** para roles de plataforma sin permisos
granulares explícitos vive en **una sola función**:
`role_allows_permission(role, permission)` en `backend/core/permissions.py`.

- **REST:** `require_permission` la usa como fallback cuando el usuario no
  tiene el permiso granular (`_has_permission` falla) ni es admin.
- **MCP:** `require_mcp_permission` (`backend/mcp_auth.py`) calcula los scopes
  del usuario con `_effective_user_scopes`, que combina
  `get_user_effective_permissions` (rol_plataforma, `UsuarioRolModulo` y
  `UsuarioPermisoOverride`) con los allowances de `role_allows_permission`
  aplicados sobre toda la taxonomía `PERMISSIONS`; si aun así no hay match,
  aplica `role_allows_permission` directamente antes de denegar.

Ambas fronteras leen los permisos granulares de la **misma fuente de verdad**
(`get_user_effective_permissions`), por lo que jerarquía, grants modulares y
denegaciones coinciden permiso por permiso. La garantía la cubren
`tests/test_mcp_auth.py` (`TestMcpRoleMatrixParity` y
`TestMcpRestParityGranularPermissions`, que comparan REST y MCP sobre toda la
taxonomía).

Allowances por rol (además de los permisos granulares explícitos en BD):

| Rol | Permisos concedidos por rol | Módulos sin allowance |
|---|---|---|
| `admin` / `administrador` | Todos (`system:config`, `profile:manage` y cada `módulo:read/edit/manage`) | — (bypass total) |
| `pastor` | `crm:*`, `evangelism:*`, `academy:read/study/edit/manage`, `projects:*`, `wiki:*` | CMS, finanzas, soporte, comunidad, etc. |
| `coordinador` | `evangelism:read/edit`, `academy:read/study/edit/manage`, `projects:*`, `wiki:*` | `evangelism:manage`, `crm:*`, CMS, finanzas, etc. |
| `docente` | `academy:read/study/edit`, `projects:*`, `wiki:*` | `academy:manage`, `evangelism:*`, `crm:*`, etc. |
| `estudiante`, `lector`, `miembro`, `aspirante` | `academy:read/study` | Todo lo demás |

Donde `módulo:*` significa `read` + `edit` + `manage`, y la jerarquía sigue
siendo `manage → edit → read`. Un `coordinador` puede reportar asistencia de
evangelismo (`evangelism:edit`) pero no crear estrategias ni dividir grupos
(`evangelism:manage`) sin el permiso granular explícito; un `docente` edita
contenido académico pero no archiva cursos ni administra estudiantes
(`academy:manage`).

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

Las filas soft-deleted de la misma clave `(event_id, session_date, persona_id)`
se **reutilizan y reactivan** (`deleted_at = NULL`) al volver a seleccionar a
la persona, en lugar de insertar un duplicado que violaría la restricción
única (la `UniqueConstraint` no considera `deleted_at`). Las filas
soft-deleted que no se seleccionan permanecen borradas y no se reviven como
ausentes. Este comportamiento es idéntico al del endpoint REST
`POST /api/evangelism/attendance/bulk`.

## 6. Contrato del MCP público y del CMS privado

El CMS expone dos superficies MCP con contratos distintos, ambas en
`backend/mcp_public.py`:

- **Pública** (`public_mcp`, montada en `/mcp`): solo lectura del contenido
  publicado; no requiere JWT.
- **Privada** (`cms_admin_mcp`, montada en `/mcp/cms` con
  `authenticated_mcp_app`): gestión editorial con Bearer JWT, `cms:edit` y
  roles editoriales.

### 6.1 MCP público — contenido publicado (solo lectura)

No requiere autenticación. Lee únicamente contenido publicado del sitio
público y nunca expone borradores, datos administrativos ni personas. La
protección de transporte solo acepta los hosts permitidos definidos en
`backend/mcp_public.py` (dominio canónico `ministerioselfaro.org`, su variante
`www` y localhost).

| Herramienta | Parámetros | Comportamiento |
|---|---|---|
| `list_public_pages` | `site_key` (default `ccf`), `limit` (máx. 100) | Lista páginas publicadas del sitio |
| `get_public_page` | `slug`, `site_key` | Página publicada con sus secciones, SEO y datos estructurados |
| `get_public_menu` | `menu_key` (default `main`), `site_key` | Enlaces visibles de un menú publicado |
| `list_public_posts` | `site_key`, `limit` (máx. 50) | Lista publicaciones y sermones publicados |
| `get_public_post` | `slug`, `site_key` | Publicación o sermón publicado |
| `search_public_content` | `query` (mín. 2 caracteres), `site_key`, `limit` (máx. 20) | Busca en títulos y contenido publicado de páginas y posts; devuelve `kind` (`page`/`post`), `slug`, `title` y `href` |

### 6.2 MCP privado — gestión editorial

Reutiliza el JWT CCF, el permiso `cms:edit`, el aislamiento por sitio
(`_get_scoped_site_or_404`) y las funciones CRUD/workflow del CMS. Crear
siempre produce un **borrador**; las acciones de publicación exigen además los
roles publicadores definidos por CMS (`CMS_PUBLISHER_ROLES` =
`admin`, `coordinador`, `gestor`, `pastor`; el resto de ediciones usa
`CMS_EDITOR_ROLES`, que suma `docente` y `editor`).

La credencial viaja únicamente en `Authorization: Bearer`; ninguna herramienta
acepta un token como argumento y todas exigen el contexto de autenticación
MCP (`ctx`) — sin él se rechaza la operación.

| Herramienta | Parámetros | Comportamiento |
|---|---|---|
| `list_manageable_pages` | `site_key`, `limit` (máx. 200) | Lista páginas de todos los estados (borrador, revisión, publicado, archivado) del sitio |
| `create_public_page` | `slug`, `title`, `site_key`, `seo_json` | Normaliza el slug (`_slugify`), valida duplicados (`SlugConflictError`) y crea un borrador; nunca publica automáticamente |
| `update_public_page` | `slug`, `site_key`, `new_slug`, `title`, `seo_json` | Edita metadatos (título, SEO, slug) sin cambiar el estado de publicación; valida duplicados de slug |
| `upsert_public_page_section` | `slug`, `section_type`, `props_json`, `site_key`, `section_id` (opcional), `sort_order`, `is_visible` | Valida el tipo contra el catálogo (`get_allowed_section_types`) y las props contra `validate_section_props`; con `section_id` actualiza la sección existente (un UUID malformado se rechaza con `ValueError` controlado) y sin él la crea |
| `publish_public_page` | `slug`, `action` (`publish`, `unpublish`, `archive`, `revert_draft`, `submit_review`, `approve`), `site_key`, `notes` | Ejecuta la transición del workflow (`PageWorkflowService`); `publish`, `unpublish`, `archive` y `approve` exigen rol publicador; reindexa la página o la retira del índice de búsqueda según el estado resultante |

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
./venv/bin/python -m pytest -q -o addopts='' tests/test_mcp_auth.py tests/test_mcp_evangelism.py tests/test_mcp_crm.py tests/test_mcp_academy.py tests/test_mcp_agenda.py tests/test_mcp_platform.py
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
