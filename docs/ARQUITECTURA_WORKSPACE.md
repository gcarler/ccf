# Arquitectura del Módulo Workspace — CCF

> **TL;DR:** El módulo Workspace es la infraestructura transversal de la plataforma: feature flags, incidencias, compliance, auditoría y config del espacio de trabajo. Este documento es la guía canónica de arquitectura y reglas de negocio. Cualquier agente que vaya a tocar el módulo debe leer este documento primero.

**Última actualización:** 2026-08-02
**Estado del módulo:** ✅ PEND-WORKSPACE-001 cerrado — los snapshots de feature flags quedan fuera del árbol de git (archivos regenerables no se versionan).

---

## 1. Mapa del módulo

El módulo vive en `backend/api/workspace*.py` con helpers compartidos en el paquete `backend/api/workspace_shared/`:

| Archivo | Responsabilidad |
|---|---|
| `backend/api/workspace.py` | Router raíz + agregación de sub-routers |
| `backend/api/workspace_flags.py` | Feature flags: `PUT /flags`, `PUT /flags/rules/{id}` |
| `backend/api/workspace_incidents.py` | Incidencias: listado, scan, update, cleanup, export |
| `backend/api/workspace_compliance.py` | Compliance: snapshots, policy, suppressions, history, drift |
| `backend/api/workspace_config.py` | Config del workspace |
| `backend/api/workspace_audit.py` | Lectura del audit trail |
| `backend/api/workspace_shared/` | Helpers puros (flags, incidents, snapshots, storage, audit) |

### 1.1 Estructura del paquete `workspace_shared`

```
backend/api/workspace_shared/
├── __init__.py     ← paths (DATA_DIR), constantes, DEFAULT_WORKSPACE_CONFIG, re-exports
├── _flags.py       ← normalización de features/rules/rollout
├── _incidents.py   ← severidad, anomalías, trends, fingerprints
├── _snapshots.py   ← construcción de snapshots de compliance, drift, hash
├── _storage.py     ← persistencia en backend/data (config, incidents, audit, notifications, history)
└── _audit.py       ← enriquecimiento/filtrado del audit trail
```

Otros archivos clave:

| Archivo | Rol |
|---|---|
| `backend/core/file_lock.py` | Lock por archivo + escritura de `feature_flags.json` |
| `backend/scheduler.py` | Emisión periódica de snapshots (runtime) |
| `tests/test_workspace_*.py` | Suite de tests (246 tests, ver §6) |

---

## 2. Criterio canónico: *archivos regenerables no se versionan*

> **Regla de oro del módulo Workspace:** cualquier archivo de estado que el código **regenera en runtime** NO debe estar trackeado en git. Se documenta con un patrón en `.gitignore` y el código debe tolerar su ausencia (fallback a defaults).

### 2.1 Los 5 snapshots de feature flags

`backend/api/workspace_shared/__init__.py` define `DATA_DIR` y 5 archivos de estado en `backend/data/`:

| Archivo | Contenido | Escritor runtime | Ausente → fallback |
|---|---|---|---|
| `feature_flags.json` | Config activa del workspace (features_enabled, feature_rules, compliance_policy) | `_storage.py:_save_workspace_config` + `file_lock.py` | `DEFAULT_WORKSPACE_CONFIG` (en código) |
| `feature_flags_incidents.json` | Incidencias persistidas | `_storage.py:_save_incidents` | `[]` |
| `feature_flags_audit.ndjson` | Audit trail (append) | `_storage.py:_append_audit_event` | `[]` |
| `feature_flags_notifications.ndjson` | Notificaciones (append) | `_storage.py:_append_notification` | `[]` |
| `feature_flags_snapshot_history.ndjson` | Historial de snapshots (append) | `_storage.py:_append_snapshot_history` / `_save_snapshot_history` | `[]` |

> **Nota:** solo `workspace_shared/_storage.py` y `backend/core/file_lock.py` escriben en `backend/data/`. Los demás `open(...,"wb")` del backend (media en `comments.py`, `core/storage.py`, `public.py`, `chat.py`) escriben en `uploads_root`, NO en `backend/data/`.

### 2.2 Patrones de `.gitignore` (canónicos)

```gitignore
backend/data/feature_flags*.ndjson
backend/data/feature_flags*.json
```

**Regla:** al añadir un snapshot nuevo, agregar su patrón aquí — no versionarlo.

### 2.3 Contrato de tolerancia a ausencia (clone fresco)

- Un clone fresco de CI **no tiene** los 5 archivos (no están trackeados).
- El código debe arrancar sin ellos: los loads caen a defaults (`DEFAULT_WORKSPACE_CONFIG`, `[]`) y los saves regeneran los archivos bajo demanda (`DATA_DIR.mkdir(parents=True, exist_ok=True)`).
- **Gate de validación:** la suite de workspace (246 tests: audit/flags/incidents/snapshots/storage/system/api) debe pasar **verde con los archivos movidos** (simulando clone fresco), y `git status` debe quedar limpio después de correrla.
- Smoke de arranque: `from backend.main import app` debe importar OK sin los archivos (validado 2026-08-02).

### 2.4 Cierre PEND-WORKSPACE-001 (2026-08-02)

Des-trackeados vía `git rm --cached` (quedan en disco, cubiertos por `.gitignore`):

| Commit | Alcance |
|---|---|
| `b087353e` | 3 × `feature_flags_*.ndjson` (audit, notifications, snapshot_history) |
| `6a55e0a1` | 2 × `feature_flags.json` + `feature_flags_incidents.json` |

En `main`, `git ls-tree main backend/data/` = **0 archivos trackeados**. Los archivos siguen en disco y se regeneran bajo demanda.

### 2.5 Riesgo conocido: merge de branch paralelo

> El branch `feature/whiteboard-superpro` (sesión paralela) aún trackea los 5 archivos y su `.gitignore` solo tiene el patrón `*.ndjson`. Al mergear a `main` habrá conflictos **delete/modify** en los 5. **Resolución correcta:** aceptar la eliminación (`git rm --cached`) y quedarse con el `.gitignore` de `main` — NO re-añadir los archivos. Después del merge, re-correr el gate de clone fresco (246 tests).

---

## 3. Modelo de datos

El módulo Workspace **no usa tablas SQL** para flags/incidents: persiste en archivos JSON/NDJSON en `backend/data/` (ver §2). La config de features es:

```
DEFAULT_WORKSPACE_CONFIG = {
    "features_enabled": {...},      # command_center, knowledge_graph, web_vitals_dashboard, ...
    "ui_theme_config": {...},
    "navigation_schema": [],
    "feature_rules": {...},         # roles_allow/deny, users_allow/deny, rollout_percent
    "compliance_policy": {...},
}
```

Reglas de merge al cargar: `feature_rules` y `compliance_policy.environments` se mergean **deep** sobre los defaults (no se reemplazan por completo). `critical_feature_flags` se unifica por sort.

---

## 4. Reglas de negocio

### 4.1 RBAC

Todos los endpoints de flags/incidents/compliance exigen `require_admin`. Rate limiting por endpoint (`rate_limiter`).

### 4.2 Compliance snapshot

- `GET /flags/compliance/snapshot?record=true` construye y (por defecto) **registra** un snapshot firmado en `feature_flags_snapshot_history.ndjson` (hash sha256 + `snapshot_id`).
- El drift se calcula contra el snapshot previo (`_maybe_emit_snapshot_drift_alert`).
- `notifications.ndjson` solo se materializa al emitir alertas de drift — en un primer arranque fresco puede no existir (append-on-demand).

### 4.3 Timestamps

- `datetime.now(timezone.utc)` — nunca `datetime.utcnow()`.

---

## 5. RBAC (resumen)

| Endpoint | Permiso |
|---|---|
| flags / incidents / compliance | `require_admin` |
| exports (json/csv) | `require_admin` + rate limit |

---

## 6. Tests y verificación

### 6.1 Smoke canónico

```bash
cd /root/ccf && source venv/bin/activate
python scripts/test_workspace_quality.py
```

### 6.2 Suite de workspace (246 tests validados)

```bash
cd /root/ccf && source venv/bin/activate
python -m pytest -q --no-header -o addopts= -p no:cacheprovider --no-cov \
  tests/test_workspace_audit.py tests/test_workspace_flags.py \
  tests/test_workspace_incidents.py tests/test_workspace_snapshots.py \
  tests/test_workspace_storage.py tests/test_system_final.py \
  tests/test_workspace_api.py
```

> `test_workspace_storage_extended.py` (cobertura extra de storage) no estaba en la corrida validada de 246; añadirlo suma más tests.

### 6.3 Gate de clone fresco (imprescindible tras cambios de storage)

```bash
# 1. Mover los 5 archivos fuera (simula clone fresco)
mkdir -p /tmp/ff_backup && mv backend/data/feature_flags* /tmp/ff_backup/
# 2. Correr la suite (debe pasar en verde)
python -m pytest -q --no-cov tests/test_workspace_*.py
# 3. Restaurar y verificar arbol limpio
mv /tmp/ff_backup/* backend/data/ && git status --short
```

---

## 7. Reglas para agentes que trabajan en Workspace

1. **Leer este documento antes de tocar el módulo.**
2. **Nunca versionar un archivo regenerable:** si el código escribe un archivo en runtime, agregar su patrón a `.gitignore` y verificar el fallback de load.
3. **Respetar el gate de clone fresco** (§6.3) tras cualquier cambio de storage.
4. **`datetime.now(timezone.utc)`** — nunca `datetime.utcnow()`.
5. **VENV OBLIGATORIO:** `cd /root/ccf && source venv/bin/activate` antes de cualquier `pytest`/`uvicorn`.
6. **Commit style:** `chore(workspace): ...` / `fix(workspace): ...` / `docs(workspace): ...`.

---

## 8. Documentos relacionados

| Documento | Rol |
|---|---|
| `docs/ARQUITECTURA_WORKSPACE.md` (este) | Guía canónica de arquitectura y reglas de negocio |
| `docs/ESTADO_WORKSPACE.md` | Estado operativo, backlog (PEND/DONE-WORKSPACE-001) |
| `docs/AUDITORIA_TRANSVERSAL_WORKSPACE.md` | Auditoría transversal del módulo |
| `docs/WORKSPACE_QA_CHECKLIST.md` | Checklist de QA |

---

## 9. Comandos rápidos

```bash
# Estado de los snapshots (nada debe estar trackeado en main)
git ls-tree main --name-only backend/data/

# Suite de workspace
cd /root/ccf && source venv/bin/activate
python -m pytest -q --no-cov tests/test_workspace_*.py

# Smoke de arranque sin snapshots
python -c 'from backend.main import app; print("app OK")'
```
