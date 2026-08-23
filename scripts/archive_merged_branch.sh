#!/usr/bin/env bash
# Conserva una rama ya integrada bajo archive/merged/ antes de eliminarla.
set -euo pipefail

REMOTE="${1:-origin}"
SOURCE_BRANCH="${2:-}"

if [ -z "$SOURCE_BRANCH" ]; then
    echo "Uso: scripts/archive_merged_branch.sh origin <rama-integrada>" >&2
    exit 2
fi

if [ "$SOURCE_BRANCH" = "main" ] || [[ "$SOURCE_BRANCH" == archive/merged/* ]] || [[ "$SOURCE_BRANCH" == integration/* ]]; then
    echo "✗ Solo se archivan ramas propietarias integradas; recibida: $SOURCE_BRANCH." >&2
    exit 2
fi

if [ -n "$(git status --short)" ]; then
    echo "✗ El worktree actual está sucio; archivar requiere un worktree limpio." >&2
    git status --short >&2
    exit 2
fi

git fetch --prune "$REMOTE" main "$SOURCE_BRANCH"
MAIN_REF="refs/remotes/$REMOTE/main"
SOURCE_REF="refs/remotes/$REMOTE/$SOURCE_BRANCH"

if ! git rev-parse "$SOURCE_REF^{commit}" >/dev/null 2>&1; then
    echo "✗ No existe $REMOTE/$SOURCE_BRANCH." >&2
    exit 2
fi

SOURCE_SHA="$(git rev-parse "$SOURCE_REF^{commit}")"
if ! git merge-base --is-ancestor "$SOURCE_SHA" "$MAIN_REF"; then
    echo "✗ $SOURCE_BRANCH no está integrada completamente en $REMOTE/main." >&2
    echo "  Se conserva activa; revisa conflictos o integra primero." >&2
    exit 1
fi

ARCHIVE_BRANCH="archive/merged/${SOURCE_BRANCH//\//-}"
if git ls-remote --exit-code --heads "$REMOTE" "refs/heads/$ARCHIVE_BRANCH" >/dev/null 2>&1; then
    ARCHIVE_SHA="$(git ls-remote --heads "$REMOTE" "refs/heads/$ARCHIVE_BRANCH" | awk 'NR == 1 { print $1 }')"
    if [ "$ARCHIVE_SHA" != "$SOURCE_SHA" ]; then
        echo "✗ El archivo remoto ya existe con otro SHA: $ARCHIVE_BRANCH." >&2
        exit 1
    fi
    echo "✓ Archivo remoto ya confirmado: $ARCHIVE_BRANCH -> $SOURCE_SHA"
else
    git push "$REMOTE" "$SOURCE_SHA:refs/heads/$ARCHIVE_BRANCH"
    ARCHIVE_SHA="$(git ls-remote --heads "$REMOTE" "refs/heads/$ARCHIVE_BRANCH" | awk 'NR == 1 { print $1 }')"
    if [ "$ARCHIVE_SHA" != "$SOURCE_SHA" ]; then
        echo "✗ No se pudo confirmar el archivo remoto." >&2
        exit 1
    fi
    echo "✓ Rama archivada: $ARCHIVE_BRANCH -> $SOURCE_SHA"
fi

git push "$REMOTE" --delete "$SOURCE_BRANCH"
echo "✓ Rama fuente eliminada después de archivar: $REMOTE/$SOURCE_BRANCH"
echo "  Confirma localmente con: git branch -r --contains $SOURCE_SHA"
