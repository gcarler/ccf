#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# Verify: 20260710_0003_align_crm_casos_columns
#
# Operador corre este script tras el deploy. Confirma que los endpoints
# /healthz, /api/crm/casos y /api/crm/leads/newsletter ya NO devuelven 5xx
# (los 500 que reportaba el bug "psycopg2.errors.UndefinedColumn column
# crm_casos…_casos…"). Si algún endpoint responde 5xx, este script sale con
# código != 0 y, siempre que pueda, lee los logs recientes del backend
# (systemd unit 'ccf-backend' o backend.log) para entregar contexto.
#
# Uso:
#   BASE_URL=https://elfarocc.tech scripts/verify_20260710_0003_align_crm_casos.sh
#
# Diseño:
#  - urllib nativo (no asumimos curl, ni DNS público).
#  - 401/403 se cuentan como "login requerido, ruta viva"; solo 5xx es FAIL.
#  - Logs: preferimos journalctl; fallback a backend.log; si no hay nada,
#    instruimos al operador a mirar la consola del proceso.
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail

cd "$(dirname "$0")/.."
VENV_PATH="${VENV_PATH:-venv/bin}"
PYTHON="${PYTHON:-$VENV_PATH/python}"
export PYTHONPATH="$(pwd)"

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "================================================="
echo " Verify 20260710_0003 — endpoints /api/crm/*"
echo "  Base URL: ${BASE_URL}"
echo "================================================="
echo "Contrato del verify:"
echo "  - HTTP 200             : ruta viva, contrato OK"
echo "  - HTTP 401 / 403       : ruta viva (guard de auth respondió primero), contrato OK"
echo "  - HTTP 5xx             : regresión (FAIL). El bug original era psycopg2.errors.UndefinedColumn → 500."
echo "  - Exception / timeout  : FAIL (red, DNS, o servicio caído)"
echo "================================================="

"${PYTHON}" - << PY
import sys
import urllib.request
import urllib.error

BASE = "${BASE_URL}"
TEST_ENDPOINTS = [
    "/healthz",
    "/api/crm/casos",
    "/api/crm/leads/newsletter?page=1&page_size=50",
]

print("[1/3] Sanity: /healthz responde sin 5xx…")
try:
    with urllib.request.urlopen(
        urllib.request.Request(BASE + "/healthz", headers={"Accept": "application/json"}),
        timeout=10,
    ) as r:
        print(f"  -> /healthz | HTTP {r.status} OK")
except urllib.error.HTTPError as e:
    if e.code < 500:
        print(f"  -> /healthz | HTTP {e.code}  (ruta no 5xx, skip)")
    else:
        print(f"  -> /healthz | HTTP {e.code}  (FALLO)")
        sys.exit(1)
except Exception as e:
    print(f"  -> /healthz | ERROR: {e}")
    sys.exit(1)

print("[2/3] Endpoints CRM sensibles a columnas faltantes…")
fails = []
for path in TEST_ENDPOINTS[1:]:
    url = BASE + path
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"  -> {url} | HTTP {r.status} OK")
    except urllib.error.HTTPError as e:
        if e.code < 500:
            print(f"  -> {url} | HTTP {e.code}  (ruta no 5xx; guard de auth respondió primero)")
        else:
            print(f"  -> {url} | HTTP {e.code}  :: FALLO 5xx (regresión?)")
            fails.append((url, e.code))
    except Exception as e:
        print(f"  -> {url} | ERROR: {e}")
        fails.append((url, "exception"))

print("[3/3] Resumen…")
if fails:
    print(f"  -> {len(fails)} endpoint(s) sigue(n) devolviendo 5xx: {fails}", file=sys.stderr)
    print("  -> Revisa los logs del backend (systemd unit 'ccf-backend' o backend.log).", file=sys.stderr)
    sys.exit(1)

print("  -> OK: ningún endpoint devuelve 5xx tras el deploy.")
PY
VERIFY_EXIT=$?

if [ "${VERIFY_EXIT}" -ne 0 ]; then
    echo ""
    echo "Recolectando logs recientes del backend para contexto…"
    if command -v journalctl >/dev/null 2>&1 && systemctl is-active --quiet ccf-backend 2>/dev/null; then
        echo "  (systemd unit 'ccf-backend', últimos 5 min)"
        journalctl -u ccf-backend --no-pager --since "5 min ago" 2>/dev/null \
            | grep -iE 'error|traceback|sqlalchemy|undefinedcolumn' \
            | tail -n 40 \
            || echo "  (no se encontraron entradas con error/traceback)"
    elif [ -f "logs/backend.log" ]; then
        echo "  (logs/backend.log, project-local)"
        tail -n 200 logs/backend.log 2>/dev/null \
            | grep -iE 'error|traceback|sqlalchemy|undefinedcolumn' \
            | tail -n 50 \
            || echo "  (no se encontraron entradas con error/traceback)"
    elif [ -f "backend.log" ]; then
        echo "  (backend.log, CWD)"
        tail -n 200 backend.log 2>/dev/null \
            | grep -iE 'error|traceback|sqlalchemy|undefinedcolumn' \
            | tail -n 50 \
            || echo "  (no se encontraron entradas con error/traceback)"
    else
        echo "  No se encontró systemd unit 'ccf-backend' ni backend.log ni logs/backend.log."
        echo "  Revisa la consola del proceso backend en el host."
    fi
    exit "${VERIFY_EXIT}"
fi

echo ""
echo "================================================="
echo " Verify 20260710_0003 EXITOSO."
echo "   GET /healthz                                       OK"
echo "   GET /api/crm/casos                                 OK (sin UndefinedColumn)"
echo "   GET /api/crm/leads/newsletter?page=1&page_size=50   OK (sin UndefinedColumn)"
echo "================================================="
