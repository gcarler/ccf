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


def test_projects_owns_evm_service_but_not_other_module_services():
    assert ownership_violations(
        "feature/projects-indicator-core",
        ["backend/services/project_evm_service.py"],
    ) == []
    assert ownership_violations(
        "feature/projects-indicator-core",
        ["backend/services/knowledge_base.py", "backend/services/academic_engine_service.py"],
    ) == ["backend/services/knowledge_base.py", "backend/services/academic_engine_service.py"]


def test_ci_and_shared_facades_have_platform_ownership():
    paths = [".github/workflows/ci.yml", "requirements.txt", ".coveragerc",
             "backend/models.py", "backend/schemas/__init__.py", "alembic/env.py",
             "frontend/vitest.config.ts"]
    assert ownership_violations("feature/platform-ci", paths) == []
    assert ownership_violations("feature/projects-ci", paths) == paths


def test_projects_owns_pmi_services_but_no_unrelated_apis():
    paths = ["backend/services/project_ccb_service.py", "backend/services/anydoc_service.py",
             "backend/services/wiki_pmi_service.py"]
    assert ownership_violations("feature/projects-pmi-quality", paths) == []
    foreign = ["backend/api/messaging.py", "backend/services/academic_engine_service.py"]
    assert ownership_violations("feature/projects-pmi-quality", foreign) == foreign


def test_finance_has_an_explicit_owner_and_rejects_foreign_module_files():
    own = ["backend/api/finance_suite.py", "tests/test_finance_multi_approval.py", "docs/FINANCE_API_CONTRACTS.md"]
    assert ownership_violations("feature/finance-quality", own) == []
    foreign = ["backend/api/projects.py", "backend/api/crm/personas.py"]
    assert ownership_violations("feature/finance-quality", foreign) == foreign


def test_projects_owns_only_its_exact_deployed_coq_revision():
    own = "alembic/canonical_versions/20261024_0001_add_coq_amount_to_project_dod_acceptances.py"
    foreign = "alembic/canonical_versions/20261018_0001_other.py"
    assert ownership_violations("feature/projects-quality", [own]) == []
    assert ownership_violations("feature/projects-quality", [foreign]) == [foreign]
    assert ownership_violations("feature/academy-quality", [own]) == [own]
