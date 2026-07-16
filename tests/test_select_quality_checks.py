from scripts.select_quality_checks import format_explanations, select_quality_checks


def test_module_docs_select_owner_checks():
    checks = select_quality_checks(["docs/ESTADO_CRM.md", "docs/CMS_QA_CHECKLIST.md"])
    assert checks == ["cms_quality", "crm_quality"]


def test_generic_docs_only_selects_no_module_checks():
    checks = select_quality_checks(["docs/ARRANQUE_MODULAR_CCF.md", "docs/ESTANDARES_DESARROLLO.md"])
    assert checks == []


def test_crm_paths_select_crm_quality_once():
    checks = select_quality_checks(
        [
            "backend/api/crm/personas.py",
            "frontend/src/app/plataforma/crm/personas/page.tsx",
            "tests/test_crm_domain.py",
        ]
    )
    assert checks == ["crm_quality", "frontend_build"]


def test_crm_e2e_paths_select_crm_quality_and_frontend_build():
    checks = select_quality_checks(["frontend/tests/e2e/crm/smoke.spec.ts"])
    assert checks == ["crm_quality", "frontend_build"]


def test_projects_e2e_paths_select_projects_quality_and_frontend_build():
    checks = select_quality_checks(["frontend/tests/e2e/projects/smoke.spec.ts"])
    assert checks == ["frontend_build", "projects_quality"]


def test_shared_paths_select_critical_modules():
    checks = select_quality_checks(["frontend/src/components/ui/TableView.tsx"])
    assert checks == [
        "academy_quality",
        "agenda_quality",
        "cms_quality",
        "crm_quality",
        "evangelism_quality",
        "frontend_build",
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
        "frontend_build",
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
        "frontend_build",
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
    assert checks == ["cms_quality", "frontend_build"]


def test_cms_e2e_paths_select_cms_quality_and_frontend_build():
    checks = select_quality_checks(["frontend/tests/e2e/cms/smoke.spec.ts"])
    assert checks == ["cms_quality", "frontend_build"]


def test_agenda_paths_select_agenda_quality():
    checks = select_quality_checks(
        [
            "backend/api/agenda.py",
            "frontend/src/app/plataforma/calendar/page.tsx",
        ]
    )
    assert checks == ["agenda_quality", "frontend_build"]


def test_agenda_e2e_paths_select_agenda_quality_and_frontend_build():
    checks = select_quality_checks(["frontend/tests/e2e/agenda/smoke.spec.ts"])
    assert checks == ["agenda_quality", "frontend_build"]


def test_platform_paths_select_platform_quality():
    checks = select_quality_checks(
        [
            "backend/api/auth_v3.py",
            "backend/models_kernel.py",
        ]
    )
    assert checks == ["platform_quality"]


def test_protected_route_shared_path_selects_frontend_build_and_critical_modules():
    checks = select_quality_checks(["frontend/src/components/ProtectedRoute.tsx"])
    assert checks == [
        "academy_quality",
        "agenda_quality",
        "cms_quality",
        "crm_quality",
        "evangelism_quality",
        "frontend_build",
        "messaging_quality",
        "platform_quality",
        "projects_quality",
    ]


def test_workspace_access_shared_path_selects_frontend_build_and_critical_modules():
    checks = select_quality_checks(["frontend/src/lib/workspaceAccess.ts"])
    assert checks == [
        "academy_quality",
        "agenda_quality",
        "cms_quality",
        "crm_quality",
        "evangelism_quality",
        "frontend_build",
        "messaging_quality",
        "platform_quality",
        "projects_quality",
    ]


def test_platform_e2e_spec_selects_frontend_build_and_critical_modules():
    checks = select_quality_checks(["frontend/tests/e2e/platform-critical-routes.spec.ts"])
    assert checks == [
        "academy_quality",
        "agenda_quality",
        "cms_quality",
        "crm_quality",
        "evangelism_quality",
        "frontend_build",
        "messaging_quality",
        "platform_quality",
        "projects_quality",
    ]


def test_platform_docs_select_platform_quality():
    checks = select_quality_checks(
        ["docs/PLATAFORMA_AUTH_RUNTIME_CONTRACT.md", "docs/PLATAFORMA_COMPARTIDA_QA_CHECKLIST.md"]
    )
    assert checks == ["platform_quality"]


def test_projects_contract_docs_select_projects_quality():
    checks = select_quality_checks(["docs/PROJECTS_API_CONTRACTS.md"])
    assert checks == ["projects_quality"]


def test_explain_module_docs_reports_owner_and_path():
    lines = format_explanations(["docs/ESTADO_CRM.md"])
    assert lines == ["crm_quality: docs/ESTADO_CRM.md"]


def test_explain_shared_path_reports_shared_reason():
    lines = format_explanations(["frontend/src/components/ui/TableView.tsx"])
    assert "crm_quality: shared:frontend/src/components/ui/TableView.tsx" in lines
    assert "platform_quality: shared:frontend/src/components/ui/TableView.tsx" in lines


def test_explain_generic_docs_is_empty():
    assert format_explanations(["docs/ARRANQUE_MODULAR_CCF.md"]) == []


def test_academy_e2e_paths_select_academy_quality_and_frontend_build():
    checks = select_quality_checks(["frontend/tests/e2e/academy/smoke.spec.ts"])
    assert checks == ["academy_quality", "frontend_build"]


def test_messaging_e2e_paths_select_messaging_quality_and_frontend_build():
    checks = select_quality_checks(["frontend/tests/e2e/messaging/smoke.spec.ts"])
    assert checks == ["frontend_build", "messaging_quality"]


def test_evangelism_e2e_paths_select_evangelism_quality_and_frontend_build():
    checks = select_quality_checks(["frontend/tests/e2e/evangelism/smoke.spec.ts"])
    assert checks == ["evangelism_quality", "frontend_build"]
