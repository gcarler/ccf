# CMS v2 — Runbook de Operaciones

> **Módulo:** CMS v2 (Centro Cristiano Faro)
> **Última actualización:** 2026-07-31
> **Audiencia:** DevOps, Backend Dev, On-Call

> **📖 Para el equipo editorial:** ver [Checklist Editorial — Sitio Público Editable desde el CMS](./CHECKLIST_EDITABILIDAD_PUBLICO_EDITORIAL.md) para saber qué textos e imágenes se editan desde el CMS y dónde.

---

## Tabla de Contenidos

1. [Arquitectura del Módulo](#1-arquitectura-del-módulo)
2. [Arranque y Detención](#2-arranque-y-detención)
3. [Deploy](#3-deploy)
4. [Rollback](#4-rollback)
5. [Troubleshooting Común](#5-troubleshooting-común)
6. [Variables de Entorno](#6-variables-de-entorno)
7. [Monitoreo y Logs](#7-monitoreo-y-logs)
8. [Backup y Restauración](#8-backup-y-restauración)

---

## 1. Arquitectura del Módulo

```
┌─────────────────────────────────────────────────┐
│  Frontend (React/Vite)                          │
│  frontend/src/app/plataforma/cms/               │
│  → CMS Builder, Editor, Media Library           │
├─────────────────────────────────────────────────┤
│  API Backend (FastAPI)                          │
│  backend/api/cms_v2/ (paquete refactorizado)    │
│    ├── __init__.py         (router orchestrator)│
│    ├── _shared.py          (helpers compartidos)│
│    ├── section_types.py    (tipos de sección)   │
│    ├── global_blocks.py    (bloques globales)   │
│    ├── sites.py            (sites CRUD)         │
│    ├── themes_menus.py     (temas + menús)      │
│    ├── pages.py            (páginas + secciones)│
│    ├── public.py           (endpoints públicos) │
│    ├── posts.py            (categorías + posts) │
│    ├── analytics_ops.py    (tracking + ops)     │
│    ├── forms.py            (formularios)        │
│    ├── newsletter.py       (newsletter)         │
│    ├── popups.py           (popups nativos)     │
│    ├── presence.py         (presencia real-time)│
│    └── ab_testing.py       (A/B testing)        │
├─────────────────────────────────────────────────┤
│  CRUD Layer                                     │
│  backend/crud/cms.py                            │
├─────────────────────────────────────────────────┤
│  Modelos y Schemas                              │
│  backend/models_cms.py                          │
│  backend/schemas/cms_v2_sections.py             │
│  backend/exceptions/cms.py                      │
└─────────────────────────────────────────────────┘
```

**Base de datos:**
- Producción: PostgreSQL (ver `DATABASE_URL` en `.env`)
- Desarrollo: SQLite (`ccf_dev.db`)

**Prefijos de rutas:**
- Admin: `/api/cms/v2/...`
- Público: `/api/cms/v2/public/sites/{site_key}/...`

---

## 2. Arranque y Detención

### Desarrollo

```bash
# Arrancar backend + frontend (dev mode)
cd /root/ccf
./startccf-dev

# Detener
./stopccf-dev

# Solo backend
cd /root/ccf && source .venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Solo frontend
cd /root/ccf/frontend
npm run dev
```

### Producción (PM2)

```bash
# Arrancar todos los servicios
cd /root/ccf
./startccf

# Detener todos los servicios
./stopccf

# Ver estado de todos los procesos PM2
pm2 status

# Ver logs en tiempo real
pm2 logs ccf-backend
pm2 logs ccf-frontend
```

---

## 3. Deploy

### Deploy Manual

```bash
# 1. Hacer pull de los últimos cambios
cd /root/ccf
git pull origin main

# 2. Actualizar dependencias backend (si hubo cambios en requirements.txt)
source .venv/bin/activate
pip install -r requirements.txt

# 3. Correr migraciones de base de datos
alembic upgrade head

# 4. Actualizar dependencias frontend (si hubo cambios en package.json)
cd frontend && npm install

# 5. Build del frontend
npm run build

# 6. Reiniciar servicios
cd /root/ccf
./stopccf
./startccf

# 7. Verificar que los servicios están corriendo
pm2 status
curl -s http://localhost:8000/health | jq .
```

### Verificación post-deploy

```bash
# Verificar health del backend
curl http://localhost:8000/health

# Verificar endpoint público CMS
curl "http://localhost:8000/api/cms/v2/public/sites/faro/theme" | jq .status

# Verificar que el sitemap responde
curl -I "http://localhost:8000/api/cms/v2/public/sites/faro/sitemap.xml"

# Correr smoke tests E2E
cd /root/ccf/frontend
npm run test:e2e:cms
```

---

## 4. Rollback

### Rollback de Código

```bash
# Identificar el commit anterior estable
git log --oneline -10

# Revertir al commit anterior
git revert HEAD --no-commit
git commit -m "revert: rollback a commit anterior por incidencia"

# O checkout a un tag específico
git checkout tags/v1.2.3 -b rollback-v1.2.3

# Rebuild y redeploy
cd frontend && npm run build
cd /root/ccf && ./stopccf && ./startccf
```

### Rollback de Base de Datos

```bash
# Ver migraciones aplicadas
alembic history

# Revertir la última migración
alembic downgrade -1

# Revertir a una revisión específica
alembic downgrade 20260710_0002

# Restaurar desde backup (ver Sección 8)
```

### Checklist de Rollback

- [ ] Identificar el commit/tag estable al que revertir
- [ ] Hacer backup de la BD antes del rollback
- [ ] Ejecutar `alembic downgrade` si la migración nueva es incompatible
- [ ] Hacer checkout/revert del código
- [ ] Rebuild frontend
- [ ] Reiniciar servicios
- [ ] Verificar health endpoints
- [ ] Comunicar el estado al equipo

---

## 5. Troubleshooting Común

### Error: `500 Internal Server Error` en endpoints CMS

**Síntomas:** Todos los endpoints CMS devuelven 500.

**Diagnóstico:**
```bash
# Ver logs del backend
pm2 logs ccf-backend --lines 50

# Buscar errores de importación
grep -i "importerror\|modulenot" /root/ccf/logs/backend.log | tail -20

# Verificar que el módulo CMS carga
python3 -c "from backend.api.cms_v2 import router; print('OK')"
```

**Solución más común:** Import circular o error de sintaxis en un submódulo de `cms_v2/`.
```bash
python3 -c "from backend.api import cms_v2" 2>&1
```

---

### Error: `403 Forbidden` en operaciones de admin CMS

**Síntomas:** Un editor recibe 403 en operaciones que debería poder hacer.

**Diagnóstico:**
```bash
# Verificar roles del usuario en la BD
# (reemplazar <user_id> con el ID del usuario)
sqlite3 ccf_dev.db "SELECT r.name FROM roles r JOIN user_roles ur ON ur.role_id = r.id WHERE ur.user_id = '<user_id>';"
```

**Causa más común:** El usuario no tiene el rol `CMS_EDITOR` o `CMS_PUBLISHER` asignado.

**Solución:**
```bash
# En el admin de la plataforma: Usuarios → [usuario] → Roles → Agregar CMS_EDITOR
```

---

### Error: Sección con `props_json` inválido

**Síntomas:** `422 Unprocessable Entity` al guardar una sección.

**Diagnóstico:**
```bash
# Ver el schema del tipo de sección
grep -A 20 "class HeroProps\|SECTION_PROPS_SCHEMAS" backend/schemas/cms_v2_sections.py | head -40
```

**Solución:** Validar el `props_json` contra el schema Pydantic correspondiente al `section_type`.

---

### Error: Sitemap XML no genera páginas

**Síntomas:** El sitemap está vacío o solo muestra el sitio raíz.

**Diagnóstico:**
```bash
# Verificar que hay páginas publicadas
sqlite3 ccf_dev.db "SELECT slug, status FROM cms_pages WHERE status = 'published' LIMIT 10;"
```

**Causa:** No hay páginas con `status = 'published'` en el site.

---

### Error: N+1 queries en producción (alto tiempo de respuesta)

**Síntomas:** El endpoint `public_page` o `public_posts_list` tarda > 2 segundos.

**Diagnóstico:**
```bash
# Habilitar SQL logging temporalmente
SQLALCHEMY_ECHO=1 uvicorn backend.main:app --port 8001

# Monitorear queries
curl "http://localhost:8001/api/cms/v2/public/sites/faro/pages/home" 2>&1 | grep "SELECT" | wc -l
```

**Si el conteo de queries es > 5 por request, revisar:**
1. Si se introdujo un nuevo loop sobre resultados de BD
2. Si `_get_system_vars_batch` está siendo bypasseado
3. Ver `docs/cms_query_metrics.md` para referencia de queries esperadas

---

### Error: `409 Conflict` al crear página con slug duplicado

**Síntomas:** Al crear una página, recibe `{"detail": "Slug already exists"}`.

**Causa:** El slug ya existe en el mismo site.

**Solución:**
```bash
# Verificar qué página tiene ese slug
sqlite3 ccf_dev.db "SELECT id, title, status FROM cms_pages WHERE slug = 'mi-slug' AND site_id = 'site-id';"
```

---

### Error: Media Library — imágenes no se suben

**Síntomas:** El upload de imágenes falla con `500` o `413`.

**Diagnóstico:**
```bash
# Verificar directorio de uploads
ls -la /root/ccf/uploads/
df -h /root/ccf/uploads/

# Verificar límite de tamaño de archivo en nginx
grep -i "client_max_body_size" /etc/nginx/sites-enabled/default
```

**Solución:** Ajustar `client_max_body_size` en nginx si los archivos son > 10MB.

---

## 6. Variables de Entorno

Las variables críticas del CMS están en `/root/ccf/.env`:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DATABASE_URL` | URL de conexión a PostgreSQL | `postgresql://user:pass@localhost/ccf` |
| `SECRET_KEY` | JWT secret | `your-secret-key-here` |
| `FRONTEND_URL` | URL pública del frontend | `https://app.ccf.com` |
| `STORAGE_PATH` | Directorio de uploads | `/root/ccf/uploads` |
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo de upload | `50` |

Ver `.env.example` para la lista completa con descripciones.

---

## 7. Monitoreo y Logs

### Logs de Aplicación

```bash
# Backend
pm2 logs ccf-backend
tail -f /root/ccf/logs/backend.log

# Frontend build
tail -f /root/ccf/logs/frontend.log

# Logs de nginx (si aplica)
tail -f /var/log/nginx/access.log | grep "/api/cms"
```

### Métricas Clave a Monitorear

| Métrica | Threshold de Alerta | Endpoint |
|---|---|---|
| Tiempo de respuesta `public_page` | > 500ms | `/api/cms/v2/public/sites/*/pages/*` |
| Tiempo de respuesta `public_posts_list` | > 300ms | `/api/cms/v2/public/sites/*/posts` |
| Rate de errores 5xx | > 1% | Cualquier endpoint `/api/cms` |
| Tamaño del directorio de uploads | > 80% del disco | `/root/ccf/uploads` |

### Analytics CMS

El módulo CMS incluye tracking de page views. Ver `backend/api/cms_v2/analytics_ops.py`.

```bash
# Consultar page views del último día
sqlite3 ccf_dev.db "SELECT page_id, COUNT(*) as views FROM cms_page_views WHERE created_at > datetime('now', '-1 day') GROUP BY page_id ORDER BY views DESC LIMIT 10;"
```

---

## 8. Backup y Restauración

### Backup de Base de Datos

```bash
# Backup SQLite (desarrollo)
cp /root/ccf/ccf_dev.db /root/ccf/backups/ccf_dev_$(date +%Y%m%d_%H%M%S).db

# Backup PostgreSQL (producción)
pg_dump ccf_db > /root/ccf/backups/ccf_db_$(date +%Y%m%d_%H%M%S).sql
```

### Backup de Media

```bash
# Comprimir directorio de uploads
tar -czf /root/ccf/backups/uploads_$(date +%Y%m%d_%H%M%S).tar.gz /root/ccf/uploads/
```

### Restaurar Base de Datos

```bash
# Restaurar SQLite
cp /root/ccf/backups/ccf_dev_20260731_000000.db /root/ccf/ccf_dev.db

# Restaurar PostgreSQL
psql ccf_db < /root/ccf/backups/ccf_db_20260731_000000.sql
```

### Restaurar Media

```bash
tar -xzf /root/ccf/backups/uploads_20260731_000000.tar.gz -C /root/ccf/
```

---

## Contactos y Escalación

| Rol | Responsabilidad |
|---|---|
| Backend Dev | Errores de API, migraciones, rendimiento |
| Frontend Dev | Errores de UI, build, E2E tests |
| DevOps / On-Call | Infraestructura, nginx, PM2, backups |

---

*Este runbook es un documento vivo. Actualizar cuando se detecten nuevos patrones de incidencias.*
