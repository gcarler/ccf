#!/usr/bin/env bash
# Archiva una rama bajo archive/merged/ o archive/stale/ y solo despues elimina la fuente.
set -euo pipefail

REMOTE="${1:-origin}"
CATEGORY="${2:-}"
SOURCE_BRANCH="${3:-}"

if [ -z "$SOURCE_BRANCH" ] || [ -z "$CATEGORY" ]; then
    echo "Uso: scripts/archive_branch.sh origin <merged|stale> <rama>" >&2
    exit 2
fi

case "$CATEGORY" in
    merged|stale) ;;
    *)
        echo "x Categoria invalida: $CATEGORY. Usa merged o stale." >&2
        exit 2
        ;;
esac

if [ "$SOURCE_BRANCH" = "main" ] || [[ "$SOURCE_BRANCH" == archive/* ]]; then
    echo "x No se puede archivar main ni una rama ya archivada: $SOURCE_BRANCH" >&2
    exit 2
fi

if [ -n "$(git status --short)" ]; then
    echo "x El worktree actual esta sucio; archivar requiere un worktree limpio." >&2
    git status --short >&2
    exit 2
fi

if git worktree list --porcelain | awk -v branch="refs/heads/$SOURCE_BRANCH" '
    $1 == "branch" && $2 == branch { found = 1 }
    END { exit(found ? 0 : 1) }
'; then
    echo "x La rama tiene un worktree activo: $SOURCE_BRANCH" >&2
    echo "  Retira ese worktree de forma explicita antes de archivarla." >&2
    exit 2
fi

git fetch --prune "$REMOTE" main "$SOURCE_BRANCH"
SOURCE_REF="refs/remotes/$REMOTE/$SOURCE_BRANCH"
MAIN_REF="refs/remotes/$REMOTE/main"

if ! git rev-parse "$SOURCE_REF^{commit}" >/dev/null 2>&1; then
    echo "x No existe $REMOTE/$SOURCE_BRANCH." >&2
    exit 2
fi

SOURCE_SHA="$(git rev-parse "$SOURCE_REF^{commit}")"
if [ "$CATEGORY" = "merged" ] && ! git merge-base --is-ancestor "$SOURCE_SHA" "$MAIN_REF"; then
    echo "x $SOURCE_BRANCH no esta integrada completamente en $REMOTE/main." >&2
    echo "  Usa la categoria stale o integra primero la rama." >&2
    exit 1
fi

ARCHIVE_BRANCH="archive/$CATEGORY/${SOURCE_BRANCH//\//-}"
ARCHIVE_REF="refs/heads/$ARCHIVE_BRANCH"
EXISTING_SHA="$(git ls-remote --heads "$REMOTE" "$ARCHIVE_REF" | awk 'NR == 1 { print $1 }')"
if [ -n "$EXISTING_SHA" ]; then
    if [ "$EXISTING_SHA" != "$SOURCE_SHA" ]; then
        echo "x El archivo remoto ya existe con otro SHA: $ARCHIVE_BRANCH." >&2
        exit 1
    fi
    echo "ok Archivo remoto ya confirmado: $ARCHIVE_BRANCH -> $SOURCE_SHA"
else
    git push "$REMOTE" "$SOURCE_SHA:$ARCHIVE_REF"
    CONFIRMED_SHA="$(git ls-remote --heads "$REMOTE" "$ARCHIVE_REF" | awk 'NR == 1 { print $1 }')"
    if [ "$CONFIRMED_SHA" != "$SOURCE_SHA" ]; then
        echo "x No se pudo confirmar el archivo remoto." >&2
        exit 1
    fi
    echo "ok Rama archivada: $ARCHIVE_BRANCH -> $SOURCE_SHA"
fi

git push "$REMOTE" --delete "$SOURCE_BRANCH"
echo "ok Rama fuente eliminada despues de archivar: $REMOTE/$SOURCE_BRANCH"
echo "  SHA conservado: $SOURCE_SHA"
