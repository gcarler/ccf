#!/usr/bin/env bash
# deploy_backend.sh — Reinicia el backend CCF desde ccf-cms-main-final.
# No hay build step (Python no compila); simplemente reinicia uvicorn para
# que cargue los módulos nuevos.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PM2_BIN="$(command -v pm2 || echo /usr/local/bin/pm2)"
BACKEND_PORT="${BACKEND_PORT:-8000}"

echo "  [backend-deploy] (1/2) reiniciando ccf-backend-staging..."
if "$PM2_BIN" jlist 2>/dev/null | grep -q '"name":"ccf-backend-staging"'; then
    # Si PM2 ya gestiona el proceso, solo reiniciarlo
    "$PM2_BIN" restart ccf-backend-staging >/dev/null
else
    # Primera vez: registrar el proceso usando el script de arranque
    "$PM2_BIN" start "$ROOT_DIR/scripts/start_backend.sh" \
      --name "ccf-backend-staging" \
      --interpreter bash \
      >/dev/null
    "$PM2_BIN" save >/dev/null
fi

echo "  [backend-deploy] (2/2) smoke HTTP :$BACKEND_PORT..."
BACK_HTTP="000"
for _ in $(seq 1 20); do
    BACK_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$BACKEND_PORT/healthz" 2>/dev/null || echo "000")
    [ "$BACK_HTTP" = "200" ] && break
    sleep 1
done

if [ "$BACK_HTTP" = "200" ]; then
    echo "  ✓ Backend en servicio (HTTP $BACK_HTTP)"
else
    echo "  ✗ Backend no responde (HTTP $BACK_HTTP) — revisa: pm2 logs ccf-backend-staging" >&2
    exit 1
fi
