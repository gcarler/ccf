#!/usr/bin/env python3
"""Enforce module ownership and branch/worktree boundaries before a push.

The hook passes the branch and the exact diff base.  This guard deliberately
checks only the files introduced by the push, so older history can be adopted
without rewriting it while new cross-module drift is rejected early.
"""

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
    "feature/modulo-estructural": (
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
    "feature/academy": (
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
    "feature/messaging": (
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
    "feature/evangelism": (
        "backend/api/evangelism",
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
    "feature/cms": (
        "backend/api/cms",
        "backend/api/cms_v2",
        "backend/api/enterprise_cms",
        "backend/crud/cms",
        "backend/models_cms",
        "backend/schemas/cms",
        "frontend/src/app/plataforma/cms/",
        "frontend/src/components/cms/",
        "frontend/tests/cms-",
        "frontend/tests/e2e/cms",
        "tests/test_cms_",
        "docs/CMS_",
        "docs/ESTADO_CMS.md",
        "docs/PLAN_CMS_",
    ),
}


def _matches(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path == prefix or path.startswith(prefix) for prefix in prefixes)


def ownership_violations(branch: str, files: list[str]) -> list[str]:
    """Return changed paths that do not belong to the target module branch."""

    prefixes = MODULE_PREFIXES.get(branch)
    if prefixes is None:
        # main/develop and unregistered feature branches are intentionally not
        # assigned a module owner; the hook still validates their quality.
        return []

    allowed = prefixes + COMMON_PREFIXES
    return [path for path in files if not _matches(path, allowed)]


def changed_files(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--diff-filter=ACMRTUXB", "--name-only", base, head],
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
        print(f"✓ Branch contract OK: {args.branch} ({len(files)} changed files)")
        return 0

    print(f"✗ Branch contract violated by {args.branch}:", file=sys.stderr)
    print("  Estos archivos pertenecen a otro módulo o requieren integración estructural:", file=sys.stderr)
    for path in violations:
        print(f"  - {path}", file=sys.stderr)
    print("  Haz el commit en la rama propietaria y luego integra por el flujo definido.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
