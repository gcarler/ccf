# Plan de Produccion - Proyecto CCF

**Actualizado:** 2026-06-26

La plataforma corre en VPS directo con FastAPI, PostgreSQL, Next.js, nginx y PM2.

## Contratos de Produccion

- Backend expuesto por FastAPI en puerto interno.
- Frontend Next.js servido por PM2.
- Base de datos PostgreSQL.
- Migraciones con Alembic.
- Identidad de personas por UUID en `personas.id`.
- Acceso por Auth v3 en `auth_users`.

## Deploy

```bash
cd /root/ccf
git pull origin main
source venv/bin/activate
alembic upgrade head
pm2 restart ccf-backend ccf-frontend
```

## Smoke Test

```bash
curl -f http://127.0.0.1:8000/healthz
curl -f http://127.0.0.1:8000/api/system/health
curl -f http://127.0.0.1:3000/plataforma
```

## Seguridad Operativa

- `.env` no se versiona.
- Produccion debe definir `ENCRYPTION_KEY`.
- Cookies seguras deben activarse por entorno.
- No desplegar si Alembic no llega a `head`.
- No desplegar si `/plataforma` responde con error de aplicacion.

## Rollback

1. Identificar el commit anterior sano.
2. Aplicar `git revert` del commit defectuoso.
3. Ejecutar migracion de reversa solo si el cambio la incluyo y fue validada.
4. Reiniciar servicios PM2.
5. Repetir smoke test.

El runbook extendido vive en `docs/RUNBOOK_PRODUCCION.md`.
