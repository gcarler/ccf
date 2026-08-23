#!/usr/bin/env bash
# Push sectorizado: fetch, valida la rama activa y confirma el remoto.
set -euo pipefail

REMOTE="${1:-origin}"
BRANCH="${2:-$(git symbolic-ref --quiet --short HEAD || true)}"
CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"

if [ -z "$BRANCH" ] || [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "✗ El worktree activo no corresponde a la rama solicitada."
    echo "  Activa: ${CURRENT_BRANCH:-detached}"
    echo "  Solicitada: ${BRANCH:-vacía}"
    exit 2
fi

if [ -n "$(git status --short)" ]; then
    echo "✗ Worktree sucio: no se permite push con cambios sin commit."
    git status --short
    exit 2
fi

echo "→ Sincronizando base remota: $REMOTE/$BRANCH"
git fetch --prune "$REMOTE" "$BRANCH"

LOCAL_BASE="$(git rev-parse "refs/remotes/$REMOTE/$BRANCH" 2>/dev/null || true)"
if [ -z "$LOCAL_BASE" ]; then
    echo "✗ No existe la rama remota $REMOTE/$BRANCH. Créala explícitamente o revisa el nombre."
    exit 2
fi

export CCF_PRE_PUSH_BASE="$REMOTE/$BRANCH"
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=20}"

echo "→ Validando y publicando únicamente $BRANCH"
git push "$REMOTE" "HEAD:refs/heads/$BRANCH"

REMOTE_HEAD="$(git ls-remote --heads "$REMOTE" "refs/heads/$BRANCH" | awk 'NR == 1 { print $1 }')"
LOCAL_HEAD="$(git rev-parse HEAD)"
if [ "$REMOTE_HEAD" != "$LOCAL_HEAD" ]; then
    echo "✗ El push terminó sin confirmar el commit remoto esperado."
    echo "  Local:  $LOCAL_HEAD"
    echo "  Remoto: ${REMOTE_HEAD:-no encontrado}"
    exit 1
fi

echo "✓ Push confirmado: $REMOTE/$BRANCH -> $LOCAL_HEAD"
