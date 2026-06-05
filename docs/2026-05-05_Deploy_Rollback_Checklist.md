# Deploy Rollback Checklist (CCF)

Fecha: 2026-06-05
Estado: Vigente
Ambito: incidentes de despliegue para backend/frontend en VPS directo.

## 1. Criterios de activacion

Activar rollback si ocurre al menos una condicion:
- error 5xx sostenido despues de deploy
- `./startccf` no converge (backend o frontend no levantan)
- degradacion critica de login, CRM, evangelismo o academy
- incompatibilidad de migracion detectada en runtime

## 2. Preflight rapido (2-3 minutos)

1. Verificar git status:
   - `cd /root/ccf && git log --oneline -3`
   - `git status --short`
2. Verificar puertos ocupados:
   - `lsof -i :8000` (backend)
   - `lsof -i :3000` (frontend)
3. Confirmar impacto:
   - errores en `tail -50 /root/ccf/backend.log`
   - errores en `tail -50 /root/ccf/frontend.log`

## 3. Rollback operativo

### Opcion A: Revertir commit (rapida)

1. Detener app:
   - `cd /root/ccf && ./stopccf`
2. Revertir el ultimo commit:
   - `git revert HEAD --no-edit`
3. Subir app:
   - `./startccf`
4. Verificacion:
   - `curl -f https://elfarocc.tech/healthz`
   - `curl -f https://elfarocc.tech/api/system/health`

### Opcion B: Volver a commit anterior (controlado)

1. Ver historial:
   - `git log --oneline -10`
2. Hard reset a commit estable:
   - `git reset --hard <SHA_ESTABLE>`
3. Subir app:
   - `./startccf`
4. Verificacion:
   - `curl -f https://elfarocc.tech/healthz`

## 4. Datos y migraciones

- Si hubo migraciones incompatibles, detener nuevos writes antes de rollback.
- Si el rollback de app depende de esquema previo, ejecutar `alembic downgrade -1`.
- Nunca ejecutar rollback destructivo de BD sin respaldo validado (`pg_dump`).

## 5. Cierre del incidente

1. Confirmar recuperacion funcional:
   - login
   - dashboard
   - CRM y evangelismo (eventos/asistencia)
2. Confirmar recuperacion tecnica:
   - `curl -f https://elfarocc.tech/healthz` → 200
   - `curl -f https://elfarocc.tech/` → 200
3. Documentar postmortem minimo:
   - SHA desplegado
   - causa raiz
   - accion de rollback aplicada
   - accion preventiva

## 6. Prevencion obligatoria despues de rollback

- bloquear redeploy automatico del mismo SHA
- abrir fix de app antes de reintentar despliegue
- validar en local con quality gate antes de push
