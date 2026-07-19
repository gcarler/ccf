# Makefile — CCF Plataforma developer ergonomics layer
# ----------------------------------------------------------------------
# This Makefile is a THIN LAYER over scripts/run_ci.sh,
# scripts/nightly_regression.sh, and scripts/check_academy_backlog.sh so
# developers can use familiar `make <target>` muscle memory instead of
# remembering bash paths. Every target maps 1:1 to an existing script —
# do not put real logic here; if you need a new procedure, write a
# script first, then add a 1-line target here.
#
# Discover targets:
#   make             # default → list available targets
#   make help        # same
# ----------------------------------------------------------------------

# Path conventions. Override on the command line for non-standard setups,
# e.g. `make PYTHON=python3 check-academy` or
# `make LOG_DIR=/tmp/ccf-logs test-nightly-regression`.
PYTHON       ?= ./venv/bin/python
SCRIPTS_DIR  := scripts
CI_SCRIPT    := $(SCRIPTS_DIR)/run_ci.sh
NIGHTLY      := $(SCRIPTS_DIR)/nightly_regression.sh
CHECK_ACAD   := $(SCRIPTS_DIR)/check_academy_backlog.sh
PRE_COMMIT   := .pre-commit-config.yaml
CRONTAB_FILE := infra/cron/ccf-platform
FASE_A_TESTS := tests/test_academy_fase_a_crit.py

# LOG_DIR is the directory the nightly cron log lives in. Override if the
# project is not deployed under /root/ccf/. The directory must exist and
# be writable by the cron user (or whoever invokes
# `make test-nightly-regression`).
LOG_DIR      ?= /var/log/ccf
NIGHTLY_LOG  := $(LOG_DIR)/nightly.log

.DEFAULT_GOAL := help

# `.PHONY` keeps `make` from confusing targets with real files in the
# directory (e.g. an accidental `Makefile` file vs the target).
.PHONY: help check-academy precommit run-ci-academy test-fase-a test-nightly-regression \
	audit-log install-cron preview-cron clean

## help: list available targets with their purpose.
help:
	@echo "CCF Plataforma — developer targets:"
	@echo
	@grep -E '^## ' Makefile | sed 's/^## //'
	@echo
	@echo "Override PYTHON or LOG_DIR for non-standard setups:"
	@echo "  make PYTHON=python3 check-academy"
	@echo "  make LOG_DIR=/tmp/ccf-logs test-nightly-regression"

## check-academy: validate docs/ACADEMY_BACKLOG.md is the single source of truth
##                (no ⬜ ticket without gate, severities valid, IDs unique,
##                legacy docs carry DEPRECADO banner + redirect).
##                Fast (~1s). Exits non-zero if any rule fails.
check-academy:
	@bash $(CHECK_ACAD)

## precommit: run the git pre-commit hooks across the whole repo (bandit,
##           ruff, ruff-format, pytest smoke, pytest reglas_plataforma,
##           check_academy_backlog). Slow (~30-90s).
precommit:
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "❌ pre-commit not installed. Run: pip install pre-commit && pre-commit install"; \
		exit 1; \
	}
	pre-commit run --all-files --verbose

## run-ci-academy: full CI suite for the Academy module
##                 (ruff + pytest backlog estructural + pytest API + smoke canónico).
##                 ~5-10 min locally; the same script CI runs.
run-ci-academy:
	@bash $(CI_SCRIPT)

## test-fase-a: run the 18 regression gates of ACAD-TKT-010..015 (Fase A CRIT).
##              Fast (~15s) — the suite is the structural closure for the
##              6 CRIT del módulo Academy; corre antes de commit cuando tocás
##              Academy o cuando querés validar que las validaciones de sede /
##              extra="forbid" siguen activas.
test-fase-a:
	@$(PYTHON) -m pytest -v -o "addopts=" $(FASE_A_TESTS)

## audit-log: ACAD-TKT-134 stub target — corre los tests que persisten audit logs
##            (AcademyActivityLog.payload_json, etc.). Marcado como nightly-only
##            porque escribe en DB. Cuando cierres los tickets ACAD-TKT-023..028,
##            esta suite crece; ahora mismo es xfail porque los endpoints aún
##            no escriben logs.
audit-log:
	@$(PYTHON) -m pytest -v -o "addopts=" tests/test_academy_backlog.py -k audit_log

## test-nightly-regression: run the nightly cron pipeline on demand (without
##                          waiting for 02:00). ~10-15 min. Costly — only run when
##                          you have post-merge stage changes that need
##                          integration-wide validation.
##                          Output is appended to $(NIGHTLY_LOG) — same
##                          destination the cron job writes to, so manual
##                          runs accumulate alongside scheduled ones.
test-nightly-regression:
	@mkdir -p $(LOG_DIR) || { \
		echo "❌ No puedo crear $(LOG_DIR) — ¿sos root? ¿está montado el dir?"; \
		exit 1; \
	}
	@bash $(NIGHTLY) >> $(NIGHTLY_LOG) 2>&1 || { \
		echo "❌ nightly_regression.sh exited non-zero — see tail of $(NIGHTLY_LOG)"; \
		exit 1; \
	}
	@echo "✅ test-nightly-regression OK — tail $(NIGHTLY_LOG)"

## install-cron: install the project crontab into the current user's crontab.
##              Requires the user to be the runtime owner (commonly root) and
##              an explicit confirmation via env var (prevents accidental
##              `crontab -r`-style destruction). Env comparison is
##              case-insensitive so CONFIRM=yes / YES / Yes all work.
##
##              Usage:
##                make preview-cron             # dry-run, prints the crontab
##                make install-cron CONFIRM=yes # installs the crontab
install-cron:
	@if [ "$(CONFIRM_LC)" != "yes" ]; then \
		echo "⚠️  This will REPLACE your current crontab with infra/cron/ccf-platform."; \
		echo "    Run \`make preview-cron\` first to inspect, then:"; \
		echo "    make install-cron CONFIRM=yes"; \
		exit 1; \
	}
	@crontab $(CRONTAB_FILE)
	@echo "✅ crontab installed. Verify with: crontab -l | grep ccf"

# CONFIRM_LC normalizes CONFIRM to lowercase so the install-cron guard is
# case-insensitive (CONFIRM=yes / YES / Yes / yEs all work).
CONFIRM_LC  := $(shell echo $(CONFIRM) | tr '[:upper:]' '[:lower:]')

## preview-cron: print the crontab entry that would be installed (dry-run).
preview-cron:
	@echo "─── infra/cron/ccf-platform ───"
	@cat $(CRONTAB_FILE)
	@echo "─── end ───"

## clean: drop __pycache__/.pytest_cache/.ruff_cache artifacts.
clean:
	@find . -type d -name '__pycache__' -not -path '*/node_modules/*' -prune -exec rm -rf {} +
	@find . -type d -name '.pytest_cache' -not -path '*/node_modules/*' -prune -exec rm -rf {} +
	@find . -type d -name '.ruff_cache' -not -path '*/node_modules/*' -prune -exec rm -rf {} +
	@echo "✅ Python caches cleared"
