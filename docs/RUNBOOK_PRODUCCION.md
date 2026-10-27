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
│   Dominio: ministerioselfaro.org                                │
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
| `/etc/nginx/sites-available/ministerioselfaro.org` | Configuración de proxy inverso |
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
SHA y confirma el respaldo antes de borrar la rama temporal. Para ramas antiguas
absorbidas parcialmente usa el helper explicito:

```bash
scripts/archive_branch.sh origin stale feature/security-hardening
```

El helper exige un worktree limpio y que la rama fuente no tenga un worktree activo.
Conserva el SHA exacto bajo `archive/merged/` o `archive/stale/`, verifica el
respaldo remoto y solo despues elimina la rama fuente. El registro visible
`docs/ARCHIVED_BRANCHES.md` marca cada entrada como `ARCHIVADA - NO REACTIVAR`.
Las ramas que aun tengan trabajo rescatable permanecen activas y las ramas con
conflictos no se archivan ni se eliminan.

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

### Backend: versión revisada y estado compartido

El backend usa código de un worktree separado en
`/root/ccf-releases/backend/<SHA40>`. El directorio de trabajo de PM2 continúa
siendo `/root/ccf`: se conservan `.env`, `backend/.env`, `uploads/`, `static/`,
`analytics/` y `backend/data/`. Los dos archivos de entorno se enlazan como
configuración ignorada; los adjuntos, claves VAPID y estado de workspace usan
`CCF_RUNTIME_DIR`. No se reemplaza ningún directorio de código por enlaces.

El starter rechaza el arranque si no existe un puntero de release revisado;
nunca vuelve al checkout mutable por ausencia de configuración.

No es necesario actualizar ningún archivo del checkout mutable para adoptar
este flujo. Ejecutar el helper desde el código limpio revisado. El primer
proceso PM2 puede apuntar a `/root/ccf/scripts/start_backend.sh`; el helper
reapunta su launcher a `scripts/start_backend.sh` del release nuevo, con cwd
`/root/ccf`. Los siguientes launchers deben pertenecer a releases limpios
integrados en `origin/main`; cualquier ruta ajena se rechaza.

La actualización usa un snapshot JSON privado (modo 0600) con un único proceso.
`scripts/rebind_backend_pm2.cjs` lee el snapshot y aplica únicamente la RPC nativa
PM2 `restartProcessId`, dirigida al mismo `pm_id`, con `current_conf` para
launcher, cwd y entorno capturado. El resto de configuración permanece en el
daemon: intérprete, política de reinicios/memoria, logs e identidad. La API
nativa evita que el CLI filtre `pm_exec_path` y evita mezclar variables de
pruebas del shell del despliegue. Se verifica de nuevo identidad, cwd y launcher
antes de emitir la RPC. No se elimina/recrea el proceso ni se reinician otros
servicios. El JSON no se imprime ni se adjunta a logs:
puede contener secretos. Se guarda el estado PM2 tras el smoke satisfactorio. Se requiere Node y el
módulo PM2 instalado; se resuelve localmente o mediante `npm root -g`.
`CCF_PM2_MODULE`, si se usa, debe apuntar a una instalación absoluta confiable.

```bash
# Desde el worktree limpio que contiene los scripts revisados.
# SHA40 corresponde a un commit integrado y validado de origin/main.
CCF_RUNTIME_DIR=/root/ccf bash scripts/deploy_backend.sh <SHA40>
```

La primera adopción exige declarar además una versión estable revisada para
rollback. Debe incluir el soporte `CCF_RUNTIME_DIR` de los cuatro módulos de
adjuntos/estado y los tres helpers de arranque/RPC. El preflight verifica
sintaxis Bash, Python y Node en ambos releases; se rechazan versiones anteriores
para no separar datos al volver atrás. En la primera adopción aún no existe un
launcher de releases probado en servicio: el fallback puede compartir el helper
candidato revisado. Esa limitación inicial se registra; no equivale a disponer
de un launcher anterior probado. En despliegues posteriores, el rollback usa el
launcher limpio anterior, evitando depender del helper nuevo si éste falla. No se deduce del HEAD del checkout porque puede haberse movido
mientras el proceso anterior seguía en memoria:

```bash
CCF_RUNTIME_DIR=/root/ccf bash scripts/deploy_backend.sh <SHA40> \
  --rollback-sha <SHA40-estable-anterior>
```

Sin SHA explícito, el comando resuelve el último `origin/main` tras fetch. Para
CI/CD siempre se pasa el SHA exacto que superó los gates. El helper verifica
que cada release pertenece a `origin/main`, está limpio y coincide con su SHA.
Un lock exclusivo en `/root/ccf-runtime/backend/deploy.lock` impide dos deploys
simultáneos. No hace pull, checkout, reset ni stash del checkout mutable.

Antes de cambiar el puntero o reiniciar, crea un backup PostgreSQL mediante
`scripts/db_backup.sh`, usando la configuración efectiva del proceso vivo. El
backup se verifica con `pg_restore --list`, se guarda con permisos privados en
`/root/ccf-runtime/backend/backups/` y un fallo cancela el despliegue. Las
credenciales no se imprimen ni se pasan por argumentos. No se ejecutan
migraciones automáticamente; si el cambio requiere esquema, su plan reversible
se valida y aplica por separado desde el release limpio, después del backup.

El puntero `/root/ccf-runtime/backend/current.json` se sustituye atómicamente.
El launcher limpio ejecuta uvicorn con `--app-dir` del release, `PYTHONPATH` del
release y cwd canónico. Tras restart, el helper exige un PID nuevo, SHA/ruta de origen
esperados en el proceso y HTTP 200 en `/healthz`. Si falla, restaura el puntero
anterior, reaplica el launcher limpio anterior y comprueba el rollback.
Así tampoco vuelve al launcher del checkout mutable si falla la adopción.
Se conservan los worktrees de release como evidencia y para rollback; no se
eliminan mientras sean origen de código o launcher activo.

Verificación pública, sólo lectura:

```bash
curl -f https://ministerioselfaro.org/healthz
curl -f https://ministerioselfaro.org/api/system/health
```

### Frontend: procedimiento canónico

Ejecutar siempre el wrapper desde un worktree revisado limpio separado del
runtime. No es necesario avanzar ni limpiar `/root/ccf` para desplegar:

```bash
CCF_RUNTIME_DIR=/root/ccf bash /root/ccf-releases/deploy/<SHA40>/scripts/deploy_frontend.sh
curl -f https://ministerioselfaro.org/
curl -I https://ministerioselfaro.org/plataforma
```

El wrapper toma el lock exclusivo externo
`/root/ccf-runtime/frontend/deploy.lock`, comprueba locks locales de Next y
procesos build activos sin borrarlos. Usa las variables del proceso vivo y
archivos de entorno ignorados del runtime, verificando que no cambien durante
la compilación. Instala dependencias en el worktree mediante `npm ci` y construye
mediante el `build-safe` del repositorio. Logs privados:
`/root/ccf-runtime/frontend/build.log`. Nunca compila dentro del cwd servido.

`package.json`, lockfile y todos los assets públicos deben coincidir con el
runtime; si difieren, el deploy se detiene antes del build/restart. Esos cambios
requieren un rollout separado de dependencias/assets, fuera de este flujo. Los
archivos `next.config.*` sólo se sustituyen si siguen idénticos a su HEAD
canónico o a la configuración del último manifest de deploy. Cualquier edición
local desconocida se conserva y bloquea la operación. No se copian otros archivos de
código ni se descartan cambios de otros agentes.

El artefacto se copia primero a `.next-build` del runtime. Se conserva la copia
real servida en `.next-old` y la configuración anterior en
`/root/ccf-runtime/frontend/rollback-config/` hasta que termine el smoke con PID
nuevo y HTTP 200. Si falla promoción, reinicio o smoke, se restauran artefacto y
configuración en el cwd real y se verifica el rollback. Un `.next-old`/staging
previo nunca se borra automáticamente: debe revisarse su propietario y estado.
El manifest privado `frontend/current.json` registra SHA, BUILD_ID y hashes de
configuración. No ejecutar builds, copias de `.next` o reinicios paralelos.

### Workflow de despliegue

`.github/workflows/deploy.yml` sólo acepta CI exitoso de `main` del propio
repositorio o una ejecución manual desde `main` con SHA completo y CI exitoso.
Comprueba que el SHA siga siendo exactamente `origin/main`, crea un worktree
detached y no hace pull/reset/stash del runtime. La concurrencia no cancela un
deploy activo; un lock global del VPS protege también otras ejecuciones.

Antes de tocar el frontend, el preflight backend valida fuente, rollback,
launchers y un backup PostgreSQL. La primera adopción requiere `rollback_sha`.
Si no existe manifest frontend, reconstruye conservadoramente. Después sólo
omite el frontend cuando el manifest demuestra que no hubo cambios en su árbol.
Un fallo frontend evita el restart backend. Backend repite backup y guardas
antes de su propio restart. Finalmente verifica los endpoints públicos.

> **Aclaración de "producción" en este VPS:** nginx (`/etc/nginx/sites-available/ministerioselfaro.org`)
> proxiea `ministerioselfaro.org` directamente a `127.0.0.1:3000` (frontend) y `127.0.0.1:8000` (backend),
> que son los puertos de `ccf-frontend-staging` y `ccf-backend-staging`. **No existe cluster
> separado de producción** — lo que reinicies en PM2 staging **es** lo que se publica en
> ministerioselfaro.org. El sufijo "-staging" es un misnomer a nivel PM2.

---

## 4. Rollback

### Rollback Rápido (Cambio de código)

El backend restaura automáticamente la versión anterior si falla su smoke.
Para un rollback posterior, volver a desplegar el SHA estable revisado con el
mismo helper; se mantiene el backup previo y se comprueba el proceso y HTTP:

```bash
CCF_RUNTIME_DIR=/root/ccf bash scripts/deploy_backend.sh <SHA40-estable>
curl -f https://ministerioselfaro.org/healthz
```

Un rollback de código no revierte datos ni esquema. Si una migración no es
compatible con la versión anterior, seguir el plan reversible de esa migración
antes de cambiar el código. No hacer revert o checkout sobre el árbol mutable.

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
curl -f https://ministerioselfaro.org/healthz
curl -f https://ministerioselfaro.org/api/system/health
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
