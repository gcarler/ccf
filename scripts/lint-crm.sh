#!/usr/bin/env bash
# scripts/lint-crm.sh
# Lint de import organization para todos los módulos backend de CRM.
# Se usa en CI (.github/workflows/ci.yml) y en run_ci.sh local.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source "$REPO_ROOT/scripts/_ruff.sh"

CRM_PATHS=(
  backend/api/crm/
  backend/crud/crm_/
  backend/crud/crm.py
  backend/schemas/crm/
  backend/schemas/crm_pipeline.py
  backend/schemas/crm_resources.py
  backend/schemas/crm_automation.py
  backend/services/crm_resource_bank.py
  backend/services/evangelism_crm_bridge.py
  backend/models_crm.py
  backend/models_crm_pipeline.py
)

$RUFF check --select I "${CRM_PATHS[@]}"
echo "✔ CRM import organization lint passed"
