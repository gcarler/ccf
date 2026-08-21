#!/usr/bin/env bash
# scripts/lint-evangelism.sh
# Lint de import organization para todos los módulos backend de Evangelismo.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source "$REPO_ROOT/scripts/_ruff.sh"

EVANGELISM_PATHS=(
  backend/api/evangelism.py
  backend/api/evangelism_shared.py
  backend/api/evangelism_main/
  backend/api/evangelism_events/
  backend/api/evangelism_grupos/
  backend/api/evangelism_notifications.py
  backend/api/evangelism_rankings.py
  backend/api/evangelism_multiplication.py
  backend/api/evangelism_reports.py
  backend/api/evangelism_analytics.py
  backend/crud/evangelism.py
  backend/schemas/evangelism.py
  backend/models_evangelism.py
)

$RUFF check --select I "${EVANGELISM_PATHS[@]}"
echo "✔ Evangelism import organization lint passed"
