#!/usr/bin/env bash
# The only production frontend build entrypoint: reviewed source, runtime lock,
# atomic artifact/config promotion and rollback at the actual PM2 cwd.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${CCF_RUNTIME_DIR:-/root/ccf}"
exec "$RUNTIME_DIR/venv/bin/python" "$ROOT_DIR/scripts/frontend_release.py" \
  --source "$ROOT_DIR" --runtime "$RUNTIME_DIR"
