# Estado Arquitectonico CCF

**Fecha:** 2026-06-27
**Contrato vigente:** plataforma v3 con Kernel de Personas.

## Contratos Activos

- `personas.id` es el unico identificador de una persona.
- `auth_users.id` comparte el UUID de `personas.id`.
- Auth expone exclusivamente `/api/v3/auth`.
- Academy expone exclusivamente `/api/academy` y persiste en tablas `academy_*`.
- Los roles de plataforma viven en `auth_roles` y `auth_user_module_roles`.
- Los datos administrativos y pastorales respetan `sede_id`.

## Estado De Datos

Verificado en produccion antes de la migracion final:

- 769 personas y 769 usuarios Auth activos.
- 0 personas sin usuario Auth.
- 0 correos duplicados en personas.
- `gscarlosernesto@gmail.com` tiene rol `ADMINISTRADOR`.
- Las tablas Academy paralelas y las tablas Identity paralelas estan vacias; las migraciones abortan si esa precondicion cambia.

## Academy

- Catalogo, lecciones, matriculas, progreso, evaluaciones, certificados, tareas y foro usan UUID.
- Un usuario `LECTOR` recibe `academy:study` y puede operar solo sobre su propia matricula y progreso.
- Edicion y gestion requieren `academy:edit` o `academy:manage`.
- Las consultas de curso y dashboard aplican el alcance de sede.
- No existe una ruta `/api/v2/academy` ni un segundo modelo Academy.

## Gate De Cierre

```bash
rg -n "/api/v2/academy|CCF-MBR|personas\.user_id|subject\.isdigit" backend frontend/src tests scripts docs REGLAS.md
rg -n "FROM (courses|lessons|enrollments|assessments|certificates)" backend scripts

source venv/bin/activate
python -m pytest -q -o addopts='' tests/test_structural_contracts.py tests/test_smoke.py tests/test_academy_api.py

cd frontend
npm run typecheck
npm run build
```

El cierre requiere ademas `alembic upgrade head`, health checks local/publicos y un flujo autenticado Academy con un administrador y un usuario `LECTOR`.
