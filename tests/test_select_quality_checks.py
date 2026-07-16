from scripts.select_quality_checks import select_quality_checks


def test_docs_only_selects_no_module_checks():
    checks = select_quality_checks(["docs/ESTADO_CRM.md", "docs/CMS_QA_CHECKLIST.md"])
    assert checks == []


def test_crm_paths_select_crm_quality_once():
    checks = select_quality_checks(
        [
            "backend/api/crm/personas.py",
            "frontend/src/app/plataforma/crm/personas/page.tsx",
            "tests/test_crm_domain.py",
        ]
    )
    assert checks == ["crm_quality"]


def test_shared_paths_select_critical_modules():
    checks = select_quality_checks(["frontend/src/components/ui/TableView.tsx"])
    assert checks == [
        "academy_quality",
        "agenda_quality",
        "cms_quality",
        "crm_quality",
        "evangelism_quality",
        "messaging_quality",
        "platform_quality",
        "projects_quality",
    ]


def test_pre_push_selector_changes_select_critical_modules():
    checks = select_quality_checks(["scripts/hooks/pre-push", "scripts/select_quality_checks.py"])
    assert checks == [
        "academy_quality",
        "agenda_quality",
        "cms_quality",
        "crm_quality",
        "evangelism_quality",
        "messaging_quality",
        "platform_quality",
        "projects_quality",
    ]


def test_migration_selects_critical_modules():
    checks = select_quality_checks(["alembic/versions/20260717_0001_normalize_project_status.py"])
    assert checks == [
        "academy_quality",
        "agenda_quality",
        "cms_quality",
        "crm_quality",
        "evangelism_quality",
        "messaging_quality",
        "platform_quality",
        "projects_quality",
    ]


def test_cms_frontend_and_tests_select_cms_quality():
    checks = select_quality_checks(
        [
            "frontend/src/app/plataforma/cms/page.tsx",
            "frontend/tests/cms-components.test.ts",
            "tests/test_enterprise_cms.py",
        ]
    )
    assert checks == ["cms_quality"]


def test_agenda_paths_select_agenda_quality():
    checks = select_quality_checks(
        [
            "backend/api/agenda.py",
            "frontend/src/app/plataforma/calendar/page.tsx",
        ]
    )
    assert checks == ["agenda_quality"]


def test_platform_paths_select_platform_quality():
    checks = select_quality_checks(
        [
            "backend/api/auth_v3.py",
            "backend/models_kernel.py",
        ]
    )
    assert checks == ["platform_quality"]
