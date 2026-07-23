# Revisión de Calidad — Plataforma CCF

**Fecha:** 2026-07-23
**Revisado por:** Opencode (agente de revisión autónomo)
**Alcance:** Backend, Frontend, Infraestructura, Seguridad, Testing, Documentación

---

## Resumen Ejecutivo

| Métrica | Valor | Estado |
|---------|-------|--------|
| Backend (Python) | ~45,500 líneas en 51+ archivos API | Maduro |
| Frontend (TypeScript/React) | ~141,700 líneas en 684 archivos | Maduro |
| Tests Backend | ~65,300 líneas en 194 archivos | Sólido |
| Tests Frontend | ~5,550 líneas | Insuficiente |
| Cobertura Backend | ~39% (meta: 70%) | CRÍTICO |
| Cobertura Frontend | ~40% (meta: 40%) | En el límite |
| Módulos Backend | 30+ routers API registrados | Maduro |
| Páginas Frontend | 213 rutas mapeadas | Maduro |
| Puntuación Global | **65/100** | ACEPTABLE CON RESERVAS |

---

## 1. Arquitectura y Estructura

### Fortalezas

- **Arquitectura modular bien definida:** El backend sigue un patrón claro de `api/` → `crud/` → `schemas/` → `models_*` con separación de responsabilidades.
- **Kernel de Personas como identidad única:** El Axioma 1 (`personas.id` como identidad canónica UUID) está correctamente implementado y documentado en `REGLAS.md`.
- **Multi-tenancy por sede:** El filtro `sede_id` está ampliamente aplicado con `get_user_sede_id()` y `require_user_sede_id()` en `backend/core/tenant.py`.
- **RBAC robusto:** Sistema de permisos de 3 dimensiones (Ministerio, Rol Iglesia, Rol Plataforma) bien documentado en `GLOSSARY.md` y motor implementado en `backend/core/permissions.py` (760 líneas) y `backend/core/kernel_rbac.py` (238 líneas).
- **Module Isolation Middleware:** Circuito breaker por módulo en `backend/middleware/module_isolation.py` que impide que un módulo caído tumbe al servidor completo.
- **Separación frontend/backend clara:** Next.js 15 + FastAPI con PM2 como gestor de procesos.
- **Documentación arquitectónica exhaustiva:** `REGLAS.md`, `GLOSSARY.md`, `PRODUCTION_READINESS.md`, contratos API por módulo, matrices RBAC, checklists QA.

### Debilidades

- **Fragmentación excesiva de modelos:** 15 archivos `models_*.py` separados (academy_core, agenda, agents, auth, cms, conversation, crm, crm_pipeline, enterprise, evangelism, finance_suite, governance, identity, kernel, knowledge_base, ops, other, projects, shared, system, wiki). Aunque modular, dificulta la navegación y el refactoring.
- **Archivos barrel (`models.py`) con 265 líneas de re-exports:** Genera confusión sobre dónde vive cada modelo.
- **Dualidad de sistemas de roles:** `backend/core/permissions.py` y `backend/core/kernel_rbac.py` implementan sistemas de RBAC superpuestos con lógica de resolución que puede causar inconsistencias.
- **Nomenclatura inconsistente:** Mezcla de español/inglés en nombres de módulos, tablas y campos (ej: `evangelism/grupos_evangelismo`, `crm_casos`, `auth_users`).

---

## 2. Seguridad

### Fortalezas

- **Cifrado de datos en reposo:** Fernet encryption implementado en `backend/core/security.py` con fallback a `ENCRYPTION_KEY`.
- **Headers de seguridad:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, CSP, HSTS (no-local) en `backend/core/security_headers.py`.
- **Rate limiting:** Doble sistema (Redis-based + slowapi) en `backend/core/rate_limit.py` con bypass para pytest y per-user bucketing.
- **Validación de producción:** `Settings.validate_security_defaults()` en `backend/core/config.py` bloquea SECRET_KEY débil, SQLite en no-local, y cookie secure en producción.
- **HTML Sanitization:** Sanitizador whitelist-based sin dependencias externas en `backend/core/sanitize_html.py`.
- **JWT con cookies HttpOnly:** Access token de 15 min + refresh token de 180 días.
- **Bandit en pre-commit:** Escaneo de seguridad estático configurado.
- **Auditoría:** `AdminAuditLog`, `LogSeguridad` y `record_admin_action()` en `backend/core/audit.py`.

### Debilidades

- **ENCRYPTION_KEY no configurado por defecto:** En `.env.example` está vacío. Sin esta key, los datos cifrados usan SECRET_KEY, lo cual es inseguro en producción.
- **CORS amplio en desarrollo:** 8 orígenes localhost en `Settings.cors_origins` — riesgo si `ENVIRONMENT` no se configura correctamente.
- **Mypy no bloquea el CI:** En `ci.yml` línea 65: `mypy backend/ --ignore-missing-imports || true` — los errores de tipo se ignoran.
- **Bandit no bloquea el CI:** En `ci.yml` línea 60: `bandit -r backend/ -f json -o bandit-report.json || true`.
- **Secretos potencialmente expuestos:** En `.bash_history` se observan API keys de NVIDIA en texto plano (línea 1102-1109). Aunque no están en el código fuente, indican práctica insegura.
- **CSP policy lax:** `script-src 'self'` sin `nonce` o `hash` — vulnerable si se inyecta un script en una página.
- **`allow_methods=["*"]` y `allow_headers=["*"]`** en CORS middleware — permisivo de más para producción.

---

## 3. Testing

### Fortalezas

- **Suite extensa de tests backend:** 194 archivos de test, ~65,300 líneas.
- **Pre-commit hooks:** Smoke tests, reglas de plataforma, y backlog check ejecutados antes de cada commit.
- **Nightly regression:** Pipeline completo en `scripts/nightly_regression.sh` con 8 pasos.
- **CI/CD automatizado:** GitHub Actions con quality gate backend, frontend, y migrations check.
- **Conftest robusto:** `tests/conftest.py` (505 líneas) con SQLite UUID patching, circuit breaker reset, cache clearing entre tests, y helpers de autenticación (`seed_admin`, `auth_headers`, `seed_user_with_role`).
- **E2E con Playwright:** Tests de CRM, Academy, Evangelism, Projects, Messaging, Agenda, CMS.
- **Storybook:** Configurado para componentes UI con addon a11y.

### Debilidades

- **Cobertura backend en 39%:** Muy por debajo del objetivo de 70% (`pytest.ini` línea 7). Módulos críticos con baja cobertura:
  - `cms_v2.py`: 21%
  - `pastoral.py`: 15%
  - `pipelines.py`: 22%
  - `projects.py`: 17%
  - `crud/cms.py`: 14%
- **Cobertura frontend mínimo:** Vitest configurado con threshold de 40% lines pero scoped solo a `src/design/**/*.{ts,tsx}` — los componentes reales de la aplicación no se testean con unit tests.
- **Tests e2e frontend débiles:** Solo ~5,550 líneas para 213 páginas.
- **Sin tests de performance/load:** No hay evidencia de benchmarks de rendimiento.
- **Sin tests de seguridad específicos:** No hay tests de inyección SQL, XSS, CSRF, o autorización cross-tenant más allá de los tests de aislamiento de sede.
- **CI coverage threshold bajo en frontend:** Solo 40% en `ci.yml` línea 149.

---

## 4. Frontend

### Fortalezas

- **Stack moderno:** Next.js 15, React 18, TypeScript 5, Tailwind CSS 3, Zustand, React Hook Form.
- **UI Component Library:** Componentes en `src/components/ui/` con Storybook.
- **Diseño system:** Directorio `src/design/` con tests unitarios.
- **Error Boundaries:** `ErrorBoundary.tsx` y `ModuleErrorBoundary.tsx` implementados.
- **Middleware de routing:** Reescritura automática de rutas legacy a `/plataforma/...`.
- **SEO:** Sitemap, robots.txt, metadata, y schema markup.
- **Gestión de estado:** Zustand para stores globales, context providers para Auth, Config, Toast, Theme, Command Center.
- **AG Grid:** Integración de AG Grid para vistas de tabla (CRM, Academy).
- **DnD Kit:** Drag & drop para Kanban boards.
- **TipTap:** Editor de texto rico para contenido.

### Debilidades

- **Provider nesting excesivo:** 7 providers anidados en `layout.tsx` (`AuthProvider > ConfigProvider > ToastProvider > ThemeProvider > CommandCenterProvider > CreationProvider > SidebarLayerProvider`).
- **`"use client"` excesivo:** Muchos componentes que podrían ser Server Components usan `"use client"`.
- **Archivos de test muy escasos:** Solo ~5,550 líneas de tests para 141,700 líneas de código.
- **Sin typecheck estricto en CI:** `tsc --noEmit` ejecuta pero no bloquea (observado en `run_ci.sh` con `|| fail` pero en `ci.yml` sí bloquea).
- **Logs de error en archivos temporales:** Archivos como `frontend-dev-4121.err.log` acumulados en el directorio frontend.
- **`.next.backup-*` directorio:** Indica problemas de build previos que no se limpiaron.

---

## 5. Base de Datos y Migraciones

### Fortalezas

- **Alembic configurado:** Migraciones versionadas en `alembic/` con `canonical_versions/`.
- **CI verifica migraciones:** Pipeline ejecuta `alembic upgrade head` + `alembic downgrade base` + `alembic upgrade head` en `ci.yml`.
- **UUID como PK:** Entidades transaccionales usan UUID (REGLAS.md §5).
- **DateTime timezone-aware:** REGLAS.md §6 especifica `DateTime(timezone=True)` y backend persiste en UTC.
- **Soft deletes:** `deleted_at`, `estado`, `is_active` en vez de hard deletes (REGLAS.md §6).
- **DB backups:** Scripts `db_backup.sh` y `backup_rotate.sh` en `scripts/`.

### Debilidades

- **SQLite en desarrollo:** `.env.example` no especifica PostgreSQL para dev, y `pytest.ini` usa SQLite para tests — puede enmascarar bugs de PostgreSQL.
- **`alembic.ini` hardcodea credenciales:** Línea 6: `sqlalchemy.url = postgresql+psycopg2://postgres:postgres@localhost:5432/ccf_db`.
- **Sin connection pooling configurable:** No hay configuración visible de `pool_size`, `max_overflow`, o `pool_recycle` en el engine de SQLAlchemy.

---

## 6. CI/CD y Deploy

### Fortalezas

- **Pipeline completo:** `ci.yml` con 3 jobs paralelos (backend-quality, frontend-quality, migrations-check) + deploy staging/production.
- **Deploy automatizado:** `deploy.yml` ejecuta SSH deploy tras CI exitoso en main.
- **PM2 con defensas anti-loop:** `ecosystem.config.cjs` con `max_restarts`, `min_uptime`, `exp_backoff_restart_delay`, y `kill_timeout`.
- **Pre-commit hooks:** 8 hooks configurados (trailing-whitespace, ruff, bandit, pytest smoke, reglas_plataforma, academy backlog).
- **Scripts de calidad por módulo:** 16+ scripts `test_*_quality.py` en `scripts/`.

### Debilidades

- **Deploy es `git pull + pm2 restart`:** Sin build reproducible en staging, sin verificación post-deploy automatizada, sin healthcheck gate.
- **Sin containerización:** No hay Dockerfile o docker-compose — depende de configuración manual del VPS.
- **GitHub Actions deploy es un echo:** Línea 231 de `deploy.yml`: `run: echo "🚀 Deploy to production would run here"`.
- **No hay rollback automatizado:** El runbook describe rollback manual.
- **Sin feature flags en runtime:** `feature_flags.py` lee de `Settings.feature_flags` (dict vacío por defecto) pero no hay UI de administración.

---

## 7. Documentación

### Fortalezas

- **Documentación extrema:** 138 archivos en `docs/` incluyendo contratos API, matrices RBAC, checklists QA, auditorías forenses, planes de calidad por módulo, y runbook de producción.
- **Glosario oficial:** `GLOSSARY.md` con 100 líneas definiendo términos del dominio y términos prohibidos.
- **REGLAS.md:** 193 líneas de reglas arquitectónicas verificables con comandos.
- **PRODUCTION_READINESS.md:** Gate ejecutable con script `production_readiness.py`.
- **COBERTURA_FRONTEND_BACKEND.md:** Mapeo detallado de 213 rutas frontend a endpoints backend.

### Debilidades

- **Documentación posiblemente desactualizada:** Con 138 archivos y desarrollo activo, la documentación puede tener drift.
- **Sin generación automática de API docs:** No se observa Swagger/ReDoc configurado en el FastAPI app (solo el título/descripción en `app.py`).
- **Comentarios de código escasos en backend:** La directiva del proyecto es "DO NOT ADD COMMENTS unless asked" — resultado: código funcional pero con poca documentación inline.

---

## 8. Rendimiento y Escalabilidad

### Fortalezas

- **Redis caching:** Sistema de caché con `@cached` decorator y `MemoryRedis` fallback para testing.
- **Rate limiting per-user:** Bucketing por user_id o IP, con bypass para managers.
- **OpenTelemetry integrado:** Tracing distribuido configurable en `backend/core/telemetry.py`.
- **Image optimization:** Sharp para WebP conversion, Pillow para resize.
- **Background tasks:** YouTube cache warming, knowledge base rebuild, y event consumers en lifespan.

### Debilidades

- **`MemoryRedis` como fallback:** En producción sin Redis, el cache y rate limiting no funcionan correctamente — el warning en `rate_limit.py` línea 50 lo confirma.
- **Caché en memoria del módulo:** `_system_var_cache` en `cms_v2.py` es un dict a nivel de módulo — no se invalida entre workers.
- **Sin connection pooling visible:** No hay configuración explícita de SQLAlchemy pool.
- **Knowledge base rebuild en startup:** `indexer.rebuild_all()` en cada arranque del servidor — costoso con datos grandes.
- **`lru_cache()` en `get_settings()`:** Los settings se cachean para siempre — problemático si las env vars cambian durante runtime.

---

## 9. Code Quality

### Fortalezas

- **Ruff como linter:** Configurado en `pyproject.toml` con reglas E, W, F, I.
- **Formatting consistente:** ruff-format + Prettier en frontend.
- **Pre-commit hooks:** 8 hooks ejecutados antes de cada commit.
- **TypeScript strict mode:** `tsconfig.json` con `"strict": true`.
- **ESLint configurado:** Con plugins de Next.js, Prettier, y Storybook.

### Debilidades

- **51 archivos en `backend/api/`:** Muchos archivos monolíticos (ej: `evangelism_reports.py` de 14,633 bytes, `members.py` de 752 líneas).
- **`|| true` en CI:** Errores de mypy y bandit se ignoran activamente.
- **Archivos temporales de debug:** `.run/`, logs de frontend dev, `lint_output.txt`, `ts_report.txt` acumulados en el repo.
- **Dependencias desactualizadas potenciales:** `bcrypt==4.0.1` (pin exacto), `slowapi==0.1.10` — versions hardcodeadas que pueden acumular CVEs.

---

## 10. Accesibilidad (A11y)

### Fortalezas

- **Storybook addon a11y:** Configurado con `@storybook/addon-a11y`.
- **axe-core integration:** `@axe-core/playwright` en devDependencies.
- **ACAD-TKT-204 a11y gate:** Test específico `test_academy_fase_7_tkt_204_a11y_gate.py`.

### Debilidades

- **Sin Lighthouse CI:** No hay medición automatizada de accesibilidad.
- **Testing a11y limitado:** Solo un gate específico de Academy.
- **`suppressHydrationWarning` en layout.tsx:** Puede enmascarar problemas de hidratación.

---

## Recomendaciones Prioritarias

### CRÍTICAS (Impacto alto, esfuerzo medio-alto)

1. **Subir cobertura backend a >=70%:** Los módulos cms_v2 (21%), pastoral (15%), pipelines (22%), projects (17%), crud/cms (14%) son los gaps más grandes. Priorizar tests de integración para estos módulos.
2. **Configurar ENCRYPTION_KEY obligatorio en staging/prod:** Ya está validado en el model_validator pero `.env.example` lo deja vacío. Documentar generación.
3. **Hacer que mypy y bandit bloqueen el CI:** Cambiar `|| true` a `|| exit 1` en `ci.yml`.
4. **Containerizar la aplicación:** Crear Dockerfile multi-stage para backend y frontend. Eliminar dependencia de configuración manual del VPS.
5. **Implementar healthchecks post-deploy:** El `deploy.yml` actual es un echo. Agregar verificación de `/healthz` y smoke test.

### IMPORTANTES (Impacto alto, esfuerzo bajo-medio)

6. **Agregar unit tests al frontend:** Actualmente solo `src/design/` tiene tests. Priorizar componentes de CRM, Academy, y Auth.
7. **Swagger/ReDoc habilitado:** Agregar `app = FastAPI(..., docs_url="/api/docs", redoc_url="/api/redoc")`.
8. **Limpiar archivos temporales del repo:** Agregar `.gitignore` para logs de dev, lint_output, test_artifacts.
9. **Configurar connection pooling:** Agregar `pool_size`, `max_overflow`, `pool_recycle` al engine de SQLAlchemy.
10. **Unificar sistemas RBAC:** Decidir entre `permissions.py` y `kernel_rbac.py` como fuente única de verdad.

### MENORES (Impacto bajo, esfuerzo bajo)

11. **Eliminar directories `.next.backup-*`** y logs de dev accumulados.
12. **Externalizar secretos de `alembic.ini`:** Usar env var en vez de hardcodear.
13. **Agregar Lighthouse CI** al pipeline de frontend.
14. **Configurar dependabot/renovate** para mantener dependencias actualizadas.
15. **Reducir provider nesting** en `layout.tsx` usando compound patterns o reducer.

---

## Matriz de Madurez por Módulo

| Módulo | Backend | Tests | Frontend | Docs | Nota |
|--------|---------|-------|----------|------|------|
| Auth v3 | Maduro | Bueno | Maduro | Excelente | A+ |
| CRM | Maduro | Bueno | Maduro | Bueno | A |
| Academy | Maduro | Excelente | Maduro | Excelente | A+ |
| Evangelismo | Maduro | Bueno | Maduro | Bueno | A |
| CMS v2 | Maduro | Débil | Maduro | Bueno | B |
| Projects | Maduro | Débil | Maduro | Bueno | B |
| Finance | Maduro | Medio | Parcial | Medio | B- |
| Admin | Maduro | Bueno | Maduro | Bueno | A |
| Community | Maduro | Medio | Maduro | Medio | B |
| Support/KB | Maduro | Medio | Parcial | Medio | B- |
| Governance | Maduro | Medio | Maduro | Medio | B |
| Wiki | Maduro | Medio | Maduro | Medio | B |
| Spiritual Life | Maduro | Medio | Maduro | Medio | B |
| Graph | Maduro | Débil | Parcial | Medio | C+ |
| Agents/AI | Maduro | Medio | Maduro | Bueno | B |
| Messaging | Maduro | Bueno | Maduro | Bueno | A- |

---

## Conclusión

La plataforma CCF es un sistema **maduro y bien arquitecturado** con documentación excepcional, un kernel de personas sólido, multi-tenancy robusto, y una suite de testing extensa. Los puntos más débiles son la **cobertura de tests** (especialmente frontend), la **falta de containerización**, y la **pendencia de hacer que las herramientas de calidad bloqueen el CI**. La deuda técnica acumulada es manejable y los fundamentos arquitectónicos permiten escalar con confianza.

**Prioridad inmediata:** Subir cobertura backend a 70%, containerizar, y activar mypy/bandit como gates de CI.
