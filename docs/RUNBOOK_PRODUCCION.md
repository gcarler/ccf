# Runbook de Operaciones — Plataforma CCF v3.0

**Fecha:** 2026-06-02  
**Autor:** Equipo de Arquitectura CCF  
**Audiencia:** DevOps, SRE, DBA, Desarrolladores Backend  

---

## 📋 Índice

1. [Arquitectura del Sistema](#1-arquitectura-del-sistema)
2. [Procedimiento de Deploy](#2-procedimiento-de-deploy)
3. [Rollback](#3-rollback)
4. [Monitoreo y Alertas](#4-monitoreo-y-alertas)
5. [Escalamiento](#5-escalamiento)
6. [Procedimientos de Emergencia](#6-procedimientos-de-emergencia)
7. [Mantenimiento Programado](#7-mantenimiento-programado)
8. [Contactos](#8-contactos)

---

## 1. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUARIOS                                │
│              (Web, Mobile, Agentes IA)                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────────┐
│                    NGINX / Load Balancer                        │
│         (SSL termination, rate limiting, static files)          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│                    FRONTEND (Next.js)                           │
│              (Vercel / Kubernetes / Docker)                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │ apiFetch → /api/*
┌───────────────────────────▼─────────────────────────────────────┐
│                    BACKEND (FastAPI)                            │
│         (3+ replicas, auto-scaling, health checks)              │
└───────────────────────────┬─────────────────────────────────────┘
                            │ SQLAlchemy + psycopg2
┌───────────────────────────▼─────────────────────────────────────┐
│                    POSTGRESQL (Primary + Replica)               │
│         (RDS / Cloud SQL / Managed Postgres)                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│              REDIS (Cache + Sessions + PubSub)                  │
└─────────────────────────────────────────────────────────────────┘
```

### Componentes Críticos

| Componente | Tecnología | Réplicas | Health Check |
|---|---|---|---|
| Frontend | Next.js 14 | 2+ | `/` → 200 |
| Backend | FastAPI + Python 3.12 | 3+ | `/healthz` → 200 |
| Base de Datos | PostgreSQL 15 | 1 primary + 1 replica | `pg_isready` |
| Cache | Redis 7 | 2 (master + replica) | `PING` → PONG |
| Storage | S3 / MinIO | — | — |

---

## 2. Procedimiento de Deploy

### Pre-Deploy Checklist

- [ ] 1. Todos los tests pasan (`pytest tests/ -q`)
- [ ] 2. Cobertura ≥ 70% (`pytest --cov=backend --cov-fail-under=70`)
- [ ] 3. Bandit sin vulnerabilidades HIGH/CRITICAL (`bandit -r backend/`)
- [ ] 4. Migraciones Alembic generadas y revisadas (`alembic revision --autogenerate -m "..."`)
- [ ] 5. `.env` actualizado en todos los entornos
- [ ] 6. Backup de BD ejecutado antes del deploy

### Deploy Paso a Paso

#### 2.1 Staging

```bash
# 1. Backup de staging
pg_dump $DATABASE_URL > backups/staging_$(date +%Y%m%d_%H%M%S).sql

# 2. Aplicar migraciones
alembic upgrade head

# 3. Deploy backend
kubectl set image deployment/ccf-backend backend=ccf/backend:${VERSION}
kubectl rollout status deployment/ccf-backend

# 4. Deploy frontend
kubectl set image deployment/ccf-frontend frontend=ccf/frontend:${VERSION}
kubectl rollout status deployment/ccf-frontend

# 5. Verificar health checks
curl -f https://staging.ccfministerio.com/healthz
curl -f https://staging.ccfministerio.com/api/healthz

# 6. Smoke tests
pytest tests/test_smoke.py -v
```

#### 2.2 Producción (Blue-Green)

```bash
# 1. Backup de producción (OBLIGATORIO)
pg_dump $DATABASE_URL > backups/prod_$(date +%Y%m%d_%H%M%S).sql

# 2. Pausar tráfico al entorno blue
kubectl patch service ccf-backend -p '{"spec":{"selector":{"version":"green"}}}'

# 3. Aplicar migraciones (sin downtime con CONCURRENTLY)
alembic upgrade head

# 4. Deploy al entorno blue
kubectl set image deployment/ccf-backend-blue backend=ccf/backend:${VERSION}
kubectl rollout status deployment/ccf-backend-blue

# 5. Verificar health checks en blue
curl -f https://prod.ccfministerio.com/healthz

# 6. Cambiar tráfico a blue
kubectl patch service ccf-backend -p '{"spec":{"selector":{"version":"blue"}}}'

# 7. Monitorear métricas (5 minutos)
# - Error rate < 0.1%
# - P95 latency < 500ms
# - CPU usage < 70%

# 8. Si todo OK, actualizar green como backup
kubectl set image deployment/ccf-backend-green backend=ccf/backend:${VERSION}
```

---

## 3. Rollback

### Rollback Rápido (Emergencia)

```bash
# 1. Revertir tráfico al entorno anterior
kubectl patch service ccf-backend -p '{"spec":{"selector":{"version":"green"}}}'

# 2. Verificar que green aún funciona
curl -f https://prod.ccfministerio.com/healthz

# 3. Notificar al equipo
# Slack: #alerts-ccf
# Email: on-call@ccfministerio.com
```

### Rollback Completo (con BD)

```bash
# ⚠️ PELIGROSO: Solo en caso de pérdida de datos

# 1. Detener todo el tráfico
kubectl scale deployment ccf-backend --replicas=0
kubectl scale deployment ccf-frontend --replicas=0

# 2. Restaurar backup de BD
psql $DATABASE_URL < backups/prod_YYYYMMDD_HHMMSS.sql

# 3. Revertir migraciones
alembic downgrade -1  # o downgrade a versión específica

# 4. Deploy versión anterior
docker pull ccf/backend:${PREVIOUS_VERSION}
kubectl set image deployment/ccf-backend backend=ccf/backend:${PREVIOUS_VERSION}

# 5. Restaurar tráfico
kubectl scale deployment ccf-backend --replicas=3
kubectl scale deployment ccf-frontend --replicas=2
```

---

## 4. Monitoreo y Alertas

### Métricas Clave

| Métrica | Umbral de Alerta | Severidad |
|---|---|---|
| Error rate (5xx) | > 0.5% en 5 min | CRITICAL |
| P95 latency | > 1000ms en 5 min | HIGH |
| P99 latency | > 2000ms en 5 min | HIGH |
| CPU usage | > 80% en 10 min | MEDIUM |
| Memory usage | > 85% en 10 min | MEDIUM |
| DB connections | > 80% del pool | HIGH |
| Disk usage | > 85% | CRITICAL |
| Redis memory | > 90% | HIGH |

### Dashboards

- **Grafana:** https://grafana.ccfministerio.com/d/ccf-overview
- **Datadog / CloudWatch:** CCF-Production dashboard
- **Sentry:** https://sentry.ccfministerio.com/projects/ccf-backend

### Logs

```bash
# Logs del backend
kubectl logs -l app=ccf-backend --tail=100 -f

# Logs de errores
kubectl logs -l app=ccf-backend | grep -E "ERROR|CRITICAL|500"

# Logs de autenticación sospechosa
kubectl logs -l app=ccf-backend | grep -E "LOGIN_FAILED|Unauthorized|403"
```

---

## 5. Escalamiento

### Niveles de Severidad

| Nivel | Descripción | Respuesta | Notificación |
|---|---|---|---|
| P1 (CRITICAL) | Plataforma caída, pérdida de datos | Inmediato (15 min) | PagerDuty + Slack #alerts-ccf |
| P2 (HIGH) | Funcionalidad crítica afectada | 1 hora | Slack #alerts-ccf |
| P3 (MEDIUM) | Degradación de performance | 4 horas | Slack #dev-ccf |
| P4 (LOW) | Bug menor, workaround disponible | 24 horas | Jira ticket |

### Runbook por Síntoma

#### "Endpoint de listado lento (>2s)"
1. Verificar N+1 queries: `EXPLAIN ANALYZE` en queries lentas
2. Verificar índices faltantes: `	d+ tabla` en psql
3. Verificar cache hit rate en Redis
4. Escalar réplicas de backend si CPU > 70%

#### "Error 500 masivo"
1. Verificar logs: `kubectl logs -l app=ccf-backend --tail=500`
2. Verificar estado de BD: `pg_isready`, conexiones activas
3. Verificar Redis: `redis-cli PING`
4. Rollback si error está en código nuevo

#### "Fuga de datos entre sedes"
1. Verificar filtros `sede_id` en endpoints afectados
2. Verificar queries directas sin `WHERE sede_id = ?`
3. Aplicar hotfix inmediato
4. Auditar logs de acceso

---

## 6. Procedimientos de Emergencia

### Pérdida de Datos

1. **NO ejecutar más operaciones de escritura**
2. Backup inmediato del estado actual (incluso si está corrupto)
3. Restaurar desde el último backup válido
4. Auditar quién/qué causó la pérdida
5. Post-mortem en 24 horas

### Token JWT Comprometido

1. Rotar `SECRET_KEY` inmediatamente
2. Invalidar todos los refresh tokens
3. Forzar re-login a todos los usuarios
4. Auditar sesiones sospechosas

### Ataque DDoS

1. Activar rate limiting agresivo en CloudFlare / WAF
2. Escalar réplicas de backend
3. Activar modo "sólo lectura" si es necesario
4. Contactar proveedor de CDN

---

## 7. Mantenimiento Programado

### Tareas Diarias
- [ ] Revisar logs de errores (Sentry)
- [ ] Verificar backups automáticos
- [ ] Revisar métricas de performance

### Tareas Semanales
- [ ] Análisis de queries lentas (pg_stat_statements)
- [ ] Revisar índices no utilizados
- [ ] Verificar espacio en disco
- [ ] Revisar alertas de seguridad (Dependabot, Snyk)

### Tareas Mensuales
- [ ] Rotar credenciales de servicios
- [ ] Actualizar dependencias (patch releases)
- [ ] Revisar y archivar logs antiguos
- [ ] Prueba de restauración de backup

### Tareas Trimestrales
- [ ] Penetration test
- [ ] Revisión de accesos y permisos
- [ ] Optimización de queries críticas
- [ ] Actualización de documentación

---

## 8. Contactos

| Rol | Nombre | Email | Teléfono | PagerDuty |
|---|---|---|---|---|
| On-Call Principal | — | on-call@ccfministerio.com | — | Primary |
| Arquitecto de Software | — | arquitectura@ccfministerio.com | — | Secondary |
| DBA Principal | — | dba@ccfministerio.com | — | Secondary |
| DevOps Lead | — | devops@ccfministerio.com | — | Secondary |
| Security Lead | — | security@ccfministerio.com | — | Escalation |

### Canales de Comunicación

- **Emergencias:** #alerts-ccf (Slack) + PagerDuty
- **Incidentes:** #incidents-ccf (Slack)
- **General:** #dev-ccf (Slack)
- **Email:** dev-team@ccfministerio.com

---

> **"La preparación de hoy evita la crisis de mañana."**
>
> Documento vivo — actualizar tras cada incidente o deploy mayor.
