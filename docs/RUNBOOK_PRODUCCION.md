# Runbook de Operaciones — Plataforma CCF v3.0

**Fecha:** 2026-08-21 (revisado; última revisión previa: 2026-06-05)
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
7. [Flujo de Eventos: Registro → Email QR → Check-in](#7-flujo-de-eventos-registro--email-qr--check-in)

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

## 2. Procedimiento de Deploy

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

## 7. Flujo de Eventos: Registro → Email QR → Check-in

> **Veredicto de revisión (2026-08-21):** esta sección se añadió para cerrar la
> brecha de documentación operativa del flujo de pre-registro de eventos masivos
> (p.ej. el **Aniversario 40 Años CCF** en `/aniversario40`). Los detalles de
> diseño viven en `docs/PLAN_PREREGISTRO_EVENTOS_MASIVOS.md` y
> `docs/AUDITORIA_FORENSE_EVENT_REGISTRATION.md`; aquí está lo que necesita un
> operador en producción.

### 7.1 Visión del flujo

```
Anuncio (CMS /aniversario40) ──► /public/events/{id}/register (form dinámico)
        │  POST /api/public/events/{id}/register   (rate-limited por IP)
        ▼
EventRegistration = CONFIRMED (o WAITLIST si capacity_max lleno)
        │  _issue_qr() → token CCF-EVT- (NUNCA persistido plano; solo sha256 en qr_token_hash)
        │  _issue_cancel_token() → CCF-CXL- (hash en extras._cancel_token_hash)
        ▼
Email corporativo con QR PNG embebido (plantilla render_event_confirmation_email)
        │  img src = {base}/api/public/events/{id}/qr.png?token=…&cancel=…
        ▼
Día del evento: scanner/check-in con require_evangelism:edit
        │  POST /api/evangelism/events/{id}/sessions/{fecha}/ccf-evt-checkin
        ▼
EventAttendance(attended=True, role_at_event)  +  reg → CHECKED_IN
```

### 7.2 Endpoints involucrados

**Público** (`backend/api/public.py`, prefix `/api/public`):

| Endpoint | Uso | Notas operativas |
|---|---|---|
| `GET /events/{id}` | Detalle del evento (ventana de registro, capacidad) | `PUBLIC_EVENT_RATE_LIMIT` |
| `POST /events/{id}/identify` + `/identify/verify` | Flujo “ya soy parte de CCF” (token single-use) | consume `event_identity_challenges` |
| `POST /events/{id}/register` | Pre-registro con form dinámico (`form_data`) | Idempotente; validación server-side del `CmsForm` vinculado; hCaptcha si `form.captcha_enabled` |
| `GET /events/{id}/verify` | Verificación por email (24h) | Token `CCF-VER-` |
| `GET /events/{id}/ticket` | Ticket público por token QR | **Hash-bound**: busca por `qr_token_hash`, nunca por token plano |
| `GET /events/{id}/qr.png` | Imagen PNG del QR para el email | `?token=…&cancel=…`; 200 `image/png`; token inválido → 404; status ≠ CONFIRMED/CHECKED_IN → 409 |
| `GET /events/{id}/status` | Consulta de inscripción por email | No expone PII (correcto por diseño) |
| `POST /events/{id}/cancel` | Auto-cancelación con token | Token de cancelación expira a las 72h desde `qr_generated_at`; libera el cupo y promueve waitlist |

**Admin / check-in** (`backend/api/evangelism_events/`, requieren `evangelism:edit` + alcance de sede):

| Endpoint | Uso | Notas operativas |
|---|---|---|
| `POST /events/{id}/registrations/{reg_id}/resend-confirmation` | Reenviar email con QR | Usa `resolve_public_base_url()` — nunca `""` ni placeholder |
| `POST /events/{id}/sessions/{fecha}/ccf-evt-checkin` | Check-in por QR de inscripción `CCF-EVT-` | Persiste `role_at_event` (rol contextual); idempotente (`is_duplicate=True`) |
| `POST /events/{id}/sessions/{fecha}/checkin` | Check-in unificado (`CCF-EVT-`, `CCF-PER-`, `persona_id`, walk-in) | Idempotente por `(event_id, session_date, persona_id)`; evento CANCELLED → 409 |

### 7.3 Configuración de email (`.env`)

| Variable | Valor en prod | Efecto |
|---|---|---|
| `smtp_host` / `smtp_port` | `smtp.gmail.com` / `587` | Relay SMTP |
| `smtp_use_tls` | `True` | STARTTLS obligatorio |
| `smtp_user` / `smtp_password` | credenciales de app Gmail | AUTH LOGIN (validar con `smtplib` si falla el envío) |
| `smtp_from_email` / `smtp_from_name` | remitente corporativo | Remitente visible del email |
| `frontend_url` | `https://ministerioselfaro.org` | **Dominio canónico** |
| `public_base_url` | *(vacío)* | Si vacío → usa `frontend_url`; **nunca** cae al placeholder `https://ccf.co` |
| `environment` | `staging`/`production` | El validator fuerza credenciales fuertes; fuera de `local` los emails se envían reales |
| `stub_comms` | `False` | Si `True` **no sale ningún email** (solo `CommunicationLog`); excepción: `test_email_override` |
| `test_email_override` | *(vacío)* | Única dirección que recibe email real con `stub_comms=True` |

> **Verificación rápida del dominio de los links QR** (defecto histórico corregido 2026-08-21):
> ```bash
> cd /root/ccf && ./venv/bin/python -c "from backend.core.config import get_settings; s=get_settings(); print(s.public_base_url or s.frontend_url)"
> # Debe imprimir https://ministerioselfaro.org — nunca https://ccf.co
> ```

### 7.4 Datos de respaldo (PostgreSQL)

- `event_registrations` — `registration_status` (`CONFIRMED`, `WAITLIST`, `CHECKED_IN`, `CANCELLED`), `qr_token_hash` (sha256, el único token persistido), `extras._cancel_token_hash`, `extras._form_data` (respuestas del form dinámico), `source` (`public_form`/…).
- `event_attendances` — asistencia del día (`attended`, `check_in_at`, `scanned_at`, `role_at_event`).
- `personas` — upsert por email/phone en el registro público.
- `crm_events.capacity_max` — aforo; al llenarse los nuevos registros van a **waitlist** y se promueven automáticamente al cancelarse un cupo (`_promote_first_waitlist`, con email propio).

```sql
-- Cupos ocupados vs aforo (para el Aniversario 40 u otro evento)
SELECT e.name, e.capacity_max,
       COUNT(r.id) FILTER (WHERE r.registration_status IN ('CONFIRMED','CHECKED_IN')) AS ocupados,
       COUNT(r.id) FILTER (WHERE r.registration_status = 'WAITLIST') AS waitlist
FROM crm_events e
LEFT JOIN event_registrations r ON r.event_id = e.id AND r.deleted_at IS NULL
WHERE e.id = '<EVENT_UUID>'
GROUP BY e.id, e.name, e.capacity_max;
```

### 7.5 Operaciones comunes

- **Reenviar QR a un inscrito**: endpoint admin `resend-confirmation` (UI del módulo evangelismo). Verifica en el email reenviado que la URL del QR comience con `https://ministerioselfaro.org` (nunca relativa ni `ccf.co`).
- **Cupo liberado por cancelación**: la fila pasa a `CANCELLED` (no se borra) y el siguiente de la waitlist recibe su email de confirmación con QR automáticamente.
- **Verificación post-deploy del flujo completo** (smoke):
  ```bash
  # 1. Registro público (form con captcha desactivado en dev/test; en prod puede requerir hCaptcha)
  curl -s -X POST https://ministerioselfaro.org/api/public/events/<ID>/register \
    -H 'Content-Type: application/json' \
    -d '{"first_name":"Smoke","last_name":"Test","email":"<TU_CORREO>","form_data":{…}}'
  # → status CONFIRMED + qr_token (transitorio, solo en la respuesta)
  # 2. Ticket y PNG del QR
  curl -s -o /dev/null -w '%{http_code}\n' 'https://ministerioselfaro.org/api/public/events/<ID>/ticket?token=<qr_token>'
  curl -s -o /dev/null -w '%{http_code}\n' 'https://ministerioselfaro.org/api/public/events/<ID>/qr.png?token=<qr_token>'
  # 3. Check-in (con JWT de evangelism:edit)
  curl -s -X POST 'https://ministerioselfaro.org/api/evangelism/events/<ID>/sessions/2026-08-23/ccf-evt-checkin' \
    -H "Authorization: Bearer <JWT>" -H 'Content-Type: application/json' \
    -d "{\"qr_token\": \"<qr_token>\"}"
  # 4. Limpiar el registro de prueba (borrar fila de event_registrations + persona)
  ```

> **Requisito operativo del usuario de check-in** (verificado en el smoke 2026-08-21):
> el JWT necesita `evangelism:edit` **y** el usuario debe pertenecer a la **misma sede
> del evento** (`require_event_access` compara `user.sede_id` con `event.sede_id`
> y devuelve 404 si difieren; no hay jerarquía de sedes en el modelo actual).
> Buscar candidato con: `SELECT u.id, u.email FROM auth_users u WHERE u.sede_id = '<SEDE_DEL_EVENTO>' AND u.is_active = true;`

### 7.6 Troubleshooting

| Síntoma | Causa probable | Acción |
|---|---|---|
| El email de confirmación no llega | `stub_comms=True`; SMTP caído; credenciales rotas | Verificar `stub_comms`/`test_email_override` en `.env`; `tail -f backend.log` (el envío loguea warning `Failed to send confirmation email`); probar AUTH con `smtplib` |
| Link del QR apunta a otro dominio o es relativo | `public_base_url`/`frontend_url` mal configurados; `resend_confirmation` con URL base vacía | Verificar sección 7.3; reenviar el QR desde el admin |
| El QR del email no muestra imagen | Imagen bloqueada por el cliente (URL relativa) o endpoint `qr.png` caído | Verificar `GET /api/public/events/{id}/qr.png` (200 `image/png`); el token se valida hash-bound |
| `422` al registrar | Form dinámico inválido o `CmsForm` inactivo/eliminado | Validar `form_data` contra los campos del form; verificar `form.is_active` |
| Check-in devuelve `403` | QR inválido (hash no coincide) o token expirado | El QR expira a los `QR_EXPIRY_DAYS` (365 días) desde `qr_generated_at`; usar `resend-confirmation` |
| Check-in devuelve `409` | Evento `CANCELLED` o inscripción no activa | Verificar `crm_events.status`; los borrados soft no admiten check-in |
| Registro va a waitlist sin aviso | `capacity_max` lleno | Promoción automática al cancelar; revisar SQL de 7.4 |

---

> **"La preparación de hoy evita la crisis de mañana."**
>
> Documento vivo — actualizar tras cada incidente o deploy mayor.
