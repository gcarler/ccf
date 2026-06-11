# Plan de Acción para Producción — Proyecto CCF

> Revisión original: 2026-05-21. Actualizado al estado real: 2026-06-10.
> Stack: VPS directo (sin Docker/Kubernetes). FastAPI + PostgreSQL 15 + Next.js + nginx.

---

## Fase 0: Correcciones de Seguridad Críticas ✅ COMPLETADA

### 0.1 — Reducir expiración de tokens JWT ✅ HECHO
**Archivos:** `backend/core/config.py:24-29`

| Campo | Valor actual |
|---|---|
| `access_token_expire_minutes` | 15 min |
| `refresh_token_expire_days` | 180 días (estilo Gmail) |

Valores aplicados. Refresh token rotation disponible vía `/auth/refresh`.

### 0.2 — Eliminar credenciales hardcodeadas ✅ HECHO
**Archivo:** `backend/core/config.py:18-21`

Default actual es `sqlite:///./ccf_dev.db` (solo dev local). El validator bloquea SQLite en entornos `production`/`staging`. Producción lee `DATABASE_URL` desde `.env`.

### 0.3 — Desactivar debug logging de autenticación ✅ HECHO
**Archivo:** `backend/api/auth.py`

No quedan logs `[AUTH DEBUG]` en auth.py. Logging de login usa nivel estándar sin exponer qué usuarios existen.

### 0.4 — Forzar `encryption_key` en producción ✅ HECHO
**Archivo:** `backend/core/config.py:98-99`

Validator activo: lanza `ValueError` si `ENCRYPTION_KEY` no está definida en entornos `production`/`prod`/`staging`.

### 0.5 — Email verification y password reset ✅ HECHO
**Archivo:** `backend/api/auth.py`

Endpoint `POST /verify-email` implementado. `backend/services/email` implementado con `render_verify_email`/`send_email`. Tablas `verification_tokens` y `reset_tokens` activas. Google OAuth retorna 501 si no está configurado (comportamiento documentado).

---

## Fase 1: Endurecimiento de Configuración

### 1.1 — Unificar driver de base de datos
**Archivos:** `requirements.txt`, `alembic.ini`

La plataforma corre en VPS directo (sin Docker ni contenedores). El driver es `psycopg2` en producción.

| Ubicación | Driver |
|---|---|
| `requirements.txt` | `psycopg2-binary` (producción) |
| `alembic.ini` | `psycopg2` |
| Dev local | SQLite vía `ccf_dev.db` |

**Acción pendiente:** confirmar que `requirements.txt` no incluye `pg8000` innecesariamente y que `alembic.ini` apunta al `DATABASE_URL` correcto desde `.env`.

### 1.2 — Endurecer defaults de Settings
**Archivo:** `backend/core/config.py`

- `access_token_cookie_secure` es `False` por defecto — debe sobreescribirse a `True` en `.env` de producción
- `redis_url` por defecto apunta a `localhost:6379` — validar que `.env` de producción lo sobreescriba si Redis corre en otra interfaz

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

### 2.3 — Mantener archivos SQLite fuera del repositorio
`ccf_dev.db` es la base de datos local de desarrollo (SQLite). Verificar que `.gitignore` incluya `*.db` y `*.db.bak` para que no se cometan al repositorio.

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

## Fase 3: Infraestructura y Despliegue

### 3.1 — EventBus Redis/Kafka opcional ✅ HECHO
**Archivo:** `backend/core/events.py`

`EventBus` abstracto implementado con prioridad Redis > Kafka > no-op. Kafka es opcional: se activa solo si `KAFKA_BOOTSTRAP_SERVERS` está definido y `kafka-python` está instalado. Sin Redis ni Kafka, corre en modo no-op sin error.

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

### 3.4 — Migraciones antes del deploy (VPS)
La plataforma NO usa Kubernetes ni Helm. El procedimiento de deploy es VPS directo.

Antes de cada deploy que incluya migraciones:
```bash
# En el VPS, antes de reiniciar la plataforma:
cd /root/ccf
source venv/bin/activate
alembic upgrade head
./stopccf && ./startccf
```

Ver procedimiento completo en `docs/RUNBOOK_PRODUCCION.md`.

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

## Resumen de Prioridades (Estado 2026-06-10)

| Fase | Estado | Pendiente |
|---|---|---|
| **Fase 0** — Seguridad crítica | ✅ Completada | — |
| **Fase 1** — Configuración | Parcial | 1.1 verificar `requirements.txt`; 1.2 `.env` prod con `cookie_secure=True` |
| **Fase 2** — Calidad de código | Parcial | 2.1 TypeScript strict; 2.4-2.5 gitignore limpio |
| **Fase 3** — Infraestructura | Parcial | 3.2 async SQLAlchemy; 3.3 rate limiter multi-worker |
| **Fase 4** — Tests y QA gates | Pendiente | Tests de seguridad, refresh token rotation |
| **Fase 5** — Deuda técnica | Pendiente | Ver `docs/PLAN_SANEAMIENTO_DEUDA_LEGACY_CCF.md` |

---

## Pipeline de Release (VPS)

```
git pull origin main
↓
alembic upgrade head   (si hay migraciones)
↓
./stopccf && ./startccf
↓
curl -f http://127.0.0.1:8000/healthz
```

Ver procedimiento completo (incluyendo rollback) en `docs/RUNBOOK_PRODUCCION.md`.
