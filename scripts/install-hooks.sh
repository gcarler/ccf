#!/usr/bin/env bash
# Instala los git hooks del proyecto CCF
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SCRIPTS_DIR="$REPO_ROOT/scripts"

echo "Instalando git hooks en $HOOKS_DIR..."

cp "$SCRIPTS_DIR/hooks/pre-push" "$HOOKS_DIR/pre-push"
chmod +x "$HOOKS_DIR/pre-push"

echo "✓ pre-push instalado"
echo ""
echo "Hooks activos:"
ls -la "$HOOKS_DIR" | grep -v '\.sample' | grep -v '^total' | grep -v '^d'
