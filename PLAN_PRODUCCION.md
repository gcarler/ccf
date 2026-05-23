# Plan de Acción para Producción — Proyecto CCF

> Basado en la revisión de calidad del 2026-05-21.
> Objetivo: Llevar la plataforma a un estado seguro y desplegable en producción.

---

## Fase 0: Correcciones de Seguridad Críticas (Día 1)
*Debe hacerse antes de cualquier despliegue a producción.*

### 0.1 — Reducir expiración de tokens JWT
**Archivos:** `backend/core/config.py:17-18`

| Campo | Valor actual | Valor producción |
|---|---|---|
| `access_token_expire_minutes` | 5,256,000 (10 años) | **30** (30 minutos) |
| `refresh_token_expire_days` | 3,650 (10 años) | **7** (7 días) |

El valor actual de 10 años para access token es una vulnerabilidad crítica: un token robado vale por una década. Implementar refresh token rotation (ya existe el endpoint `/auth/refresh`) mantiene sesiones largas de forma segura.

### 0.2 — Eliminar credenciales hardcodeadas
**Archivo:** `backend/core/config.py:13`

Reemplazar el default de `database_url`:
- **Local:** usar variable de entorno obligatoria o default solo para SQLite en memoria
- **Producción:** forzar lectura desde `.env` o secretos de Kubernetes

```python
# Antes
database_url: str = "postgresql+pg8000://postgres:admin123@localhost:5435/ccf_db"

# Después
database_url: str = Field(default="sqlite:///./dev.db")  # Solo para dev local
```

### 0.3 — Desactivar debug logging de autenticación
**Archivo:** `backend/api/auth.py:41-80`

Los logs `[AUTH DEBUG]` revelan qué usuarios existen. Reemplazar con logging condicional:

```python
if settings.environment not in {"production", "prod", "staging"}:
    log.info(f"Login attempt for: {form_data.username}")
```

O mejor, migrar los logs sensibles a nivel `DEBUG` y configurar el handler de producción en WARNING+.

### 0.4 — Forzar `encryption_key` en producción
**Archivo:** `backend/core/config.py:16`

Agregar validación en `validate_security_defaults`:
```python
if env in {"production", "prod", "staging"} and not self.encryption_key:
    raise ValueError("ENCRYPTION_KEY must be set in production environments")
```

### 0.5 — Stub de email verification y password reset
**Archivo:** `backend/api/auth.py:194-225`

Opción A (rápida): Documentar que no están implementados y devolver error 501 Not Implemented.
Opción B (completa): Implementar con un servicio de email (SendGrid, SES, o SMTP). Usar tablas de `verification_tokens` y `reset_tokens` con expiración.

---

## Fase 1: Endurecimiento de Configuración (Días 2-3)

### 1.1 — Unificar driver de base de datos
**Archivos:** `requirements.txt`, `deploy/helm/ccf/values.yaml`, `alembic.ini`

Decidir entre `psycopg2` (maduro, recomendado para producción) o `pg8000` (pure-Python, más fácil en contenedores slim) y eliminar el otro. Consistencia en:

| Ubicación | Driver actual |
|---|---|
| `requirements.txt` | Ambos |
| `docker-compose.yml` | `pg8000` |
| `backend.Dockerfile` | «libpq-dev» incluido (sugiere psycopg2) |
| `alembic.ini` | `psycopg2` |
| `deploy/helm/*/values.yaml` | `psycopg2` |

**Recomendación:** Usar `psycopg2` en producción (soporte nativo de pool, madurez) y `pg8000` como alternativa ligera para CI.

### 1.2 — Endurecer defaults de Settings
**Archivo:** `backend/core/config.py`

- `access_token_cookie_secure` debe ser `True` por defecto (solo False en local)
- Verificar que `access_token_cookie_name` tenga un valor por entorno
- Validar que `redis_url` no sea localhost en producción

### 1.3 — Verificar que .env esté en .gitignore y exista .env.example completo
**Archivo:** `.gitignore`

Confirmar que `.env` está ignorado. El `.env.example` existe pero debe incluir **todos** los valores requeridos sin defaults inseguros.

---

## Fase 2: Calidad de Código (Días 4-6)

### 2.1 — Activar TypeScript strict mode
**Archivo:** `frontend/tsconfig.json`

```json
"strict": true
```

Preparar 2-3 días para corregir errores de tipado. Hacer por módulos:
1. CRM types primero (más usado)
2. Academy
3. Admin
4. Resto

### 2.2 — Organizar scripts de la raíz
Mover ~40 scripts (`mod_*.py`, `fix_*.py`, `seed_*.py`, `test_*.py`) a directorios:

```
scripts/
  migrations/    → fix_*.py, migrate_*.py, add_col.py, alter_db.py
  seeding/       → seed_*.py, create_admin.py
  dev/           → test_*.py, check_*.py, list_*.py, count_users.py
  mods/          → mod_*.py (parches de frontend/backend generados por IA)
  auditing/      → audit_*.py, security_checker.py, diagnose_schema.py
legacy/          → scripts obsoletos o de una sola ejecución
```

### 2.3 — Eliminar `ccf_v2.db.bak` del repositorio
```bash
git rm --cached ccf_v2.db.bak
echo "*.db.bak" >> .gitignore
```

### 2.4 — Agregar archivos .log al .gitignore y limpiar existentes
```bash
git rm --cached *.log ccf_*.log frontend*.log quality_report.log
```

### 2.5 — Actualizar .gitignore completo
Agregar reglas faltantes:
- `*.db.bak` (existe pero el archivo se coló antes)
- `.run/*.log`
- `test_artifacts/` (existe pero parcial)
- `tmp_*/`
- `*_test_output.txt`

---

## Fase 3: Infraestructura y Despliegue (Días 7-9)

### 3.1 — Hacer Kafka/Redpanda opcional
**Impacto:** Simplifica drásticamente el despliegue.

Crear un `EventBus` abstracto con implementación Redis como default y Kafka como alternativa:

```python
class EventBus:
    async def publish(self, channel: str, data: dict): ...
    async def subscribe(self, channel: str): ...

class RedisEventBus(EventBus): ...   # Usa Redis Streams
class KafkaEventBus(EventBus): ...   # Usa Redpanda/Kafka
```

En `docker-compose.yml`, hacer que `redpanda` sea un servicio opcional (comentado por defecto).

### 3.2 — Migrar a driver async de SQLAlchemy
**Archivo:** `backend/core/database.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
```

Esto permite que FastAPI aproveche su naturaleza asíncrona. Requiere cambiar todos los `Depends(get_db)` a `async def` y todas las queries a sintaxis async. **Es un cambio grande** — considerar hacerlo por módulo.

**Opción rápida:** Usar `pip install asyncer` y `fastapi` con `run_in_executor` para las queries sin reescribir todo.

### 3.3 — Rate limiter multi-worker
**Archivo:** `backend/core/rate_limit.py`

Eliminar el fallback a `MemoryRedis` o al menos advertir explícitamente que no funciona con múltiples workers. Para producción, exigir Redis real.

```python
def rate_limiter(limit: int = 5, window_seconds: int = 60):
    async def dependency(request: Request) -> None:
        redis_client = get_redis()
        if isinstance(redis_client, MemoryRedis):
            # No rate limiting real en multi-worker; log advertencia
            return
        # ... lógica actual
```

### 3.4 — Actualizar Helm charts con valores reales
**Archivo:** `deploy/helm/ccf/values.yaml`

- Reemplazar `app.example.com` por el dominio real
- Verificar que los secrets tengan una fuente real (Vault, External Secrets Operator, o values reales cifrados)
- Agregar `PodDisruptionBudget` y `topologySpreadConstraints` para alta disponibilidad
- Agregar probes de readiness/liveness explícitas (el backend ya tiene `/healthz`)

### 3.5 — Agregar contenedor de migrations en Helm
**Archivo:** `deploy/helm/ccf/templates/migration-job.yaml`

Ya existe el template. Verificar que ejecute Alembic como init container antes del backend:
```yaml
initContainers:
  - name: run-migrations
    image: {{ .Values.backend.image }}
    command: ["alembic", "upgrade", "head"]
```

---

## Fase 4: Pruebas y QA Gates (Días 10-11)

### 4.1 — Agregar test de seguridad de configuración
**Archivo:** `tests/` (nuevo `test_security_config.py`)

```python
def test_production_settings_require_strong_secrets():
    """Verificar que producción no acepta defaults inseguros."""
    with pytest.raises(ValueError):
        Settings(_env_file=None, environment="production")

def test_token_expiry_is_sane():
    """Access tokens no pueden exceder 60 min."""
    s = Settings(environment="production")
    assert s.access_token_expire_minutes <= 60
```

### 4.2 — Agregar quality gate de seguridad al CI
Extender `quality_gate.py` o crear uno nuevo en `.github/workflows/`:

1. Escaneo de secretos hardcodeados (`truffleHog` o `git-secrets`)
2. Verificación de `strict: true` en tsconfig
3. Verificación de que no hay `[AUTH DEBUG]` logs
4. Verificación de que `.env` no contiene credenciales reales

### 4.3 — Agregar test de integración para refresh token rotation
**Archivo:** `tests/test_auth.py`

Test de que al hacer refresh, el token anterior queda invalidado (la función ya existe en `crud.revoke_refresh_token`).

---

## Fase 5: Deuda Técnica y Mantenibilidad (Días 12-14)

### 5.1 — Implementar email service real
Evaluar si se necesita:
- **No se necesita ahora:** Eliminar los endpoints stub y documentar la limitación
- **Sí se necesita:** Usar `fastapi-mail` o integrar con SendGrid/SES con cola en Redis

### 5.2 — Quitar redundancia de startup migrations
**Archivo:** `backend/app.py:301`

`Base.metadata.create_all()` corre en cada startup además de Alembic. Evaluar si se puede eliminar ahora que hay 19 migraciones. Mover la lógica de `_run_startup_migrations` y `_run_data_migrations` a migraciones reales de Alembic.

### 5.3 — Agregar tests de regresión visual con Storybook
Ya existe Storybook configurado y Playwright. Agregar pruebas visuales (`storybook test runner` + `playwright`) para los componentes críticos.

---

## Resumen de Prioridades

| Fase | Tareas | Esfuerzo | Dependencia | ¿Bloqueante para producción? |
|---|---|---|---|---|
| **Fase 0** | 5 tareas de seguridad | 1 día | Ninguna | **SÍ** |
| **Fase 1** | 3 tareas de configuración | 2 días | Fase 0 | SÍ |
| **Fase 2** | 5 tareas de calidad | 3 días | Fase 0 | Parcial |
| **Fase 3** | 5 tareas de infra | 3 días | Fase 1 | Parcial |
| **Fase 4** | 3 tareas de tests | 2 días | Fase 0-2 | No, pero recomendado |
| **Fase 5** | 3 tareas de deuda técnica | 3 días | Fase 2 | No |

**Total estimado:** 14 días hábiles (~3 semanas)

---

## Pipeline de Release

```
Fase 0 → Fase 1 → [TEST] → Fase 3 → [STAGING] → Fase 4 → PRODUCTION
                     ↓
                  Fase 2 (paralelo)
                     ↓
                  Fase 5 (post-producción)
```

**Recomendación:** Hacer Fase 0 + Fase 1 como hotfix branch, desplegar a staging, validar, y luego producción. El resto puede hacerse en paralelo o después del lanzamiento inicial.
