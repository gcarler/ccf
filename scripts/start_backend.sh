#!/usr/bin/env bash
# start_backend.sh — Arranca uvicorn desde ccf-cms-main-final usando el venv de /root/ccf
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="/root/ccf/venv"
UVICORN="$VENV_DIR/bin/uvicorn"

if [ ! -x "$UVICORN" ]; then
  echo "ERROR: uvicorn no encontrado en $UVICORN" >&2
  exit 1
fi

cd "$ROOT_DIR"
export PYTHONPATH="$ROOT_DIR"
export ENV_FILE="backend/.env"

exec "$UVICORN" backend.main:app --host 127.0.0.1 --port 8000
