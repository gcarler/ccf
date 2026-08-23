# Runbook de Operaciones — Plataforma CCF v3.0

**Fecha:** 2026-08-23 (revisado; última revisión previa: 2026-06-05)
**Autor:** Equipo de Arquitectura CCF
**Audiencia:** DevOps, Desarrolladores Backend, Administradores

---

## 📋 Índice

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Protocolo de Ramas, Integración y Push](#2-protocolo-de-ramas-integración-y-push)
3. [Procedimiento de Deploy](#3-procedimiento-de-deploy)
4. [Rollback](#4-rollback)
5. [Monitoreo y Alertas](#5-monitoreo-y-alertas)
6. [Procedimientos de Emergencia](#6-procedimientos-de-emergencia)
7. [Mantenimiento Programado](#7-mantenimiento-programado)

---

## 1. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIOS                                │
│              (Web, Mobile)                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS (443)
┌───────────────────────────▼─────────────────────────────────────┐
│                    NGINX (Proxy Inverso)                        │
│   SSL termination (Let's Encrypt), proxy_pass, static files     │
│   Dominio: elfarocc.tech                                        │
└───────────────────────┬──────────────────┬──────────────────────┘
                        │                  │
          ┌─────────────▼─────┐    ┌───────▼──────────────┐
          │  FastAPI Backend  │    │  Frontend (Next.js)  │
          │  :8000 (uvicorn)  │    │  :3000 (next start)  │
          │  /api/*           │    │  / → Next.js         │
          └─────────┬─────────┘    └──────────────────────┘
                    │ SQLAlchemy
          ┌─────────▼──────────────────────────────────────────┐
          │              PostgreSQL 15                          │
          │  (VPS localhost:5432, sin Docker)                   │
          └────────────────────────────────────────────────────┘
```

### Componentes en Producción

| Componente | Tecnología | Puerto | Inicio |
|---|---|---|---|
| Frontend | Next.js 15 | `:3000` | `pm2 start ecosystem.config.js --only ccf-frontend-staging` |
| Backend | FastAPI + Python 3.12 | `:8000` | `pm2 start ecosystem.config.js --only ccf-backend-staging` |
| Base de Datos | PostgreSQL 15 | `:5432` | `systemctl postgresql` |
| Proxy | nginx | `:443` / `:80` | `systemctl nginx` |
| Repositorio | Git (VPS `/root/ccf`) | — | `git pull origin main` |

### Archivos Clave

| Archivo | Propósito |
|---|---|
| `/root/ccf/startccf` | Arranque manual alterno; no usar si la instancia ya está bajo PM2 |
| `/root/ccf/stopccf` | Detiene procesos de forma limpia con `_kill_with_verify()` |
| `/etc/nginx/sites-available/elfarocc.tech` | Configuración de proxy inverso |
| `/root/ccf/.env` | Variables de entorno (DB, secretos, API keys) |

---

## 2. Protocolo de Ramas, Integración y Push

Este es el flujo obligatorio para todos los agentes y herramientas que trabajen
en CCF. `main` es la única rama canónica y estable; los módulos se publican desde
su rama propietaria y se integran mediante una rama temporal creada desde el
último `origin/main`. Las ramas con conflictos permanecen separadas hasta su
resolución explícita.

### 2.1 Antes del commit

```bash
cd /root/ccf
git status --short --branch
git diff --check
```

Si aparecen cambios ajenos, se conservan y no se agregan al commit. Cada commit
debe representar una sola unidad temática y usar un prefijo convencional.

### 2.2 Validación de la rama

```bash
BRANCH="$(git branch --show-current)"
./venv/bin/python scripts/check_branch_contract.py \
  --branch "$BRANCH" --base origin/main --head HEAD
```

El contrato evita mezclar archivos de módulos distintos. Si el cambio requiere
otra rama, se detiene el trabajo y se crea o usa el worktree propietario.

### 2.3 Push sectorizado

```bash
scripts/push_branch.sh origin "$BRANCH"
```

El helper verifica worktree limpio, sincroniza la base remota, ejecuta el
`pre-push`, bloquea pushes ambiguos o desfasados y confirma que el SHA remoto
coincida con el commit local. Está prohibido usar `git push --no-verify`, hacer
push directo a `main` como atajo o forzar historia.

### 2.4 Cierre obligatorio

```bash
git ls-remote --heads origin "$BRANCH"
git status --short --branch
```

El operador registra el SHA remoto y deja el worktree limpio. Publicar código y
desplegarlo son acciones distintas: el deploy solo continúa por la sección 3.

### 2.5 Integración temporal y archivado

```bash
# Desde un worktree limpio, sobre el último main remoto
scripts/create_integration_branch.sh origin feature/academy integration/academy-<fecha>

# Resolver y revisar manualmente si el merge deja conflictos; nunca forzar
# la resolución. Ejecutar los gates antes de publicar la rama temporal:
git diff --check
./venv/bin/python scripts/check_branch_contract.py \
  --branch "$(git branch --show-current)" --base origin/main --head HEAD
scripts/push_branch.sh origin "$(git branch --show-current)"

# Tras fusionar la integración verificada a main, conservar la rama propietaria
# y eliminarla solo después de crear el respaldo remoto:
scripts/archive_merged_branch.sh origin integration/academy-<fecha>
```

`archive_merged_branch.sh` solo acepta ramas `integration/*` cuyo SHA ya sea
ancestro de `origin/main`; crea `archive/merged/<rama-normalizada>` con el mismo
SHA y confirma el respaldo antes de borrar la rama temporal. Las ramas de módulo
permanecen activas y las ramas con conflictos no se archivan ni se eliminan.

## 3. Procedimiento de Deploy

### Flujo sectorizado de ramas y push

Cada módulo se publica desde su propia rama y worktree. No se deben empujar
commits de un módulo desde la rama de otro módulo:

| Propietario | Rama |
|---|---|
| Núcleo estructural | `feature/modulo-estructural` |
| Academy | `feature/academy` |
| Mensajería | `feature/messaging` |
| Evangelismo | `feature/evangelism` |
| CMS | `feature/cms` |

Usa el wrapper para que el proceso haga fetch, valide que el worktree está
limpio, mantenga viva la conexión SSH durante el gate y confirme el SHA remoto:

```bash
cd /root/ccf-academy-push
/root/ccf/scripts/push_branch.sh origin feature/academy
```

El wrapper bloquea worktrees sucios, ramas equivocadas y bases remotas
desactualizadas. El hook `pre-push` añade la validación de propietario de
archivos: si Academy toca Evangelismo, CMS u otro módulo, el push se rechaza.

### Pre-Deploy Checklist

- [ ] 1. `git status --short` — sin cambios locales no deseados
- [ ] 2. Tests pasan localmente: `python3 -m pytest tests/ -q --tb=short`
- [ ] 3. Quality gate: `python3 scripts/auditing/quality_gate.py`
- [ ] 4. Production readiness: `python3 scripts/auditing/production_readiness.py --strict`
- [ ] 5. Migraciones Alembic generadas: `alembic revision --autogenerate -m "..."` si aplica
- [ ] 6. Migraciones aplicadas en staging: `alembic upgrade head`
- [ ] 7. Backup de BD ejecutado antes del deploy

### Deploy Paso a Paso (VPS Directo)

```bash
# 1. Backup de producción (OBLIGATORIO)
pg_dump -U ccf_user ccf_production > /root/backups/prod_$(date +%Y%m%d_%H%M%S).sql

# 2. Aplicar migraciones
cd /root/ccf
source venv/bin/activate
alembic upgrade head

# 3. Bajar la app
./stopccf

# 4. Pull del código nuevo
git pull origin main

# 5. Reconstruir frontend si hubo cambios UI
cd /root/ccf/frontend
npm run build

# 6. Reiniciar procesos con PM2
cd /root/ccf
pm2 restart ccf-backend-staging --update-env
pm2 restart ccf-frontend-staging --update-env

# 7. Verificar health checks
curl -f https://elfarocc.tech/healthz
curl -f https://elfarocc.tech/api/system/health
curl -f https://elfarocc.tech/
python3 scripts/auditing/production_readiness.py
```

### Deploy Rápido (Hotfix — solo backend)

```bash
cd /root/ccf
git pull origin main
pm2 restart ccf-backend-staging --update-env
```

> **Nota:** En esta instancia el frontend se sirve con `pm2`. Si hay cambios frontend, se requiere `cd frontend && npm run build` antes de `pm2 restart ccf-frontend-staging --update-env`. No mezclar `pm2` con `./startccf` o con `npm run start` manual.

### Deploy desde worktree alternativo (cuando `/root/ccf` no está en `main`)

> **⚠ Caso especial registrado el 2026-08-05 (ses_030a420dfffe).**
> Aplica cuando el worktree principal `/root/ccf` está en una feature branch con trabajo
> en curso (working tree dirty) y necesitas deployar `main` (u otra rama) **sin perturbar**
> ese trabajo. Es el patrón correcto cuando se trabaja con `git worktree`.

**Por qué el procedimiento normal no alcanza aquí:** el proceso PM2 `ccf-frontend-staging`
tiene `exec cwd: /root/ccf/frontend` y sirve Next.js leyendo `.next` de **ese** directorio.
Si construyes `.next` en un worktree distinto (ej. `/root/ccf-main/frontend/.next`) y solo
haces `pm2 restart ccf-frontend-staging`, el proceso **sigue sirviendo el viejo `.next`**
del cwd PM2. El reinicio no recoge builds de otros worktrees.

```bash
# 1. Crear worktree temporal sobre la rama a deployar (main)
cd /root/ccf
git worktree add /root/ccf-main main

# 2. Instalar deps y build dentro del worktree temporal
cd /root/ccf-main/frontend
npm install --no-audit --no-fund --legacy-peer-deps   # --legacy-peer-deps requerido por
                                                       # conflicto vite/@vitejs/plugin-react
node_modules/.bin/next build                          # exit 0

# 3. Backup del .next que PM2 sirve ahora (punto de rollback)
mv /root/ccf/frontend/.next /root/ccf/frontend/.next.backup-$(date +%Y%m%d-%H%M%S)

# 4. Swap: copiar el nuevo .next al cwd de PM2
cp -a /root/ccf-main/frontend/.next /root/ccf/frontend/.next
#    (paths absolutos embebidos en .next/types/*.ts son dev-only; no afectan runtime)

# 5. Reiniciar frontend (backend NO necesita nada salvo que también haya cambiado)
pm2 restart ccf-frontend-staging
#    Si también cambió el backend: pm2 restart ccf-backend-staging
#    (backend NO tiene el acoplamiento de cwd — reimporta Python al restart, es 1 paso)

# 6. Verificar con fingerprinting de chunk (definitivo)
curl -s https://elfarocc.tech/plataforma/admin/reports | grep -oE 'app/[^"]+/page-[a-z0-9]+\.js' | head -1
#   → extrae ej. "app/plataforma/admin/reports/page-340be6eed4ccfc2a.js"
find /root/ccf/frontend/.next -name "page-340be6eed4ccfc2a.js"   # debe existir
find /root/ccf/frontend/.next.backup-* -name "page-340be6eed4ccfc2a.js" 2>/dev/null
#   NO debe existir en el backup = confirms que se sirve el build NUEVO

# 7. Health checks
curl -f https://elfarocc.tech/healthz
curl -f https://elfarocc.tech/                      # HTTP 200 home público
curl -f -o /dev/null https://elfarocc.tech/plataforma # HTTP 307 (login redirect, esperado)

# 8. Limpiar worktree temporal cuando ya no se necesite
cd /root/ccf
git worktree remove /root/ccf-main --force
git worktree prune
```

> **Rollback** (si el deploy falla o se detecta regresión):
> ```bash
> rm -rf /root/ccf/frontend/.next
> mv /root/ccf/frontend/.next.backup-<TIMESTAMP> /root/ccf/frontend/.next
> pm2 restart ccf-frontend-staging
> ```

> **Verificación alterna rápida:** comparar el `BUILD_ID` servido vs el esperado:
> ```bash
> cat /root/ccf/frontend/.next/BUILD_ID       # build NUEVO
> ls /root/ccf/frontend/.next.backup-*        # backups disponibles
> # El BUILD_ID debe cambiar entre el nuevo y cualquier backup (cada `next build` lo regenera)
> ```

> **Aclaración de "producción" en este VPS:** nginx (`/etc/nginx/sites-available/elfarocc`)
> proxiea `elfarocc.tech` directamente a `127.0.0.1:3000` (frontend) y `127.0.0.1:8000` (backend),
> que son los puertos de `ccf-frontend-staging` y `ccf-backend-staging`. **No existe cluster
> separado de producción** — lo que reinicies en PM2 staging **es** lo que se publica en
> elfarocc.tech. El sufijo "-staging" es un misnomer a nivel PM2.

---

## 4. Rollback

### Rollback Rápido (Cambio de código)

```bash
# 1. Revertir el commit
cd /root/ccf
git revert HEAD --no-edit

# 2. Bajar y subir la app
./stopccf
./startccf

# 3. Verificar
curl -f https://elfarocc.tech/healthz
```

### Rollback Completo (con BD)

```bash
# ⚠️ PELIGROSO: Solo en caso de pérdida de datos

# 1. Detener la app
./stopccf

# 2. Restaurar backup de BD
psql -U ccf_user ccf_production < /root/backups/prod_YYYYMMDD_HHMMSS.sql

# 3. Revertir migración
alembic downgrade -1

# 4. Revertir código
git checkout <commit-anterior>

# 5. Subir la app
./startccf

# 6. Verificar
curl -f https://elfarocc.tech/healthz
curl -f https://elfarocc.tech/api/system/health
```

---

## 5. Monitoreo y Alertas

### Comandos de Diagnóstico

```bash
# Estado de procesos
./stopccf --status        # o ver .started_pids
pm2 list                  # solo si esta instancia usa PM2

# Readiness global
cd /root/ccf
python3 scripts/auditing/production_readiness.py
cat test_artifacts/production_readiness.md

# Logs del backend
tail -f /root/ccf/backend.log

# Logs del frontend
tail -f /root/ccf/frontend.log

# Logs de nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Estado de PostgreSQL
systemctl status postgresql
pg_isready

# Conexiones activas a la BD
psql -U ccf_user ccf_production -c "SELECT count(*) FROM pg_stat_activity;"

# Queries lentas
psql -U ccf_user ccf_production -c "SELECT query, calls, total_time FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

### Síntomas y Acciones

| Síntoma | Acción |
|---|---|
| `500` en endpoints | Verificar `backend.log` + `./stopccf && ./startccf` |
| Frontend no carga | Verificar `frontend.log` + puerto `:3000` con `lsof -i :3000` |
| BD caída | `systemctl restart postgresql` |
| SSL expirado | `certbot renew` |
| Disco lleno | `du -sh /root/ccf/` — limpiar logs viejos, `.next/cache` |
| App no arranca | Verificar `.env`, puertos libres, `ps aux \| grep uvicorn` |

---

## 6. Procedimientos de Emergencia

### Pérdida de Datos

1. **NO ejecutar más operaciones de escritura**
2. `./stopccf`
3. Backup inmediato del estado actual (incluso si está corrupto)
4. Restaurar desde el último backup válido
5. Post-mortem

### Token JWT Comprometido

1. Rotar `SECRET_KEY` en `.env`
2. `./stopccf && ./startccf`
3. Forzar re-login a todos los usuarios

### Servidor No Responde

1. Conectarse por SSH al VPS
2. Verificar `htop` por uso de CPU/memoria
3. Verificar `df -h` por espacio en disco
4. Verificar `systemctl status nginx postgresql`
5. Si es necesario: `reboot` y luego `./startccf`

---

## 7. Mantenimiento Programado

### Tareas Semanales

- [ ] Revisar logs de errores: `grep -i error backend.log | tail -20`
- [ ] Verificar espacio en disco: `df -h`
- [ ] Verificar backups automáticos existen

### Tareas Mensuales

- [ ] Rotar credenciales de servicios
- [ ] Actualizar dependencias (patch releases)
- [ ] Revisar y archivar logs antiguos
- [ ] Probar restauración de backup
- [ ] Renovar SSL si es necesario: `certbot renew --dry-run`

### Tareas Trimestrales

- [ ] Revisión de accesos y permisos
- [ ] Optimización de queries lentas
- [ ] Actualizar documentación
- [ ] Auditar seguridad del VPS

---

> **"La preparación de hoy evita la crisis de mañana."**
>
> Documento vivo — actualizar tras cada incidente o deploy mayor.
