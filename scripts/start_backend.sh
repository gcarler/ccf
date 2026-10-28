#!/usr/bin/env bash
# Keep runtime configuration/state in its canonical directory, source in a reviewed release.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${CCF_RUNTIME_DIR:-$ROOT_DIR}"
exec "$RUNTIME_DIR/venv/bin/python" "$ROOT_DIR/scripts/backend_release.py" start --runtime "$RUNTIME_DIR"
