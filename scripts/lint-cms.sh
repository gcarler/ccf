#!/usr/bin/env bash
# scripts/lint-cms.sh
# Lint de import organization para todos los módulos backend de CMS.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

source "$REPO_ROOT/scripts/_ruff.sh"

CMS_PATHS=(
  backend/api/cms/
  backend/api/cms_v2/
  backend/api/enterprise_cms.py
  backend/api/_cms_helpers/
  backend/crud/cms/
  backend/crud/cms_pastors_sync.py
  backend/schemas/cms.py
  backend/schemas/cms_v2_sections.py
  backend/models_cms.py
)

$RUFF check --select I "${CMS_PATHS[@]}"
echo "✔ CMS import organization lint passed"
