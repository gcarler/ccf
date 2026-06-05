# Runbook de Operaciones — Plataforma CCF v3.0

**Fecha:** 2026-06-05
**Autor:** Equipo de Arquitectura CCF  
**Audiencia:** DevOps, Desarrolladores Backend, Administradores

---

## 📋 Índice

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Procedimiento de Deploy](#2-procedimiento-de-deploy)
3. [Rollback](#3-rollback)
4. [Monitoreo y Alertas](#4-monitoreo-y-alertas)
5. [Procedimientos de Emergencia](#5-procedimientos-de-emergencia)
6. [Mantenimiento Programado](#6-mantenimiento-programado)

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
| Frontend | Next.js 14 | `:3000` | `./startccf` (npm run start) |
| Backend | FastAPI + Python 3.12 | `:8000` | `./startccf` (uvicorn) |
| Base de Datos | PostgreSQL 15 | `:5432` | `systemctl postgresql` |
| Proxy | nginx | `:443` / `:80` | `systemctl nginx` |
| Repositorio | Git (VPS `/root/ccf`) | — | `git pull origin main` |

### Archivos Clave

| Archivo | Propósito |
|---|---|
| `/root/ccf/startccf` | Arranca backend + frontend en background con `_launch_detached()` |
| `/root/ccf/stopccf` | Detiene procesos de forma limpia con `_kill_with_verify()` |
| `/etc/nginx/sites-available/elfarocc.tech` | Configuración de proxy inverso |
| `/root/ccf/.env` | Variables de entorno (DB, secretos, API keys) |

---

## 2. Procedimiento de Deploy

### Pre-Deploy Checklist

- [ ] 1. `git status --short` — sin cambios locales no deseados
- [ ] 2. Tests pasan localmente: `python3 -m pytest tests/ -q --tb=short`
- [ ] 3. Quality gate: `python3 scripts/auditing/quality_gate.py`
- [ ] 4. Migraciones Alembic generadas: `alembic revision --autogenerate -m "..."` si aplica
- [ ] 5. Migraciones aplicadas en staging: `alembic upgrade head`
- [ ] 6. Backup de BD ejecutado antes del deploy

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

# 5. Subir la app
./startccf

# 6. Verificar health checks
curl -f https://elfarocc.tech/healthz
curl -f https://elfarocc.tech/api/system/health
curl -f https://elfarocc.tech/
```

### Deploy Rápido (Hotfix — solo backend)

```bash
cd /root/ccf
git pull origin main
./stopccf
./startccf
```

> **Nota:** El frontend se compila en CI y se copia al VPS. Si el hotfix es solo backend, no necesita rebuild de frontend. Si hay cambios frontend, se requiere `cd frontend && npm run build` antes de `./startccf`.

---

## 3. Rollback

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

## 4. Monitoreo y Alertas

### Comandos de Diagnóstico

```bash
# Estado de procesos
./stopccf --status        # o ver .started_pids

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

## 5. Procedimientos de Emergencia

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

## 6. Mantenimiento Programado

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
