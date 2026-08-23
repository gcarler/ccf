#!/usr/bin/env bash
# Crea una rama temporal desde origin/main e integra una sola rama propietaria.
set -euo pipefail

REMOTE="${1:-origin}"
SOURCE_BRANCH="${2:-}"
INTEGRATION_BRANCH="${3:-}"

if [ -z "$SOURCE_BRANCH" ]; then
    echo "Uso: scripts/create_integration_branch.sh origin <rama-propietaria> [integration/<tema>]" >&2
    exit 2
fi

if [ "$SOURCE_BRANCH" = "main" ] || [[ "$SOURCE_BRANCH" == archive/merged/* ]]; then
    echo "✗ La fuente debe ser una rama propietaria activa, no $SOURCE_BRANCH." >&2
    exit 2
fi

if [ -z "$INTEGRATION_BRANCH" ]; then
    INTEGRATION_BRANCH="integration/${SOURCE_BRANCH//\//-}-$(date -u +%Y%m%d%H%M%S)"
fi

if [[ "$INTEGRATION_BRANCH" != integration/* ]] || [ "$INTEGRATION_BRANCH" = "integration/" ]; then
    echo "✗ La rama temporal debe usar integration/<tema>." >&2
    exit 2
fi

if [ -n "$(git status --short)" ]; then
    echo "✗ El worktree actual está sucio; crea la integración desde un worktree limpio." >&2
    git status --short >&2
    exit 2
fi

if git show-ref --verify --quiet "refs/heads/$INTEGRATION_BRANCH" || \
   git ls-remote --exit-code --heads "$REMOTE" "refs/heads/$INTEGRATION_BRANCH" >/dev/null 2>&1; then
    echo "✗ La rama temporal ya existe: $INTEGRATION_BRANCH" >&2
    exit 2
fi

git fetch --prune "$REMOTE" main "$SOURCE_BRANCH"
MAIN_REF="refs/remotes/$REMOTE/main"
SOURCE_REF="refs/remotes/$REMOTE/$SOURCE_BRANCH"

if ! git rev-parse "$SOURCE_REF^{commit}" >/dev/null 2>&1; then
    echo "✗ No existe $REMOTE/$SOURCE_BRANCH." >&2
    exit 2
fi

if [ "$(git rev-parse "$MAIN_REF^{commit}")" = "$(git rev-parse "$SOURCE_REF^{commit}")" ]; then
    echo "✗ La rama propietaria no contiene cambios respecto de $REMOTE/main." >&2
    exit 2
fi

git switch -c "$INTEGRATION_BRANCH" "$MAIN_REF"
if git merge --no-ff --no-commit "$SOURCE_REF"; then
    echo "✓ Integración preparada: $INTEGRATION_BRANCH"
    echo "  Base: $(git rev-parse --short "$MAIN_REF")"
    echo "  Fuente: $(git rev-parse --short "$SOURCE_REF")"
    echo "  Ejecuta los gates, crea el commit de merge y publica solo esta rama."
    exit 0
fi

cat >&2 <<EOF
✗ Conflicto al integrar $SOURCE_BRANCH sobre $REMOTE/main.
  La rama $INTEGRATION_BRANCH queda separada con el conflicto visible.
  Resuelve manualmente, ejecuta los gates y continúa; no uses merge -X theirs ni fuerces la historia.
EOF
exit 1
