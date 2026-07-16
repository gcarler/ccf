#!/usr/bin/env python3
"""Select module quality checks based on changed files.

Usage:
    python scripts/select_quality_checks.py --base origin/main --head HEAD
    python scripts/select_quality_checks.py --files backend/api/crm/personas.py frontend/src/app/plataforma/crm/page.tsx
    python scripts/select_quality_checks.py --base origin/main --head HEAD --summary
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Rule:
    check_id: str
    prefixes: tuple[str, ...]


MODULE_RULES: tuple[Rule, ...] = (
    Rule(
        "frontend_build",
        (
            "frontend/src/",
            "frontend/tests/e2e/",
            "frontend/package.json",
            "frontend/package-lock.json",
            "frontend/tsconfig.json",
            "frontend/next.config.mjs",
            "frontend/eslint.config.mjs",
            "frontend/src/components/",
            "frontend/src/lib/",
            "frontend/src/context/",
        ),
    ),
    Rule(
        "projects_quality",
        (
            "docs/ESTADO_PROYECTOS.md",
            "docs/PLAN_PROYECTOS_CALIDAD.md",
            "docs/PROJECTS_API_CONTRACTS.md",
            "docs/PROJECTS_QA_CHECKLIST.md",
            "docs/PROJECTS_RBAC_MATRIX.md",
            "docs/PLAN_VISTAS_EDITABLES_PROYECTOS.md",
            "backend/api/projects.py",
            "backend/models_projects.py",
            "backend/schemas/projects.py",
            "frontend/src/app/plataforma/projects/",
            "frontend/src/components/projects/",
            "frontend/tests/e2e/projects/",
            "frontend/src/hooks/useProjectTasks.ts",
            "frontend/src/context/ProjectUpdateContext.tsx",
            "scripts/test_projects_quality.py",
            "tests/test_projects_",
        ),
    ),
    Rule(
        "crm_quality",
        (
            "docs/ESTADO_CRM.md",
            "docs/PLAN_CRM_CALIDAD.md",
            "docs/CRM_API_CONTRACTS.md",
            "docs/CRM_QA_CHECKLIST.md",
            "docs/CRM_RBAC_MATRIX.md",
            "backend/api/crm/",
            "backend/models_crm.py",
            "backend/models_crm_pipeline.py",
            "backend/schemas/crm/",
            "backend/schemas/crm_",
            "backend/crud/crm.py",
            "backend/crud/crm_/",
            "backend/services/crm_resource_bank.py",
            "frontend/src/app/plataforma/crm/",
            "frontend/tests/e2e/crm/",
            "scripts/test_crm_quality.py",
            "tests/test_crm_",
        ),
    ),
    Rule(
        "academy_quality",
        (
            "docs/ESTADO_ACADEMY.md",
            "docs/PLAN_ACADEMY_CALIDAD.md",
            "docs/ACADEMY_API_CONTRACTS.md",
            "docs/ACADEMY_QA_CHECKLIST.md",
            "docs/ACADEMY_RBAC_MATRIX.md",
            "backend/api/academy.py",
            "backend/crud/academy.py",
            "backend/models_academy_core.py",
            "backend/schemas/academy.py",
            "frontend/src/app/plataforma/academy/",
            "frontend/tests/e2e/academy/",
            "scripts/test_academy_quality.py",
            "tests/test_academy_",
        ),
    ),
    Rule(
        "cms_quality",
        (
            "docs/ESTADO_CMS.md",
            "docs/PLAN_CMS_CALIDAD.md",
            "docs/CMS_API_CONTRACTS.md",
            "docs/CMS_QA_CHECKLIST.md",
            "docs/CMS_RBAC_MATRIX.md",
            "docs/PLAN_CMS_100.md",
            "backend/api/cms.py",
            "backend/api/cms_v2.py",
            "backend/api/enterprise_cms.py",
            "backend/api/_cms_helpers/",
            "backend/crud/cms.py",
            "backend/crud/cms_pastors_sync.py",
            "backend/models_cms.py",
            "backend/schemas/cms.py",
            "backend/schemas/cms_v2_sections.py",
            "frontend/src/app/plataforma/cms/",
            "frontend/tests/cms-",
            "frontend/tests/e2e/cms-",
            "frontend/tests/e2e/cms/",
            "scripts/test_cms_quality.py",
            "tests/test_cms_",
            "tests/test_enterprise_cms.py",
        ),
    ),
    Rule(
        "evangelism_quality",
        (
            "docs/ESTADO_EVANGELISMO.md",
            "docs/PLAN_EVANGELISMO_CALIDAD.md",
            "docs/EVANGELISMO_API_CONTRACTS.md",
            "docs/EVANGELISMO_QA_CHECKLIST.md",
            "docs/EVANGELISMO_RBAC_MATRIX.md",
            "docs/AUDITORIA_FLUJO_EVANGELISMO_CCF.md",
            "backend/api/evangelism.py",
            "backend/api/evangelism_",
            "backend/api/evangelism/",
            "backend/models_evangelism.py",
            "backend/schemas/evangelism.py",
            "backend/crud/evangelism.py",
            "backend/services/evangelism_",
            "frontend/src/app/plataforma/evangelism/",
            "frontend/src/components/evangelism/",
            "frontend/src/components/evangelismFlow/",
            "frontend/tests/e2e/evangelism/",
            "scripts/test_evangelism_quality.py",
            "tests/test_evangelism_",
            "tests/test_calculo_sesiones.py",
        ),
    ),
    Rule(
        "messaging_quality",
        (
            "docs/ESTADO_MESSAGING_COMMUNITY.md",
            "docs/PLAN_MESSAGING_CALIDAD.md",
            "docs/MESSAGING_COMMUNITY_API_CONTRACTS.md",
            "docs/MESSAGING_COMMUNITY_QA_CHECKLIST.md",
            "docs/MESSAGING_COMMUNITY_RBAC_MATRIX.md",
            "backend/api/messaging.py",
            "backend/api/chat.py",
            "backend/api/community.py",
            "backend/services/messaging.py",
            "backend/schemas/notifications.py",
            "backend/crud/crm_/communication.py",
            "backend/crud/crm_/notifications.py",
            "frontend/src/app/plataforma/messages/",
            "frontend/src/app/plataforma/inbox/",
            "frontend/src/app/plataforma/community/",
            "frontend/src/app/plataforma/community/messages/",
            "frontend/tests/e2e/messaging/",
            "scripts/test_messaging_quality.py",
            "tests/test_messaging",
            "tests/test_chat_sede_isolation.py",
        ),
    ),
    Rule(
        "agenda_quality",
        (
            "docs/ESTADO_AGENDA.md",
            "docs/PLAN_AGENDA_CALIDAD.md",
            "docs/AGENDA_API_CONTRACTS.md",
            "docs/AGENDA_QA_CHECKLIST.md",
            "docs/AGENDA_RBAC_MATRIX.md",
            "docs/SYSTEM_CALENDAR_CONTRACT.md",
            "backend/api/agenda.py",
            "backend/crud/agenda.py",
            "backend/schemas/agenda.py",
            "backend/models_agenda.py",
            "frontend/src/app/plataforma/agenda/",
            "frontend/src/app/plataforma/calendar/",
            "frontend/src/components/calendar/",
            "frontend/src/components/ui/UniversalCalendarView.tsx",
            "frontend/tests/e2e/agenda/",
            "scripts/test_agenda_quality.py",
            "tests/test_agenda_api.py",
        ),
    ),
    Rule(
        "platform_quality",
        (
            "docs/ESTADO_PLATAFORMA_COMPARTIDA.md",
            "docs/PLAN_PLATAFORMA_COMPARTIDA_CALIDAD.md",
            "docs/PLATAFORMA_AUTH_RBAC_API_UI.md",
            "docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md",
            "docs/PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md",
            "docs/PLATAFORMA_UI_BASE_PROTEGIDA.md",
            "docs/PLATAFORMA_MATRIZ_MODULAR.md",
            "docs/BACKLOG_DRIFT_TRANSVERSAL_CCF.md",
            "backend/api/auth_v3.py",
            "backend/api/admin.py",
            "backend/core/permissions.py",
            "backend/core/security.py",
            "backend/models_auth.py",
            "backend/models_kernel.py",
            "frontend/src/lib/http.ts",
            "frontend/src/lib/workspaceAccess.ts",
            "frontend/src/lib/protectedRouteAccess.ts",
            "frontend/src/lib/agGrid.ts",
            "frontend/src/components/WorkspaceLayout.tsx",
            "frontend/src/components/WorkspaceMainSidebar.tsx",
            "frontend/src/components/WorkspaceMiniSidebar.tsx",
            "frontend/src/components/ProtectedRoute.tsx",
            "frontend/src/components/ui/TableView.tsx",
            "frontend/src/components/ui/UniversalTableView.tsx",
            "frontend/src/components/ui/UniversalCalendarView.tsx",
            "frontend/src/components/ui/UniversalGanttView.tsx",
            "frontend/src/components/ui/inline-editors/",
            "frontend/tests/e2e/platform-critical-routes.spec.ts",
            "scripts/test_platform_quality.py",
            "tests/test_auth",
            "tests/test_permissions_and_more.py",
            "tests/test_arquitectura_100pct.py",
        ),
    ),
)


SHARED_PREFIXES: tuple[str, ...] = (
    "backend/core/permissions.py",
    "backend/core/security.py",
    "backend/core/storage.py",
    "backend/core/uploads.py",
    "backend/models.py",
    "backend/models_auth.py",
    "backend/models_shared.py",
    "frontend/next.config.mjs",
    "frontend/src/app/plataforma/layout.tsx",
    "frontend/src/components/ui/TableView.tsx",
    "frontend/src/components/ui/UniversalTableView.tsx",
    "frontend/src/components/ui/UniversalCalendarView.tsx",
    "frontend/src/components/ui/UniversalGanttView.tsx",
    "frontend/src/components/ui/inline-editors/",
    "frontend/src/components/WorkspaceLayout.tsx",
    "frontend/src/components/WorkspaceMainSidebar.tsx",
    "frontend/src/components/WorkspaceMiniSidebar.tsx",
    "frontend/src/components/ProtectedRoute.tsx",
    "frontend/src/lib/workspaceAccess.ts",
    "frontend/src/lib/protectedRouteAccess.ts",
    "frontend/src/lib/agGrid.ts",
    "frontend/tests/e2e/platform-critical-routes.spec.ts",
    "frontend/src/lib/http",
    "frontend/src/lib/api",
    "scripts/hooks/pre-push",
    "scripts/select_quality_checks.py",
    "tests/test_select_quality_checks.py",
)


CRITICAL_CHECKS: tuple[str, ...] = (
    "frontend_build",
    "platform_quality",
    "projects_quality",
    "crm_quality",
    "academy_quality",
    "cms_quality",
    "evangelism_quality",
    "messaging_quality",
    "agenda_quality",
)


def _normalize(path: str) -> str:
    return path.strip().lstrip("./")


def _matches(path: str, prefix: str) -> bool:
    path = _normalize(path)
    prefix = _normalize(prefix)
    return path == prefix or path.startswith(prefix)


def changed_files_from_git(base: str, head: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", base, head],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [_normalize(line) for line in result.stdout.splitlines() if line.strip()]


def select_quality_checks(changed_files: list[str]) -> list[str]:
    return sorted(explain_selection(changed_files).keys())


def explain_selection(changed_files: list[str]) -> dict[str, list[str]]:
    selected: set[str] = set()
    reasons: dict[str, set[str]] = {}
    normalized = [_normalize(path) for path in changed_files if path.strip()]

    for path in normalized:
        if any(_matches(path, prefix) for prefix in SHARED_PREFIXES):
            reason = f"shared:{path}"
            selected.update(CRITICAL_CHECKS)
            for check_id in CRITICAL_CHECKS:
                reasons.setdefault(check_id, set()).add(reason)
            continue
        if _matches(path, "alembic/versions/"):
            reason = f"migration:{path}"
            selected.update(CRITICAL_CHECKS)
            for check_id in CRITICAL_CHECKS:
                reasons.setdefault(check_id, set()).add(reason)
            continue
        for rule in MODULE_RULES:
            if any(_matches(path, prefix) for prefix in rule.prefixes):
                selected.add(rule.check_id)
                reasons.setdefault(rule.check_id, set()).add(path)

    return {
        check_id: sorted(reasons.get(check_id, set()))
        for check_id in sorted(selected)
    }


def summarize(changed_files: list[str], checks: list[str]) -> str:
    if not changed_files:
        return "No changed files detected."
    if not checks:
        return f"No module checks selected for {len(changed_files)} changed files."
    return (
        f"{len(changed_files)} changed files -> "
        + ", ".join(checks)
    )


def format_explanations(changed_files: list[str]) -> list[str]:
    explained = explain_selection(changed_files)
    lines = []
    for check_id in sorted(explained):
        reasons = ", ".join(explained[check_id])
        lines.append(f"{check_id}: {reasons}")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--files", nargs="*", default=None)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--explain", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    changed_files = args.files if args.files is not None else changed_files_from_git(args.base, args.head)
    checks = select_quality_checks(changed_files)
    if args.summary:
        print(summarize(changed_files, checks))
        return 0
    if args.explain:
        for line in format_explanations(changed_files):
            print(line)
        return 0
    for check in checks:
        print(check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
