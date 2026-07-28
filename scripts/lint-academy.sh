#!/usr/bin/env bash
# scripts/lint-academy.sh
# Lint de import organization para todos los módulos backend de Academy.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source "$REPO_ROOT/scripts/_ruff.sh"

ACADEMY_PATHS=(
  backend/api/academy.py
  backend/api/academy_cache.py
  backend/crud/academy.py
  backend/schemas/academy.py
  backend/models_academy_core.py
)

$RUFF check --select I "${ACADEMY_PATHS[@]}"
echo "✔ Academy import organization lint passed"
