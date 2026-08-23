# Guía general de la plataforma CCF

**Nombre:** Plataforma CCF — Comunidad Cristiana El Faro
**Tipo de documento:** mapa funcional, arquitectónico y operativo
**Fecha de revisión del código:** 21 de agosto de 2026
**Fuente principal:** código vigente del repositorio; los documentos de estado se usan como contexto y trazabilidad.

> Esta guía es el punto de entrada para comprender CCF. No reemplaza los contratos detallados de cada módulo ni los runbooks de producción. Cuando exista una diferencia entre un plan histórico y el código actual, debe prevalecer el código, sus pruebas y la configuración de ejecución vigente.

---

## 1. Qué es CCF

CCF es una plataforma institucional para administrar la operación ministerial, pastoral, formativa, editorial y administrativa de la iglesia. Combina:

- un sitio público de contenido y comunicación;
- un espacio autenticado de trabajo para equipos y personas;
- módulos de identidad, permisos y administración;
- seguimiento pastoral y CRM;
- evangelismo, grupos, sesiones y asistencia;
- academia, cursos y progreso formativo;
- proyectos, tareas y pizarras colaborativas;
- agenda, calendario y vida espiritual;
- mensajería, chat y comunidad;
- finanzas, donaciones, documentos y firma;
- CMS, páginas públicas, media, SEO y publicación;
- analítica, auditoría, agentes y base de conocimiento.

La plataforma se identifica en el backend como **CCF Mesh API** y en el frontend como el workspace de plataforma bajo `/plataforma`.

---

## 2. Resumen ejecutivo de la arquitectura

```text
Navegador
   │
   ├── Sitio público: Next.js App Router
   │       ├── páginas públicas
   │       ├── contenido publicado por CMS
   │       └── formularios, eventos, cursos y donaciones públicas
   │
   └── Workspace autenticado: /plataforma
           ├── AuthContext + ProtectedRoute
           ├── WorkspaceLayout y navegación modular
           ├── apiFetch: tokens, refresh, timeout y errores
           └── páginas de CRM, Academia, Evangelismo, etc.
                    │
                    ▼
             FastAPI / backend.app
                    ├── routers modulares
                    ├── guards RBAC y permisos
                    ├── scope multi-sede
                    ├── CRUD / servicios / eventos
                    └── SQLAlchemy
                            │
                            ▼
                    PostgreSQL en staging/producción
                    SQLite para desarrollo local y pruebas
                            │
             Alembic: migraciones canónicas

Servicios complementarios:
- Redis: caché, sesiones auxiliares y rate limiting.
- Kafka: integración opcional de eventos.
- DuckDB: almacén analítico local configurado.
- SMTP: verificación de correo y recuperación de contraseña.
- almacenamiento local o integración opcional de objetos/media.
- OpenTelemetry: telemetría opcional.

### 2.2 Superficies MCP

El backend expone un gateway y superficies MCP por módulo:

- `/mcp/platform`: catálogo autenticado de los 32 módulos MCP.
- `/mcp`: solo lectura del CMS publicado, sin personas ni datos administrativos.
- `/mcp/cms`: gestión privada de páginas CMS, secciones y workflow con Bearer JWT y RBAC editorial.
- `/mcp/evangelism`: superficie privada con Bearer JWT, RBAC `evangelism:*` y aislamiento por `sede_id` para estrategias, grupos, sesiones, eventos y asistencia.
- `/mcp/crm`: superficie privada con Bearer JWT, RBAC `crm:*` y aislamiento por `sede_id` para personas, casos, tareas, pipeline, automatizaciones, eventos y asistencia.
- `/mcp/academy`: superficie privada con Bearer JWT y RBAC `academy:*` para cursos, lecciones, inscripciones, estudiantes y asistencia académica.
- `/mcp/calendar`: superficie privada con Bearer JWT y permisos `spiritual_life:*` para eventos de Agenda, recursos físicos, participantes y reservas.
- Los demás módulos tienen una ruta `/mcp/{modulo}` con descubrimiento de capacidades y proxy REST allowlisted, siempre sujeto al RBAC canónico.

El MCP privado de Evangelismo no requiere grupos para registrar asistencia en
eventos masivos: usa directamente `CrmEvent` + `EventAttendance`. Su contrato detallado está en
[`MCP_ARQUITECTURA_CCF.md`](MCP_ARQUITECTURA_CCF.md). El host permitido en
producción para el MCP público sigue siendo `ministerioselfaro.org` (y su
variante `www`).

Todas las superficies MCP privadas comparten la **misma matriz RBAC que
REST**: no existe una segunda taxonomía. Los permisos por rol
(`role_allows_permission`), los granulares (`UsuarioRolModulo` y overrides) y
la jerarquía se resuelven desde `backend/core/permissions.py`; el detalle
está en [`MCP_ARQUITECTURA_CCF.md`](MCP_ARQUITECTURA_CCF.md) §3.2.

### 2.3 Componentes principales

| Capa | Tecnología y ubicación | Responsabilidad |
|---|---|---|
| Frontend | Next.js, React, TypeScript en `frontend/src/` | Sitio público, workspace autenticado y componentes UI |
| API | FastAPI en `backend/api/` | Routers, endpoints, validación y dependencias |
| Dominio | CRUD y servicios en `backend/crud/` y `backend/services/` | Reglas de negocio, persistencia y procesos transversales |
| Modelos | SQLAlchemy en `backend/models_*.py` | Entidades, relaciones, enums e invariantes de datos |
| Schemas | Pydantic en `backend/schemas/` | Contratos de entrada y salida de la API |
| Seguridad | `backend/core/security.py`, `permissions.py`, `tenant.py` | JWT, contraseñas, RBAC y aislamiento por sede |
| Configuración | `backend/core/config.py` | Variables de entorno y validación por ambiente |
| Persistencia | SQLAlchemy + Alembic | Base de datos y migraciones reversibles |
| Calidad | `tests/`, `frontend/src/**/*.test.*`, Playwright | Tests de backend, frontend, contratos y E2E |
| Automatización | `.github/workflows/`, `scripts/`, `Makefile` | CI/CD, smoke tests, auditorías y operaciones |
| MCP | `backend/mcp_*.py` | Herramientas públicas y privadas para clientes MCP |

---

## 3. Estructura del repositorio

```text
backend/                 API, modelos, CRUD, servicios y núcleo técnico
frontend/                aplicación Next.js, componentes, hooks y pruebas E2E
docs/                    contratos, arquitectura, estados, QA y runbooks
tests/                   pruebas backend y contratos estructurales
alembic/                 migraciones de base de datos
scripts/                 gates, seeds, smoke tests y tareas operativas
infra/                   configuración de infraestructura y cron
uploads/                 archivos cargados localmente (no son código)
analytics/               almacén analítico local
test_artifacts/          reportes generados por pruebas o readiness
```

### 3.1 Backend

El punto de entrada es `backend.main`, que expone el objeto `app` importado desde `backend.app`.

Archivos de referencia:

- `backend/app.py`: crea la aplicación FastAPI, registra middleware, manejadores y routers.
- `backend/main.py`: exporta `app` para Uvicorn, Gunicorn y pruebas.
- `backend/core/config.py`: carga y valida configuración.
- `backend/core/database.py`: engine, `SessionLocal`, `Base` y dependencia `get_db`.
- `backend/core/permissions.py`: JWT, roles, permisos y guards.
- `backend/core/tenant.py`: resolución de `sede_id` del actor.
- `backend/models_*.py`: modelos SQLAlchemy agrupados por dominio.
- `backend/api/`: routers HTTP y WebSocket.
- `backend/crud/`: acceso al dominio y operaciones de persistencia.
- `backend/services/`: servicios, consumidores de eventos, notificaciones e integraciones.

### 3.2 Frontend

El frontend utiliza App Router de Next.js. El código vigente declara **Next.js 15.5.18** en `frontend/package.json`.

Áreas importantes:

- `frontend/src/app/(public)/`: páginas públicas.
- `frontend/src/app/plataforma/`: workspace autenticado.
- `frontend/src/components/`: componentes reutilizables y shells de módulos.
- `frontend/src/design/`: sistema de diseño documentado y probado.
- `frontend/src/context/`: Auth, comandos, creación y capas del workspace.
- `frontend/src/lib/`: HTTP, acceso a rutas, caché y utilidades.
- `frontend/tests/e2e/`: pruebas Playwright organizadas por módulo.

La ruta `/plataforma` está protegida por `ProtectedRoute`. Las reglas de acceso de navegación se centralizan en `frontend/src/lib/workspaceAccess.ts`, pero la autorización real siempre debe existir también en el backend.

---

## 4. Entrada y ciclo de vida del backend

`backend.app` registra la aplicación con:

- título `CCF Mesh API`;
- descripción `Sistema de Inteligencia Ministerial CCF`;
- versión `3.0.0-PRO`;
- middleware de observabilidad;
- cabeceras de seguridad;
- CORS configurable;
- rate limiting con SlowAPI;
- aislamiento de módulos;
- manejo uniforme de errores HTTP y de dominio CMS;
- montaje de archivos estáticos en `/api/static`.

Durante el ciclo de vida de producción intenta registrar herramientas de agentes, consumidores de eventos, reconstruir la base de conocimiento y calentar la caché de YouTube. En ambientes `test`, `testing` y `ci` omite las migraciones automáticas del arranque.

### 4.1 Health checks

```http
GET /
GET /healthz
```

`/healthz` devuelve el estado básico del proceso y la versión declarada de la API. Este endpoint no sustituye el readiness completo de producción, que también debe revisar frontend, base de datos, migraciones, assets y módulos críticos.

---

## 5. Mapa de módulos funcionales

| Módulo | Propósito | API principal | Ruta de plataforma | Documentación detallada |
|---|---|---|---|---|
| Auth v3 | Login, registro, refresh, OAuth, sesiones y perfil | `/api/v3/auth/*` | `/login`, `/register`, `/plataforma/account` | `PLATAFORMA_AUTH_RUNTIME_CONTRACT.md` |
| Kernel de personas | Identidad canónica, roles de iglesia y temas | `/api/*` | `/plataforma/theme` y superficies de personas | `ESTADO_KERNEL.md` |
| Administración | Usuarios, roles, permisos, sedes, auditoría y configuración | `/api/admin/*` | `/plataforma/admin` | `ADMIN_API_CONTRACTS.md` |
| CRM pastoral | Personas, familias, casos, pipeline, tareas y consejería | `/api/crm/*` | `/plataforma/crm` | `CRM_ARCHITECTURE.md`, `ESTADO_CRM.md` |
| Evangelismo | Estrategias, grupos, sesiones, asistencia, eventos y rankings | `/api/evangelism/*` | `/plataforma/evangelism` | `ESTADO_EVANGELISMO.md` |
| Academia | Cursos, lecciones, matrículas, progreso, evaluaciones y certificados | `/api/academy/*` | `/plataforma/academy` | `ESTADO_ACADEMY.md` |
| Proyectos | Proyectos, fases, tareas, comentarios, wiki y whiteboard | `/api/projects/*` | `/plataforma/projects` | `PROJECTS_API_CONTRACTS.md` |
| CMS | Sitios, páginas, secciones, posts, media, preview y publicación | `/api/cms/*`, `/api/cms/v2/*` | `/plataforma/cms` | `ARQUITECTURA_CMS.md`, `ESTADO_CMS.md` |
| Finanzas | Fondos, transacciones, contabilidad, facturación y gastos | `/api/finance/*`, `/api/finance-suite/*` | `/plataforma/finances`, `/contabilidad`, `/facturacion`, `/gastos` | `ESTADO_FINANCE.md` |
| Donaciones | Donaciones y configuración relacionada | `/api/donations/*` y rutas montadas en `/api` | `/plataforma/admin/donations` | `AUDITORIA_FORENSE_DONATIONS.md` |
| Agenda | Eventos, recursos, participantes y reservas | `/api/agenda/*` | `/plataforma/agenda`, `/plataforma/calendar` | `AGENDA_API_CONTRACTS.md` |
| Vida espiritual | Línea de tiempo, certificados y hitos | `/api/spiritual-life/*` | `/plataforma/spiritual-life` | `ESTADO_VIDA_ESPIRITUAL.md` |
| Mensajería y chat | Inbox, notificaciones, presencia, conversaciones y mensajes | `/api/messaging/*`, `/api/chat/*` | `/plataforma/inbox`, `/plataforma/messages` | `MESSAGING_COMMUNITY_API_CONTRACTS.md` |
| Comunidad | Grupos, eventos, testimonios, oración y anuncios | `/api/community/*` | `/plataforma/community`, `/plataforma/groups` | `ESTADO_COMMUNITY.md` |
| Wiki | Documentación colaborativa con versiones y soft delete | `/api/wiki/*` | `/plataforma/wiki` | `WIKI_API_CONTRACTS.md` |
| Workspace | Flags, incidencias, compliance, auditoría y configuración | `/api/workspace/*` | transversal | `ARQUITECTURA_WORKSPACE.md` |
| Soporte | Base de conocimiento, tickets, historial y contacto | `/api/support/*` y `/api/*` | `/plataforma/support` | `ESTADO_SUPPORT.md` |
| Analítica | Dashboards, métricas, warehouse y tendencias | `/api/analytics/*` y agregadores | `/plataforma/dashboard`, `/plataforma/admin/analytics` | `ESTADO_ANALYTICS.md` |
| Grafo | Relaciones y conexiones de conocimiento | `/api/graph/*` | `/plataforma/graph` | `ESTADO_GRAPH.md` |
| Agentes | Registro de herramientas, ejecuciones y analítica | `/api/agents/*` | `/plataforma/agents` | `ESTADO_AGENTS.md` |
| YouTube | Integración y caché de contenido de YouTube | `/api/youtube/*` | superficies CMS/públicas | `ESTADO_YOUTUBE.md` |
| MCP | Herramientas para clientes de agentes, separadas por dominio y sensibilidad | `/mcp`, `/mcp/evangelism`, `/mcp/crm` | transversal | `MCP_ARQUITECTURA_CCF.md` |

> Algunos routers antiguos comparten el prefijo `/api` y definen su subruta dentro del propio router. Para conocer la ruta exacta de un endpoint, consultar el contrato del módulo o `/docs` de FastAPI en un entorno local.

---

## 6. Identidad, roles y multi-sede

### 6.1 Kernel de personas

La entidad humana canónica es `personas`. Su identificador es un UUID:

```text
personas.id  ← identidad de la persona
     │
     ├── auth_users.id                 ← mismo UUID
     ├── personas con roles de iglesia
     ├── matrículas, grupos y relaciones
     └── owners, autores y asignados de recursos
```

`users` o `auth_users` representan autenticación y acceso. No deben usarse como sustituto de la identidad pastoral de una persona.

### 6.2 Tres dimensiones de identidad

| Dimensión | Qué representa | Fuente principal |
|---|---|---|
| Ministerio | Llamado u oficio ministerial | `persona_ministries` |
| Iglesia | Rol de la persona dentro de la iglesia | `persona_role_assignments`, roles de iglesia |
| Plataforma | Permisos de software | `auth_roles`, `auth_user_module_roles` |

Estas dimensiones no son intercambiables.

### 6.3 RBAC

La taxonomía central vive en `backend/core/permissions.py`:

- `system:config`;
- `profile:manage`;
- `crm:read|edit|manage`;
- `finance:read|edit|manage`;
- `projects:read|edit|manage`;
- `cms:read|edit|manage`;
- `academy:read|study|edit|manage`;
- `messaging:read|edit`;
- `evangelism:read|edit|manage`;
- `community:read|edit|manage`;
- `spiritual_life:read|edit|manage`;
- `support:read|edit|manage`;
- `analytics:read|manage`;
- `dashboard:read|manage`;
- `wiki:read|edit`.

La jerarquía es acumulativa: `manage` incluye `edit` y `read`; `edit` incluye `read`. `study` es un nivel específico de Academia.

Los guards deben salir de la capa central (`require_permission`, `require_module_access` y guards nombrados). No se debe crear una taxonomía paralela dentro de un router. Las superficies MCP privadas usan la misma capa central (`require_mcp_permission` + `role_allows_permission` en `backend/mcp_auth.py`), de modo que un rol sin permisos granulares recibe en MCP exactamente los mismos allowances por rol que en REST; detalle en [`MCP_ARQUITECTURA_CCF.md`](MCP_ARQUITECTURA_CCF.md) §3.2.

### 6.4 Aislamiento por sede

Los datos pastorales, administrativos y generados por usuarios deben filtrarse según la `sede_id` derivada del actor autenticado. El cliente no puede elegir libremente la sede de una mutación protegida.

Reglas esenciales:

1. resolver la sede desde Auth/Persona;
2. aplicar el filtro en la API;
3. repetir la defensa en CRUD cuando el dominio sea sensible;
4. validar owners, autores, asignados y relaciones en la misma sede;
5. evitar revelar la existencia de recursos de otra sede: normalmente se responde `404`;
6. no permitir UGC sin actor, owner o tenant atribuible.

Excepción editorial documentada: `CmsSite`, páginas, secciones, temas y menús globales pueden ser compartidos por diseño del sitio público. El contenido generado por usuarios, media y superficies administrativas sí debe respetar el scope que corresponda.

---

## 7. Autenticación y sesión

### 7.1 Endpoints canónicos

```text
POST /api/v3/auth/login
POST /api/v3/auth/initialize-password
POST /api/v3/auth/change-password
GET  /api/v3/auth/check-email
GET  /api/v3/auth/me
PATCH /api/v3/auth/me
POST /api/v3/auth/refresh
POST /api/v3/auth/logout
GET  /api/v3/auth/sessions
POST /api/v3/auth/sessions/{session_id}/revoke
POST /api/v3/auth/sessions/revoke-all
GET  /api/v3/auth/google
GET  /api/v3/auth/google/callback
POST /api/v3/auth/forgot-password
POST /api/v3/auth/reset-password
POST /api/v3/auth/verify-email
POST /api/v3/auth/send-verification-email
```

### 7.2 Transporte actual de sesión

El runtime soporta dos mecanismos coordinados:

1. El backend emite access token y refresh token.
2. También mantiene cookies `HttpOnly` para permitir refresh seguro.
3. El frontend guarda tokens para compatibilidad en `sessionStorage` bajo `ccf_token` y `ccf_refresh_token`.
4. `apiFetch` agrega `Authorization: Bearer ...` cuando existe token.
5. Un `401` dispara un único refresh compartido entre solicitudes concurrentes.
6. Si el refresh falla, se limpia la sesión y se redirige a login expirado.

El callback OAuth no debe colocar JWT en la URL. El flujo seguro usa `state`, cookie temporal y cookies de sesión antes de redirigir a `/auth/callback`.

### 7.3 Regla para frontend

El cliente HTTP canónico es:

```ts
import { apiFetch } from '@/lib/http';

const data = await apiFetch('/crm/personas');
```

No se debe duplicar la lógica de tokens, refresh, timeouts o errores en cada pantalla. Para descargar archivos se utiliza `apiFetchBlob` cuando corresponda.

---

## 8. Base de datos y migraciones

### 8.1 Ambientes

- **Local:** SQLite por defecto (`sqlite:///./ccf_dev.db`) para desarrollo rápido y pruebas.
- **Staging/producción:** PostgreSQL obligatorio; `backend/core/config.py` rechaza SQLite fuera de ambientes locales/de prueba.
- **Sesiones:** SQLAlchemy con `SessionLocal` y una sesión transaccional por solicitud.
- **Pool PostgreSQL:** pre-ping, pool de conexiones y reciclaje configurado.

SQLite tiene adaptaciones para tipos PostgreSQL usados por los modelos, como `CITEXT`, `ARRAY` y `JSONB`, con el fin de facilitar pruebas locales. Eso no convierte SQLite en una réplica funcional completa de PostgreSQL; los cambios de esquema y consultas críticas deben validarse contra PostgreSQL.

### 8.2 Alembic

Las migraciones viven en `alembic/canonical_versions/` y deben cumplir:

- una intención por migración;
- reversibilidad salvo excepción documentada;
- no modificar migraciones ya desplegadas;
- ejecutar `alembic upgrade head` antes del despliegue;
- mantener una cadena canónica y lineal;
- incluir índices y restricciones necesarias;
- probar upgrade, downgrade cuando aplique y estado final.

### 8.3 Integridad de datos

La plataforma usa UUID para entidades transaccionales expuestas por API, UTC para fechas y soft delete en entidades pastorales, administrativas y de contenido cuando el historial importa. No se debe implementar hard delete de personas ni de recursos protegidos sin una decisión explícita del dominio.

---

## 9. CMS y sitio público

El CMS tiene tres superficies relacionadas pero distintas:

### CMS v1
Conserva compatibilidad para media, optimización y métricas. No debe recibir nuevas entidades paralelas si existe contrato v2.

### CMS v2
Administra el modelo editorial principal:

```text
CmsSite
 ├── CmsTheme
 ├── CmsMenu → CmsMenuItem
 ├── CmsPage → CmsPageVersion → CmsSection
 ├── CmsPost → categorías y etiquetas
 └── analítica, scheduling y publicación

CmsMediaItem
Testimonial
Announcement
```

Rutas frecuentes:

```text
/api/cms/v2/sites/{site_key}/pages
/api/cms/v2/sites/{site_key}/pages/{slug}/preview
/api/cms/v2/sites/{site_key}/pages/{slug}/workflow
/api/cms/v2/sites/{site_key}/posts
/api/cms/v2/sites/{site_key}/themes
/api/cms/v2/sites/{site_key}/menus
```

### Enterprise CMS
Añade auditoría, permisos de contenido, notificaciones, webhooks, tipos personalizados, búsqueda, sesiones, carpetas de media, redirecciones y detección de enlaces rotos.

### Flujo editorial recomendado

```text
Borrador → Preview → Revisión/workflow → Publicado → Auditoría
```

Preview, publicado y contenido público son contratos diferentes y deben validarse por separado. Los uploads deben pasar por límite de tamaño, lista de extensiones, alineación MIME/extensión, saneamiento de nombre y scope por sede.

---

## 10. Frontend y experiencia de usuario

### 10.1 Workspace

`WorkspaceLayout`, `WorkspaceMainSidebar`, `WorkspaceMiniSidebar`, `WorkspaceToolbar`, `ProtectedRoute` y `CommandCenter` forman la infraestructura transversal del workspace.

Un cambio en estas piezas puede afectar todos los módulos. Debe validarse como cambio de plataforma compartida, no como cambio local de una pantalla.

### 10.2 Rutas

La convención general es:

```text
/plataforma/{modulo}[/{submodulo}][/{id}]
```

Ejemplos:

- `/plataforma/crm/personas`
- `/plataforma/academy/courses`
- `/plataforma/evangelism/groups`
- `/plataforma/projects`
- `/plataforma/cms/pages`
- `/plataforma/calendar`
- `/plataforma/inbox`

Existen alias históricos como `/plataforma/finances`, `/plataforma/contabilidad`, `/plataforma/facturacion`, `/plataforma/agenda`, `/plataforma/groups` y `/plataforma/tasks`. Deben conservarse solo cuando el contrato actual los requiera; las rutas nuevas deben usar la nomenclatura canónica del módulo.

### 10.3 Sistema de diseño

Los componentes de `frontend/src/design/` son la base preferida para botones, cards, tablas, tabs, inputs, badges, skeletons, tooltips, toasts y métricas.

Reglas de experiencia documentadas:

- usar tokens semánticos de color;
- mantener contraste y accesibilidad;
- preferir drawers/paneles laterales para detalles y edición contextual;
- cargar perfiles complejos por pestañas;
- evitar que cada módulo invente un shell propio;
- usar componentes base de tablas y calendarios cuando el caso aplique;
- mantener el lenguaje de dominio en español en la UI.

> La documentación histórica contiene una tensión entre la regla general de usar drawers y la existencia de `DSModal` para diálogos puntuales. La decisión debe ser contextual: no usar modales bloqueantes para flujos complejos de creación/edición; reservar diálogos breves para confirmaciones o acciones acotadas.

---

## 11. Flujos funcionales transversales

### 11.1 Registrar una persona

```text
Formulario público o administrativo
   → validación de schema
   → creación/actualización en personas
   → resolución de sede y owner
   → creación o asociación Auth cuando corresponde
   → evento, seguimiento o caso CRM según el origen
```

La persona debe conservar un único UUID durante todo el flujo.

### 11.2 Flujo de evangelismo

```text
Estrategia
  → Grupo de Evangelismo
    → Participantes
    → Sesión
      → Asistencia
        → Seguimiento
        → Caso CRM cuando aplica
```

Sesiones, asistencia y seguimiento heredan el scope del grupo y de la estrategia. El puente CRM vive en `backend/services/evangelism_crm_bridge.py`.

### 11.3 Flujo de formación

```text
Curso
  → Lecciones / recursos / evaluaciones
    → Matrícula
      → Progreso / asistencia / entregas
        → Calificación
        → Certificado
```

Los permisos Academy distinguen lectura, estudio, edición y gestión. Las operaciones de un estudiante deben verificar ownership de su propia matrícula y progreso.

### 11.4 Flujo financiero

Los dominios financieros aplican reglas de negocio específicas:

- partida doble para asientos;
- estados de facturas y gastos;
- segregación entre creador y aprobador;
- soft delete de documentos;
- scope por sede para cuentas, fondos, transacciones y documentos;
- integración de facturación electrónica no habilitada automáticamente si faltan credenciales/configuración.

### 11.5 Flujo de publicación CMS

```text
Editor crea contenido
   → página/versión/secciones
   → preview
   → workflow y permisos
   → publicación
   → invalidación de caché pública
   → auditoría y métricas
```

---

## 12. Eventos, tiempo real y procesos auxiliares

La aplicación registra consumidores de eventos durante el startup de producción. El backend también contiene superficies WebSocket para presencia, chat y colaboración, además de servicios de notificación y tareas programadas.

Principios:

- los consumidores deben tolerar reinicios y errores de dependencias externas;
- los procesos de startup no deben impedir que la API arranque si una integración opcional falla;
- las operaciones de tiempo real deben comprobar usuario, módulo y sede;
- los workers deben actuar con una persona de servicio canónica y tenant atribuible;
- las comunicaciones externas pueden bloquearse mediante `STUB_COMMS` en desarrollo/pruebas.

---

## 13. Configuración por ambiente

Variables base documentadas en `.env.example` y `frontend/.env.example`:

| Variable | Uso |
|---|---|
| `ENVIRONMENT` / `ENV` | ambiente de ejecución |
| `DATABASE_URL` | conexión a base de datos |
| `SECRET_KEY` | firma de tokens; obligatoria y fuerte fuera de local |
| `ENCRYPTION_KEY` | cifrado; obligatoria en staging/producción |
| `REDIS_URL` | Redis |
| `REDIS_PASSWORD` | contraseña Redis |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka opcional |
| `UPLOADS_DIR` | almacenamiento local de archivos |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` | correo transaccional |
| `FRONTEND_URL` | URL del frontend |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `MERCADOPAGO_*` | pagos y webhooks |
| `HCAPTCHA_SITE_KEY`, `HCAPTCHA_SECRET_KEY` | formularios anti-spam |
| `NEXT_PUBLIC_API_URL` | base pública de API para frontend |
| `NEXT_PUBLIC_WS_URL` | WebSocket del frontend |
| `API_BASE_URL` | proxy backend de Next |
| `API_PROXY_TARGET` | destino del proxy `/api` |
| `NEXT_DIST_DIR` | directorio de compilación Next cuando se usa build seguro |

En producción el código valida que no se use `SECRET_KEY=change-me`, que exista `ENCRYPTION_KEY`, que la base sea PostgreSQL y que las cookies seguras estén activadas.

Nunca se deben versionar secretos, bases locales, uploads ni archivos de estado regenerables.

---

## 14. Calidad y verificación

### 14.1 Backend

Comandos representativos:

```bash
# Smoke general
python -m pytest -q -o addopts='' tests/test_smoke.py tests/test_structural_contracts.py

# Reglas arquitectónicas
python -m pytest -q -o addopts='' tests/test_arquitectura_100pct.py

# Lint
ruff check backend/

# Compilación
python -m compileall backend

# Migraciones
alembic upgrade head
```

Los módulos tienen scripts canónicos en `scripts/`, entre ellos:

```text
scripts/test_platform_quality.py
scripts/test_crm_quality.py
scripts/test_academy_quality.py
scripts/test_cms_quality.py
scripts/test_evangelism_quality.py
scripts/test_projects_quality.py
scripts/test_messaging_quality.py
scripts/test_agenda_quality.py
scripts/test_workspace_quality.py
```

La suite adecuada depende del área modificada. Auth, permisos, `personas.id`, `sede_id`, `apiFetch`, layouts y tablas base requieren validación transversal.

### 14.2 Frontend

```bash
cd frontend
npm run typecheck
npm run lint
npm run test
npm run build
npm run test:e2e:platform
```

Cada módulo principal dispone de comandos E2E específicos en `frontend/package.json`, por ejemplo `test:e2e:crm`, `test:e2e:academy`, `test:e2e:projects`, `test:e2e:cms`, `test:e2e:evangelism`, `test:e2e:messaging` y `test:e2e:agenda`.

### 14.3 Gate proporcional

| Cambio | Verificación mínima |
|---|---|
| Documentación sin contrato modificado | revisión de enlaces y formato |
| Router o schema de un módulo | smoke del módulo + tests focalizados |
| Auth, permisos o sede | smoke de plataforma + tests de seguridad/aislamiento |
| `apiFetch`, layout o navegación | typecheck + build + rutas críticas |
| Modelo o migración | tests de dominio + migración upgrade/downgrade cuando aplique |
| CMS público o media | smoke admin + preview/publicado + upload hardening |
| Producción | readiness completo, migraciones, build, health checks y smoke post-deploy |

---

## 15. Documentación recomendada por tarea

### Cambio en plataforma compartida

1. `docs/ESTADO_PLATAFORMA_COMPARTIDA.md`
2. `docs/PLATAFORMA_AUTH_RBAC_API_UI.md`
3. `docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md`
4. `docs/PLATAFORMA_UI_BASE_PROTEGIDA.md`
5. `docs/PLATAFORMA_MATRIZ_MODULAR.md`

### Cambio en un módulo

1. `docs/ARRANQUE_MODULAR_CCF.md`
2. `docs/ESTADO_<MODULO>.md`
3. contrato API del módulo;
4. matriz RBAC del módulo;
5. checklist QA y plan de calidad;
6. auditoría forense si el cambio afecta seguridad o integridad.

### Documentos raíz

| Documento | Propósito |
|---|---|
| `README.md` | entrada rápida al repositorio |
| `PROJECT.md` | mapa histórico de arquitectura y milestones |
| `REGLAS.md` | invariantes obligatorias del kernel y la plataforma |
| `GLOSSARY.md` | vocabulario oficial de dominio |
| `FRONTEND_GLOSARIO.md` | vocabulario y convenciones de UI |
| `PRODUCTION_READINESS.md` | criterios para declarar producción lista |
| `docs/RUNBOOK_PRODUCCION.md` | operación y despliegue |
| `docs/CI_CD.md` | decisiones del pipeline |
| `docs/ARRANQUE_MODULAR_CCF.md` | inicio por módulo |
| `docs/MATRIZ_COBERTURA_MODULAR_CCF.md` | cobertura y estado de módulos |
| `CHANGELOG.md` | cambios históricos relevantes |

---

## 16. Riesgos y puntos de atención

1. **Identidad:** nunca introducir una segunda identidad humana ni usar un entero como sustituto de `personas.id`.
2. **Multi-sede:** cada consulta y mutación debe revisar scope; una pantalla correcta no compensa un endpoint inseguro.
3. **RBAC:** la UI puede ocultar una opción, pero el backend es la autoridad.
4. **Contratos duplicados:** existen aliases históricos y superficies v1/v2; no crear una tercera variante.
5. **CMS global:** el contenido editorial global es una decisión de producto; no extender esa excepción automáticamente a UGC.
6. **Runtime dual de sesión:** cualquier cambio en cookies, `sessionStorage`, refresh o OAuth requiere pruebas coordinadas frontend/backend.
7. **Migraciones:** las migraciones desplegadas son inmutables; corregir con una nueva migración.
8. **Documentos históricos:** varios archivos `ESTADO_*` contienen snapshots, tickets cerrados y referencias de fechas anteriores. No deben leerse como una garantía de que cada métrica sigue vigente sin revalidar el código.
9. **Documentación de versiones:** `PROJECT.md` menciona Next.js 14, pero el paquete vigente declara Next.js 15.5.18. Para versiones de dependencias, `package.json` y los archivos de lock son la fuente actual.
10. **Producción:** no declarar la plataforma al 100 % solo por tests locales; el readiness exige runtime web, migraciones, health checks, build reproducible, CI y árbol de cambios controlado.

---

## 17. Glosario mínimo

| Término | Definición |
|---|---|
| Persona | Ser humano registrado en el kernel; identidad en `personas` |
| Usuario/Auth | Cuenta y credenciales para acceder a la plataforma |
| Sede | Campus o tenant organizacional que delimita datos |
| RBAC | Control de acceso basado en roles y permisos |
| UGC | Contenido generado por usuarios |
| Owner | Persona responsable de un recurso |
| Soft delete | Baja lógica conservando historial mediante `deleted_at` o estado |
| Scope | Alcance de datos que puede consultar o modificar el actor |
| API canónica | Contrato vigente que debe usar el código nuevo |
| Smoke test | Prueba rápida de disponibilidad y comportamiento crítico |
| Readiness | Evaluación operativa previa a declarar un ambiente listo |

---

## 18. Principio final

CCF no debe evolucionar como una colección de pantallas aisladas. Cada funcionalidad debe conservar cuatro contratos simultáneamente:

```text
Identidad de persona
        +
Permiso del actor
        +
Aislamiento por sede
        +
Contrato API/UI verificable
```

Si una modificación rompe cualquiera de estos cuatro elementos, no es un cambio local: es un cambio de arquitectura y debe documentarse, probarse y revisarse como tal.
