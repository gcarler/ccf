from scripts.check_branch_contract import (
    branch_name_violations,
    module_for_branch,
    ownership_violations,
)


def test_academy_accepts_only_academy_and_shared_infrastructure():
    files = [
        "backend/api/academy.py",
        "frontend/src/app/plataforma/academy/page.tsx",
        "tests/test_academy_quality.py",
        "scripts/hooks/pre-push",
    ]
    assert ownership_violations("feature/academy", files) == []


def test_academy_rejects_evangelism_and_cms_files():
    files = [
        "backend/api/evangelism_events/events_main.py",
        "frontend/src/components/cms/CmsMediaUrlField.tsx",
    ]
    assert ownership_violations("feature/academy", files) == files


def test_structural_accepts_shared_platform_files():
    files = [
        "frontend/src/components/workspace/WorkspaceLayout.tsx",
        "frontend/src/design/tokens.css",
        "scripts/select_quality_checks.py",
    ]
    assert ownership_violations("feature/modulo-estructural", files) == []


def test_module_suffixes_preserve_thematic_branches():
    assert module_for_branch("feature/evangelism-audit") == "evangelism"
    assert module_for_branch("feat/cms-nosotros-stats") == "cms"
    assert module_for_branch("feature/projects-whiteboard") == "projects"


def test_unknown_module_branch_is_rejected():
    assert branch_name_violations("feature/unknown")
    assert ownership_violations("feature/unknown", ["backend/api/academy.py"])


def test_integration_branch_accepts_cross_module_merge_result():
    assert branch_name_violations("integration/academy-cms-20260823") == []
    assert ownership_violations(
        "integration/academy-cms-20260823",
        ["backend/api/academy.py", "backend/api/cms.py"],
    ) == []


def test_docs_branch_accepts_governance_files_only():
    assert ownership_violations(
        "docs/branch-governance-protocol",
        ["AGENTS_RULES_CCF.md", "docs/RUNBOOK_PRODUCCION.md", "scripts/create_integration_branch.sh"],
    ) == []
    assert ownership_violations(
        "docs/branch-governance-protocol",
        ["backend/api/academy.py"],
    ) == ["backend/api/academy.py"]
