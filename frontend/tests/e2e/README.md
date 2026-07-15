# Playwright E2E

## Suites
- `smoke.spec.ts`: rutas publicas (`/login`, `/faro`), siempre ejecutables.
- `authenticated.spec.ts`: rutas con sesion (`/academy`, `/projects`, `/crm`).
- `projects-demo.spec.ts`: semilla y verificacion de `projects`, `tasks` y `activities` con 3 proyectos / 15 tareas.

## Variables para autenticados
- `E2E_EMAIL`
- `E2E_PASSWORD`
- `E2E_API_URL` (o `NEXT_PUBLIC_API_URL`)

Si falta alguna variable, la suite autenticada se marca como `skip` automaticamente.

## Comandos
- `npm run test:e2e`
- `npm run test:e2e:auth`
- `npm run test:e2e:seed-user`
- `npm run test:e2e:seed-projects-demo`

## Seed de usuario para CI
`seed-auth-user.mjs` intenta:
1. Login con `E2E_EMAIL`/`E2E_PASSWORD`.
2. Si falla, registra usuario en `/auth/register`.
3. Reintenta login para validar credenciales.
