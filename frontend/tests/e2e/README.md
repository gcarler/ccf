# Playwright E2E

## Suites
- `smoke.spec.ts`: rutas publicas (`/login`, `/faro`), siempre ejecutables.
- `authenticated.spec.ts`: rutas con sesion (`/academy`, `/projects`, `/crm`).
- `projects/smoke.spec.ts`: smoke dedicado de Projects (`/plataforma/projects/list`, `/plataforma/projects/tasks`, `/plataforma/projects/inbox`) con bloqueo de consola/API/assets.
- `projects/detail.spec.ts`: smoke profundo seeded de Projects detail (`/plataforma/projects/[id]` dashboard/list/calendar) reutilizando `seed-projects-demo`; requiere runtime Next vivo.
- `crm/smoke.spec.ts`: smoke dedicado de CRM (`/plataforma/crm`, `/plataforma/crm/personas`, `/plataforma/crm/pipeline`) con bloqueo de consola/API/assets.
- `crm/persona-detail.spec.ts`: cobertura profunda mockeada del detalle `/plataforma/crm/personas/[id]`; valida MESH insight, tabs de historial/contribuciones y mentoría; requiere runtime Next vivo.
- `academy/smoke.spec.ts`: smoke dedicado de Academy (`/plataforma/academy`, `/plataforma/academy/forum`, `/plataforma/academy/coordination`) con bloqueo de consola/API/assets.
- `academy/profile-detail.spec.ts`: cobertura profunda mockeada de `/plataforma/academy/profile` y `/plataforma/academy/profile/progress`; valida ownership visible, cursos activos, certificados y cambios de vista; requiere runtime Next vivo.
- `messaging/smoke.spec.ts`: smoke dedicado de Messaging / Community (`/plataforma/inbox/messages`, `/plataforma/messages`, `/plataforma/community`, `/plataforma/community/events`) con bloqueo de consola/API/assets.
- `messaging/direct-messages.spec.ts`: cobertura profunda mockeada de `/plataforma/messages`; valida listado, apertura de hilo, búsqueda de usuario, creación de conversación y envío de mensaje con runner administrado.
- `agenda/smoke.spec.ts`: smoke dedicado de Agenda / Calendar (`/plataforma/calendar`, `/plataforma/agenda/events`) con bloqueo de consola/API/assets.
- `agenda/calendar-events.spec.ts`: cobertura profunda mockeada de `/plataforma/agenda/events`, `/plataforma/agenda/events/[id]` y `/plataforma/calendar`; valida CRUD manual básico, detalle editable y navegación del calendario agregado al owner route.
- `evangelism/smoke.spec.ts`: smoke dedicado de Evangelismo (`/plataforma/evangelism`, `/plataforma/evangelism/groups`, `/plataforma/evangelism/rankings`) con bloqueo de consola/API/assets.
- `evangelism/sessions-detail.spec.ts`: cobertura profunda mockeada del flujo `/plataforma/evangelism/faro/sessions/[grupo_id]`; requiere runtime Next vivo.
- `evangelism/rankings-multiplication.spec.ts`: cobertura profunda mockeada de rankings y multiplication; requiere runtime Next vivo.
- `evangelism/events-scanner.spec.ts`: cobertura profunda mockeada de `/plataforma/evangelism/events`, `/plataforma/evangelism/events/[id]` y `/plataforma/evangelism/scanner`; valida creación de eventos, asistencia por scanner, agenda de sesión y validación standalone de tokens.
- `cms/smoke.spec.ts`: smoke dedicado de CMS (`/plataforma/cms`, `/plataforma/cms/pages`, `/plataforma/cms/media`) con bloqueo de consola/API/assets.
- `cms/pages-preview.spec.ts`: cobertura profunda mockeada de `/plataforma/cms/pages` y `/plataforma/cms/preview`; valida gestión editorial, archivado y render draft con runner administrado.
- `platform-critical-routes.spec.ts`: rutas criticas canonicas de plataforma (`/plataforma/crm/personas`, `/plataforma/projects`, `/plataforma/evangelism`, `/plataforma/academy`, `/plataforma/cms`) con bloqueo de errores de consola, API y `_next/static`.
- `projects-demo.spec.ts`: semilla y verificacion de `projects`, `tasks` y `activities` con 3 proyectos / 15 tareas.

## Variables para autenticados
- `E2E_EMAIL`
- `E2E_PASSWORD`
- `E2E_API_URL` (o `NEXT_PUBLIC_API_URL`)

Si falta alguna variable, la suite autenticada se marca como `skip` automaticamente.

## Matriz multiusuario
- `npm run test:e2e:modules:matrix`
- Perfiles por defecto: `admin,editor,manager`
- Variables por perfil:
  - `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD`
  - `E2E_EDITOR_EMAIL` / `E2E_EDITOR_PASSWORD`
  - `E2E_MANAGER_EMAIL` / `E2E_MANAGER_PASSWORD`
- Se puede redefinir el orden/lista con `E2E_MATRIX_PROFILES=admin,editor,manager`
- El runner reutiliza `E2E_API_URL` o `NEXT_PUBLIC_API_URL` y ejecuta `test:e2e:modules` una vez por perfil

## Comandos
- `npm run test:e2e`
- `npm run test:e2e:auth`
- `npm run test:e2e:projects`
- `npm run test:e2e:projects:detail`
- `npm run test:e2e:crm`
- `npm run test:e2e:crm:deep`
- `npm run test:e2e:academy`
- `npm run test:e2e:academy:deep`
- `npm run test:e2e:messaging`
- `npm run test:e2e:messaging:deep`
- `npm run test:e2e:agenda`
- `npm run test:e2e:agenda:deep`
- `npm run test:e2e:evangelism`
- `npm run test:e2e:evangelism:deep`
- `npm run test:e2e:cms`
- `npm run test:e2e:cms:deep`
- `npm run test:e2e:modules`
- `npm run test:e2e:modules:matrix`
- `npm run test:e2e:platform`
- `npm run test:e2e:seed-user`
- `npm run test:e2e:seed-projects-demo`

## Runner administrado
- `npm run test:e2e:auth:managed`, `npm run test:e2e:projects:detail` y los comandos profundos de evangelismo, CRM, Academy, CMS, Messaging y Agenda levantan un `webServer` administrado por Playwright sobre `http://localhost:4173`.
- El wrapper comun vive en `frontend/scripts/run-managed-playwright.mjs`.
- El runner fija `NEXT_PUBLIC_API_URL` y `API_BASE_URL` hacia `http://127.0.0.1:8000/api` si no existen overrides.

## Seed de usuario para CI
`seed-auth-user.mjs` intenta:
1. Login con `E2E_EMAIL`/`E2E_PASSWORD`.
2. Si falla, registra usuario en `/auth/register`.
3. Reintenta login para validar credenciales.
