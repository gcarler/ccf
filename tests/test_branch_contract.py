from scripts.check_branch_contract import ownership_violations


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


def test_unknown_branch_is_not_assigned_a_module_owner():
    assert ownership_violations("feature/unknown", ["backend/api/academy.py"]) == []
