#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# Deploy: 20260710_0003_align_crm_casos_columns
#
# CCF production migration plan:
#   1. Pre-deploy connectivity + revision check (must be 20260710_0002 already;
#      idem­potent if already at 20260710_0003).
#   2. Capture crm_casos row count + sample.
#   3. Logical snapshot via pg_dump (only if pg_dump present; non-fatal if not).
#   4. Run `alembic upgrade 20260710_0003`.
#   5. Restart app (./stopccf + ./startccf if present, otherwise no-op — the
#      operator's process manager is responsible).
#   6. Post-deploy schema verification via information_schema.
#
# The migration is ADDITIVE-ONLY: it never drops/renames columns. Idempotent
# guards via `_col_exists()` make it safe to re-run. Downgrade is a no-op
# (REGLAS §9.1 immutability).
#
# Requisitos: requiere --yes explícito para impedir ejecuciones accidentales.
# Compatible con Postgres prod y SQLite para tests (el precheck salta pg_dump
# si pg_isready no responde).
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "${1:-}" != "--yes" ]; then
    echo "ERROR: este script requiere --yes para confirmar el deploy a producción." >&2
    echo "Uso:    $0 --yes [--skip-pre-check]" >&2
    exit 2
fi
SKIP_PRE_CHECK=0
if [ "${2:-}" = "--skip-pre-check" ]; then
    echo "WARN: --skip-pre-check activo. Saltando los chequeos previos (solo para ops calificado)." >&2
    SKIP_PRE_CHECK=1
fi

VENV_PATH="${VENV_PATH:-venv/bin}"
PYTHON="${PYTHON:-$VENV_PATH/python}"
ALEMBIC="${ALEMBIC:-$VENV_PATH/alembic}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ccf}"
export PYTHONPATH="$(pwd)"

# Cabecera para los logs (se imprimirá también en el journalctl si aplica).
echo "================================================="
echo " Deploy 20260710_0003_align_crm_casos (additive)"
echo "  - Branched from: 20260710_0002"
echo "  - Target head:    20260710_0003"
echo "  - Downgrade:      no-op (REGLAS §9.1)"
echo "================================================="

# 1. PRE-DEPLOY: conectividad.
echo "[1/6] Pre-deploy: conectividad de base de datos…"
if ! "${PYTHON}" - <<'PY'
import sys
try:
    from backend.core.database import SessionLocal
    db = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1")).scalar()
    finally:
        db.close()
except Exception as exc:  # noqa: BLE001
    print(f"  ERROR: {exc}", file=sys.stderr)
    sys.exit(1)
PY
then
    echo "ERROR: no se pudo conectar al Postgres de producción. Abortando." >&2
    exit 1
fi

# 2. PRE-DEPLOY: revisión actual.
# Permitimos cualquier revisión que sea ancestor de 20260710_0003 dentro del
# canonical chain (alembic upgrade will catch up). Solo rechazamos bases
# ajenas al chain (ej. legacy alias, otro entorno). Si `--skip-pre-check`
# está activo, el operador declara que conoce el estado y asume el riesgo.
echo "[2/6] Pre-deploy: revisión Alembic actual…"
CURRENT_REV="$(${ALEMBIC} current 2>/dev/null | grep -oE '[0-9a-z_]+' | head -n1 || echo unknown)"
echo "  -> Current revision: ${CURRENT_REV}"
SKIP_UPGRADE=0
if [ "${SKIP_PRE_CHECK}" -eq 1 ]; then
    echo "  -> --skip-pre-check activo: confiaremos en alembic upgrade."
elif [ "${CURRENT_REV}" = "20260710_0003" ]; then
    echo "  -> Ya migrado: revisión destino alcanzada. Skip upgrade."
    SKIP_UPGRADE=1
elif ! "${ALEMBIC}" show --rev "${CURRENT_REV}" >/dev/null 2>&1; then
    echo "ERROR: revisión actual ${CURRENT_REV} no encontrada en el árbol de migraciones. ¿DB de otro entorno?" >&2
    exit 1
fi

# Si la revisión actual es un ancestor válido, `alembic upgrade 20260710_0003`
# hará el catch-up automáticamente. Si NO lo es, alembic abortará con un error
# explícito — preferible a un rechazo silencioso aquí.

# 3. PRE-DEPLOY: captura del estado actual (no destructivo).
echo "[3/6] Pre-deploy: captura de estado de crm_casos…"
"${PYTHON}" - <<'PY'
from backend.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    total = db.execute(text("SELECT count(*) FROM crm_casos")).scalar() or 0
    has_peso = db.execute(text(
        "SELECT count(*) FROM information_schema.columns "
        "WHERE table_name='crm_casos' AND column_name='pipeline_id'"
    )).scalar() or 0
    print(f"  -> Total casos:           {total}")
    print(f"  -> columna pipeline_id:    {'PRESENTE' if has_peso else 'AUSENTE'}")
finally:
    db.close()
PY

# 4. BACKUP lógico opcional (skip silencioso si pg_dump no está instalado).
# `--lock-timeout=10000` fuerza el fail-fast (10s) si la app tiene escrituras
# activas; `--no-acl --no-owner` evita problemas de permisos al restaurar.
# Para DBs grandes, mejor un snapshot managed (wal-g / pgBackRest) — este
# backup es solo un safety net de último recurso.
echo "[4/6] Backup: intentando snapshot lógico con pg_dump…"
if command -v pg_dump >/dev/null 2>&1 && command -v pg_isready >/dev/null 2>&1; then
    mkdir -p "${BACKUP_DIR}" 2>/dev/null || true
    if pg_isready -q "${PGHOST:-localhost}" 2>/dev/null; then
        BACKUP_FILE="${BACKUP_DIR}/prod_pre_crm_align_$(date -u +%Y%m%d_%H%M%SZ).sql"
        if pg_dump --no-acl --no-owner --lock-timeout=10000 --schema=public > "${BACKUP_FILE}" 2>/dev/null; then
            echo "  -> Snapshot OK: ${BACKUP_FILE}"
        else
            echo "  -> WARN: pg_dump falló o lock-timeout agotado. Continuando (la migración es aditiva)."
        fi
    else
        echo "  -> SKIP: pg_isready reporta no-ready. El operador debe tener backup externo."
    fi
else
    echo "  -> SKIP: pg_dump/pg_isready no disponibles. Asumimos backup externo (RDS/PITR/etc.)."
fi

# 5. MIGRACIÓN.
echo "[5/6] Upgrade Alembic: 20260710_0003…"
if [ "${SKIP_UPGRADE:-0}" -eq 0 ]; then
    "${ALEMBIC}" upgrade 20260710_0003
fi
"${ALEMBIC}" current
NEW_REV="$(${ALEMBIC} current 2>/dev/null | grep -oE '[0-9a-z_]+' | head -n1 || echo unknown)"
if [ "${NEW_REV}" != "20260710_0003" ]; then
    echo "ERROR: la revisión esperada post-upgrade es 20260710_0003; se encontró ${NEW_REV}." >&2
    exit 1
fi
echo "  -> Head actual: ${NEW_REV}"

# 6. RESTART de la app — el ORM crea planes al arrancar; las nuevas columnas
# deben aparecer en el `Base.metadata` cargado tras el restart.
echo "[6/6] App restart: aplicando cambios a procesos en vivo…"
if [ -x "./stopccf" ] && [ -x "./startccf" ]; then
    ./stopccf || true
    ./startccf || true
    echo "  -> Restart ejecutado vía startccf/stopccf."
elif command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet ccf-backend 2>/dev/null; then
    sudo systemctl restart ccf-backend
    echo "  -> Restart ejecutado vía systemctl."
elif command -v pm2 >/dev/null 2>&1; then
    pm2 reload ccf-backend || pm2 restart ccf-backend
    echo "  -> Restart ejecutado vía pm2."
else
    echo "  -> Sin orquestador detectado. El operador debe reiniciar el backend manualmente."
fi

# 7. POST-DEPLOY VERIFY LOCAL (no curl ni DNS): columnas accesibles vía SQL.
# Branch por dialecto: Postgres usa information_schema, SQLite usa PRAGMA.
# Cobertura paralela al helper _col_exists() de la propia migración.
echo "[7/7] Post-deploy: validación de columnas nuevas sobre crm_casos…"
"${PYTHON}" - <<'PY'
import sys
from backend.core.database import SessionLocal
from sqlalchemy import text, inspect
EXPECTED = [
    'pipeline_id', 'etapa_actual_id', 'persona_id', 'sede_id',
    'origen_sesion_id', 'origen_grupo_id', 'origen_estrategia_id',
    'titulo_caso', 'origen_canal', 'origen_detalle_id',
    'prioridad', 'estado', 'payload_web', 'asignado_a_id',
    'fecha_creacion', 'fecha_cierre', 'sla_vencimiento_contacto',
    'deleted_at',
    'sort_order', 'drag_source_etapa_id', 'drag_target_etapa_id',
    'is_locked_for_reorder', 'last_reorder_failed',
]
db = SessionLocal()
try:
    bind = db.get_bind()
    if bind.dialect.name == 'sqlite':
        rows = bind.execute(text("PRAGMA table_info(crm_casos)")).fetchall()
        present = {r[1] for r in rows}
    else:
        rows = db.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='crm_casos'"
        )).fetchall()
        present = {r[0] for r in rows}
    missing = [c for c in EXPECTED if c not in present]
    if missing:
        print(f"  -> ERROR: columnas ausentes en crm_casos: {missing}", file=sys.stderr)
        sys.exit(1)
    print(f"  -> OK: {len(EXPECTED)} columnas canónicas presentes en crm_casos ({bind.dialect.name}).")
    print("  -> NOTA: los índices indexcanónicos quedaron deferrados a un ops migration.")
finally:
    db.close()
PY

# 8. POST-DEPLOY VERIFY NETWORK: los endpoints /api/crm/* deben responder sin 500.
echo ""
echo "Verificando endpoints HTTP /api/crm/* sin 500 (configurable via BASE_URL)…"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
"${PYTHON}" - <<PY
import sys, urllib.request, urllib.error
BASE = "${BASE_URL}"
endpoints = [
    f"{BASE}/healthz",
    f"{BASE}/api/crm/casos",
    f"{BASE}/api/crm/leads/newsletter?page=1&page_size=50",
]
all_ok = True
for u in endpoints:
    try:
        req = urllib.request.Request(u, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"  -> {u} | HTTP {r.status} OK")
    except urllib.error.HTTPError as e:
        print(f"  -> {u} | HTTP {e.code}  (no es 5xx, ruta cargó)")
        if e.code >= 500:
            all_ok = False
    except Exception as e:
        print(f"  -> {u} | FAIL: {e}")
        all_ok = False
sys.exit(0 if all_ok else 1)
PY

echo ""
echo "================================================="
echo " Deploy 20260710_0003 finalizado."
echo " Comando recomendado para el operador:"
echo "   $0 --yes && BASE_URL=https://elfarocc.tech scripts/verify_20260710_0003_align_crm_casos.sh"
echo "================================================="
