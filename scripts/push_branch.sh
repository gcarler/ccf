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

if [ "$BRANCH" = "main" ] && [ "${CCF_ALLOW_MAIN_PUSH:-0}" != "1" ]; then
    echo "✗ Push directo a main bloqueado. Usa una rama propietaria e integración revisada."
    exit 2
fi

if [ -n "$(git status --short)" ]; then
    echo "✗ Worktree sucio: no se permite push con cambios sin commit."
    git status --short
    exit 2
fi

echo "→ Sincronizando base remota: $REMOTE/$BRANCH"
if git ls-remote --exit-code --heads "$REMOTE" "refs/heads/$BRANCH" >/dev/null 2>&1; then
    git fetch --prune "$REMOTE" "$BRANCH"
else
    echo "→ La rama $REMOTE/$BRANCH aún no existe; se validará contra $REMOTE/main"
    git fetch --prune "$REMOTE" main
fi

LOCAL_BASE="$(git rev-parse "refs/remotes/$REMOTE/$BRANCH" 2>/dev/null || true)"
if [ -z "$LOCAL_BASE" ]; then
    BASE_REF="refs/remotes/$REMOTE/main"
    if ! git rev-parse "$BASE_REF^{commit}" >/dev/null 2>&1; then
        echo "✗ No existe la base $REMOTE/main para publicar la rama nueva."
        exit 2
    fi
    echo "→ Primera publicación de $BRANCH; usando $REMOTE/main como base de validación"
else
    BASE_REF="refs/remotes/$REMOTE/$BRANCH"
fi

export CCF_PRE_PUSH_BASE="${BASE_REF#refs/remotes/}"
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
