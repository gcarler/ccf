#!/usr/bin/env python3
"""Enforce module ownership and branch/worktree boundaries before a push."""

from __future__ import annotations

import argparse
import subprocess
import sys

COMMON_PREFIXES = (
    "scripts/",
    "frontend/scripts/",
    "tests/test_structural_contracts.py",
    "tests/test_select_quality_checks.py",
    "tests/test_branch_contract.py",
    "docs/RUNBOOK_PRODUCCION.md",
    "AGENTS_RULES_CCF.md",
    "REGLAS.md",
)

MODULE_PREFIXES: dict[str, tuple[str, ...]] = {
    "platform": (
        "backend/core/",
        "backend/models_kernel.py",
        "backend/models_auth.py",
        "frontend/src/app/plataforma/layout.tsx",
        "frontend/src/components/workspace/",
        "frontend/src/components/ui/",
        "frontend/src/design/",
        "frontend/src/context/",
        "frontend/src/lib/",
    ),
    "academy": (
        "backend/api/academy",
        "backend/crud/academy",
        "backend/models_academy",
        "backend/schemas/academy",
        "frontend/src/app/plataforma/academy/",
        "frontend/src/components/academy/",
        "frontend/tests/e2e/academy/",
        "tests/test_academy_",
        "docs/ACADEMY_",
        "docs/ESTADO_ACADEMY.md",
        "docs/PLAN_ACADEMY_",
    ),
    "messaging": (
        "backend/api/messaging",
        "backend/api/chat",
        "backend/api/community",
        "backend/services/messaging",
        "backend/schemas/notifications",
        "frontend/src/app/plataforma/messages/",
        "frontend/src/app/plataforma/inbox/",
        "frontend/src/app/plataforma/community/",
        "frontend/src/components/messaging/",
        "frontend/tests/e2e/messaging/",
        "tests/test_messaging",
        "tests/test_chat_sede_isolation.py",
        "docs/MESSAGING_",
        "docs/ESTADO_MESSAGING_",
        "docs/PLAN_MESSAGING_",
    ),
    "evangelism": (
        "backend/api/evangelism",
        "backend/api/evangelism_main",
        "backend/crud/evangelism",
        "backend/models_evangelism",
        "backend/schemas/evangelism",
        "frontend/src/app/plataforma/evangelism/",
        "frontend/src/components/evangelism",
        "frontend/tests/e2e/evangelism/",
        "tests/test_evangelism_",
        "docs/EVANGELISMO_",
        "docs/ESTADO_EVANGELISMO.md",
        "docs/PLAN_EVANGELISMO_",
    ),
    "cms": (
        "backend/api/cms",
        "backend/api/cms_v2",
        "backend/api/enterprise_cms",
        "backend/crud/cms",
        "backend/models_cms",
        "backend/schemas/cms",
        "frontend/src/app/plataforma/cms/",
        "frontend/src/app/(public)/pastores/",
        "frontend/src/components/public/",
        "frontend/src/hooks/useCmsV2Page.ts",
        "frontend/src/lib/cms/",
        "frontend/src/components/cms/",
        "frontend/tests/cms-",
        "frontend/tests/e2e/cms",
        "tests/test_cms_",
        "docs/CMS_",
        "docs/ESTADO_CMS.md",
        "docs/PLAN_CMS_",
    ),
    "crm": (
        "backend/api/crm",
        "backend/crud/crm",
        "backend/models_crm",
        "backend/schemas/crm",
        "frontend/src/app/plataforma/crm/",
        "frontend/src/components/crm/",
        "frontend/tests/e2e/crm/",
        "tests/test_crm_",
        "docs/CRM_",
        "docs/ESTADO_CRM.md",
        "docs/PLAN_CRM_",
    ),
    "projects": (
        "backend/api/projects",
        "backend/crud/projects",
        "backend/models_projects",
        "backend/schemas/projects",
        "frontend/src/app/plataforma/projects/",
        "frontend/src/components/projects/",
        "frontend/tests/e2e/projects/",
        "tests/test_projects",
        "docs/PROJECTS_",
        "docs/ESTADO_PROYECTOS.md",
    ),
    "agenda": (
        "backend/api/agenda",
        "backend/crud/agenda",
        "backend/models_agenda",
        "backend/schemas/agenda",
        "frontend/src/app/plataforma/agenda/",
        "frontend/src/components/agenda/",
        "frontend/tests/e2e/agenda/",
        "tests/test_agenda",
        "docs/AGENDA_",
        "docs/ESTADO_AGENDA.md",
    ),
    "frontend": (
        "frontend/src/",
        "frontend/tests/",
        "docs/FRONTEND_",
    ),
}

BRANCH_MODULE_ALIASES = {
    "feature/modulo-estructural": "platform",
    "feature/security-hardening": "platform",
    "feat/contextual-roles-recovery": "platform",
    "feature/frontend-ui": "frontend",
    "feature/events-evangelism": "evangelism",
    "fix/color-palette-regression": "frontend",
    "fix/public-legacy-redirects": "cms",
}

BRANCH_FAMILIES = ("feature", "feat", "fix", "refactor", "test")


def _matches(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes)


def module_for_branch(branch: str) -> str | None:
    """Resolve a module owner from a conventional branch name."""
    if branch in BRANCH_MODULE_ALIASES:
        return BRANCH_MODULE_ALIASES[branch]
    if "/" not in branch:
        return None
    family, suffix = branch.split("/", 1)
    if family not in BRANCH_FAMILIES:
        return None
    for module in MODULE_PREFIXES:
        if suffix == module or suffix.startswith(f"{module}-") or suffix.startswith(f"{module}/"):
            return module
    return None


def branch_name_violations(branch: str) -> list[str]:
    """Validate names for branches that participate in the governed flow."""
    if branch == "main" or branch.startswith("archive/merged/"):
        return []
    if branch.startswith("integration/"):
        return [] if branch != "integration/" else ["integration/ requiere un nombre de cambio"]
    if branch.startswith("docs/") or branch.startswith("backup/") or branch.startswith("deploy/"):
        return []
    if branch.split("/", 1)[0] in BRANCH_FAMILIES and module_for_branch(branch) is None:
        return [f"rama sin módulo propietario reconocido: {branch}"]
    return []


def ownership_violations(branch: str, files: list[str]) -> list[str]:
    """Return changed paths that do not belong to the target branch owner."""
    name_violations = branch_name_violations(branch)
    if name_violations:
        return name_violations
    if branch == "main" or branch.startswith("integration/") or branch.startswith("archive/merged/"):
        return []
    if branch.startswith("docs/"):
        allowed = COMMON_PREFIXES + ("docs/",)
        return [path for path in files if not _matches(path, allowed)]

    module = module_for_branch(branch)
    if module is None:
        return []
    allowed = MODULE_PREFIXES[module] + COMMON_PREFIXES
    return [path for path in files if not _matches(path, allowed)]


def changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--diff-filter=ACMRTUXB", "--name-only", f"{base}...{head}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", default="HEAD")
    args = parser.parse_args()

    files = changed_files(args.base, args.head)
    violations = ownership_violations(args.branch, files)
    if not violations:
        print(f"Branch contract OK: {args.branch} ({len(files)} changed files)")
        return 0

    print(f"Branch contract violated by {args.branch}:", file=sys.stderr)
    for path in violations:
        print(f"  - {path}", file=sys.stderr)
    print("Commit the change on its owning module branch, then integrate through integration/<change>.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
