#!/usr/bin/env bash
# Deploy an exact reviewed main commit; no checkout/pull/reset of the runtime tree.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${CCF_RUNTIME_DIR:-/root/ccf}"
exec "$RUNTIME_DIR/venv/bin/python" "$ROOT_DIR/scripts/backend_release.py" deploy "$@" \
  --runtime "$RUNTIME_DIR" --repo "$ROOT_DIR"
