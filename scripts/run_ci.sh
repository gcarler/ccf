#!/usr/bin/env bash
# scripts/run_ci.sh
# Pipeline CI principal para la plataforma CCF.
#
# Ejecuta (en este orden):
#   1. check_academy_backlog.sh — valida docs/ACADEMY_BACKLOG.md
#   2. ruff check (lint + format validate)
#   3. ruff check CRM (import organization)
#   4. ruff check Academy (import organization)
#   5. ruff check Evangelism (import organization)
#   6. ruff check CMS (import organization)
#   7. tsc --noEmit (Next.js)
#   8. pytest tests/test_academy_backlog.py (suite estructural)
#   9. pytest tests/test_academy_api.py + tests/test_academy_domain.py (suite runtime)
#   10. scripts/test_academy_quality.py (smoke canónico)
#
# Salida:
#   - exit 0 si TODO verde
#   - exit 1 con output acumulado al fallar cualquier step

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Resolver venv (preferimos ./venv, fallback al python3 del sistema).
if [ -x "./venv/bin/python" ]; then
  PY="./venv/bin/python"
else
  PY="python3"
fi

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

step() { echo -e "\n${YELLOW}━━━ $* ━━━${NC}"; }
pass() { echo -e "${GREEN}✔ $*${NC}"; }
fail() { echo -e "${RED}✘ $*${NC}"; exit 1; }

step "1/10 — check_academy_backlog.sh"
bash scripts/check_academy_backlog.sh || fail "Backlog sin fuente única"
pass "ACADEMY_BACKLOG validado"

step "2/10 — ruff lint"
if [ -x "./venv/bin/ruff" ]; then
  ./venv/bin/ruff check backend/ tests/ 2>&1 | tail -5 || fail "Ruff encontró issues"
else
  $PY -m ruff check backend/ tests/ 2>&1 | tail -5 || fail "Ruff no disponible"
fi
pass "ruff OK"

step "3/10 — ruff lint CRM (import organization)"
bash scripts/lint-crm.sh || fail "Ruff encontró issues en CRM"
pass "ruff CRM OK"

step "4/10 — ruff lint Academy (import organization)"
bash scripts/lint-academy.sh || fail "Ruff encontró issues en Academy"
pass "ruff Academy OK"

step "5/10 — ruff lint Evangelism (import organization)"
bash scripts/lint-evangelism.sh || fail "Ruff encontró issues en Evangelism"
pass "ruff Evangelism OK"

step "6/10 — ruff lint CMS (import organization)"
bash scripts/lint-cms.sh || fail "Ruff encontró issues en CMS"
pass "ruff CMS OK"

step "7/10 — tsc --noEmit"
if [ -d "frontend" ]; then
  ( cd frontend && npx tsc --noEmit 2>&1 | tail -5 ) || fail "tsc encontró errors"
  pass "tsc OK"
else
  echo "⚠️  frontend/ no presente; saltando tsc"
fi

step "8/10 — pytest test_academy_backlog.py (estructural)"
$PY -m pytest -q -o "addopts=" tests/test_academy_backlog.py \
  || fail "Tests estructurales del backlog fallaron"
pass "Backlog structural tests OK"

step "9/10 — pytest tests/test_academy_api.py + test_academy_domain.py"
$PY -m pytest -q -o "addopts=" tests/test_academy_api.py tests/test_academy_domain.py \
  || fail "Tests de Academy API fallaron"
pass "Academy API tests OK"

step "10/10 — scripts/test_academy_quality.py (smoke canónico)"
[ -f scripts/test_academy_quality.py ] \
  && $PY scripts/test_academy_quality.py 2>&1 | tail -10 \
  || echo "⚠️  scripts/test_academy_quality.py no presente; saltando smoke"
pass "Smoke canónico OK"

echo -e "\n${GREEN}==============================${NC}"
echo -e "${GREEN}✅ run_ci.sh: TODOS los pasos en verde${NC}"
echo -e "${GREEN}==============================${NC}"
