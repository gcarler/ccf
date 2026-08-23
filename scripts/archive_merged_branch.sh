#!/usr/bin/env bash
# Compatibilidad para archivar integraciones ya fusionadas.
set -euo pipefail

REMOTE="${1:-origin}"
SOURCE_BRANCH="${2:-}"

if [ -z "$SOURCE_BRANCH" ]; then
    echo "Uso: scripts/archive_merged_branch.sh origin <rama-integrada>" >&2
    exit 2
fi

exec "$(dirname "$0")/archive_branch.sh" "$REMOTE" merged "$SOURCE_BRANCH"
