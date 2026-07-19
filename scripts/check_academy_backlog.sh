#!/usr/bin/env bash
# scripts/check_academy_backlog.sh — wrapper de pre-commit hook
#
# Este shell delega al parser Python (scripts/check_academy_backlog.py)
# para evitar problemas de escape de comillas/backticks. El hook real
# vive en Python; el shell sólo resuelve venv + exit code.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Resolver venv.
if [ -x "./venv/bin/python" ]; then
  PY="./venv/bin/python"
else
  PY="python3"
fi

exec "$PY" scripts/check_academy_backlog.py
