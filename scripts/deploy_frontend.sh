#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# deploy_frontend.sh — Deploy seguro del frontend CCF.
#
# Secuencia (build → swap → restart → smoke):
#   1) npm run build  → compila a .next-build (el .next en producción queda
#      intacto durante todo el build; el proceso en servicio nunca ve un .next
#      a medias) y hace swap atómico .next-build → .next al terminar, dejando
#      .next-old (último build bueno) disponible para rollback.
#   2) pm2 restart ccf-frontend-staging → el proceso pasa a servir el build
#      nuevo. Sin este restart, el proceso viejo seguiría sirviendo con su
#      manifest en memoria contra chunks que ya no existen (400 en assets =
#      "chunks huérfanos").
#   3) Smoke HTTP: espera a que :3000 responda 200. Si no responde, hace
#      rollback automático al build anterior (.next-old) y reinicia de nuevo.
#   4) Solo tras el smoke OK se descarta .next-old.
#
# Si el build falla, .next queda intacto y NO se reinicia nada (rollback nulo).
# ============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
PM2_BIN="$(command -v pm2 || echo /usr/local/bin/pm2)"
FRONT_PORT="${FRONTEND_PORT:-3000}"

# PATH hardening: el shell no-interactivo del deploy (appleboy/ssh-action) puede
# no tener node/npm en PATH (nvm no se sourcea en shells no-login).
if ! command -v npm >/dev/null 2>&1; then
    for CAND in "$HOME/.nvm/versions/node"/*/bin /usr/local/bin /usr/bin; do
        if [ -x "$CAND/npm" ]; then
            export PATH="$CAND:$PATH"
            break
        fi
    done
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: no se encuentra npm — revisa el PATH del entorno de deploy" >&2
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "ERROR: no existe $FRONTEND_DIR" >&2
    exit 1
fi

echo "  [deploy] (1/3) npm run build (swap seguro)..."
# KEEP_OLD_BUILD=1: build-safe conserva .next-old (último build bueno) hasta que
# el smoke confirme el build nuevo → rollback real si restart/smoke fallan.
( cd "$FRONTEND_DIR" && KEEP_OLD_BUILD=1 npm run build )

echo "  [deploy] (2/3) reiniciando frontend para servir el build nuevo..."
if "$PM2_BIN" jlist 2>/dev/null | grep -q '"name":"ccf-frontend-staging"'; then
    "$PM2_BIN" restart ccf-frontend-staging >/dev/null
else
    echo "  [deploy] PM2 no gestiona el frontend; fallback ./stopccf + ./startccf"
    ( cd "$ROOT_DIR" && ./stopccf >/dev/null 2>&1 && ./startccf >/dev/null 2>&1 )
fi

echo "  [deploy] (3/3) smoke HTTP :$FRONT_PORT..."
FRONT_HTTP="000"
for _ in $(seq 1 15); do
    FRONT_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$FRONT_PORT" 2>/dev/null || echo "000")
    [ "$FRONT_HTTP" = "200" ] && break
    sleep 1
done

if [ "$FRONT_HTTP" = "200" ]; then
    # Smoke OK: el build nuevo ya está en servicio; descartamos el anterior.
    rm -rf "$FRONTEND_DIR/.next-old"
    echo "  ✓ Frontend en servicio con el build nuevo (HTTP $FRONT_HTTP)"
else
    echo "  ✗ Frontend no responde con el build nuevo (HTTP $FRONT_HTTP)" >&2
    if [ -d "$FRONTEND_DIR/.next-old" ]; then
        echo "  [deploy] Haciendo rollback al build anterior..."
        rm -rf "$FRONTEND_DIR/.next"
        mv "$FRONTEND_DIR/.next-old" "$FRONTEND_DIR/.next"
        if "$PM2_BIN" jlist 2>/dev/null | grep -q '"name":"ccf-frontend-staging"'; then
            "$PM2_BIN" restart ccf-frontend-staging >/dev/null
        else
            ( cd "$ROOT_DIR" && ./stopccf >/dev/null 2>&1 && ./startccf >/dev/null 2>&1 )
        fi
        RB_HTTP="000"
        for _ in $(seq 1 15); do
            RB_HTTP=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$FRONT_PORT" 2>/dev/null || echo "000")
            [ "$RB_HTTP" = "200" ] && break
            sleep 1
        done
        if [ "$RB_HTTP" = "200" ]; then
            echo "  ✓ Rollback completado — build anterior en servicio (HTTP $RB_HTTP)" >&2
        else
            echo "  ✗ Rollback falló — el sitio no responde (HTTP $RB_HTTP). Restaura manualmente frontend/.next-old" >&2
        fi
    else
        echo "  ✗ No hay .next-old para rollback — revisa el deploy manualmente" >&2
    fi
    exit 1
fi
