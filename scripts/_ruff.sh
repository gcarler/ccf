#!/usr/bin/env bash
# scripts/_ruff.sh
# Helper interno para resolver el binario de ruff a usar.
# Se espera que se use con: source "$(dirname "$0")/_ruff.sh"
# Deja la variable RUFF disponible.

if [ -x "./venv/bin/ruff" ]; then
  RUFF="./venv/bin/ruff"
else
  PY="python3"
  if command -v python >/dev/null 2>&1; then
    PY="python"
  fi
  RUFF="$PY -m ruff"
fi
