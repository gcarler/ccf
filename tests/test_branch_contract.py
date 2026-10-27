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


def _git_owner_sync_repository(tmp_path, monkeypatch):
    import subprocess

    # Real hooks export repository-local Git env. Keep fixture commands and
    # changed_files() inside their own repository even when run by pre-push.
    local_vars = subprocess.check_output(["git", "rev-parse", "--local-env-vars"], text=True).splitlines()
    for name in local_vars:
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.chdir(root)

    def git(*args):
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.PIPE).strip()

    git("init", "-q", "--initial-branch=main")
    git("config", "user.name", "Ownership Test")
    git("config", "user.email", "ownership@example.invalid")
    (root / "backend/api").mkdir(parents=True)
    (root / "backend/api/messaging.py").write_text("initial messaging\n")
    (root / "backend/api/academy.py").write_text("initial academy\n")
    git("add", ".")
    git("commit", "-qm", "initial")
    git("checkout", "-qb", "feature/messaging-proof")
    (root / "backend/api/messaging.py").write_text("published messaging\n")
    git("commit", "-qam", "messaging owner work")
    published = git("rev-parse", "HEAD")
    git("checkout", "-q", "main")
    (root / "backend/api/academy.py").write_text("reviewed upstream academy\n")
    git("commit", "-qam", "reviewed main work")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    git("checkout", "-q", "feature/messaging-proof")
    git("merge", "-q", "--no-edit", "main")
    return root, git, published


def test_owner_sync_excludes_upstream_main_but_preserves_new_owner_work(tmp_path, monkeypatch):
    from scripts.check_branch_contract import changed_files

    root, git, published = _git_owner_sync_repository(tmp_path, monkeypatch)
    (root / "backend/api/messaging.py").write_text("new messaging work after sync\n")
    git("commit", "-qam", "new messaging fix")
    paths = changed_files(published, "HEAD")
    assert paths == ["backend/api/messaging.py"]
    assert ownership_violations("feature/messaging-proof", paths) == []


def test_owner_sync_still_rejects_new_foreign_edits_and_files(tmp_path, monkeypatch):
    from scripts.check_branch_contract import changed_files

    root, git, published = _git_owner_sync_repository(tmp_path, monkeypatch)
    (root / "backend/api/academy.py").write_text("new unowned edit\n")
    (root / "backend/api/academy_new.py").write_text("new unowned file\n")
    git("add", ".")
    git("commit", "-qm", "unowned changes after sync")
    paths = changed_files(published, "HEAD")
    assert paths == ["backend/api/academy.py", "backend/api/academy_new.py"]
    assert ownership_violations("feature/messaging-proof", paths) == paths


def test_owner_sync_cannot_hide_foreign_deletion_or_cross_module_rename(tmp_path, monkeypatch):
    from scripts.check_branch_contract import changed_files

    root, git, published = _git_owner_sync_repository(tmp_path, monkeypatch)
    git("mv", "backend/api/academy.py", "backend/api/messaging_moved.py")
    git("commit", "-qm", "foreign rename after sync")
    paths = changed_files(published, "HEAD")
    assert paths == ["backend/api/academy.py", "backend/api/messaging_moved.py"]
    assert ownership_violations("feature/messaging-proof", paths) == ["backend/api/academy.py"]


def test_missing_canonical_main_keeps_original_owner_validation(tmp_path, monkeypatch):
    from scripts.check_branch_contract import changed_files

    root, git, published = _git_owner_sync_repository(tmp_path, monkeypatch)
    git("update-ref", "-d", "refs/remotes/origin/main")
    paths = changed_files(published, "HEAD")
    assert paths == ["backend/api/academy.py"]
    assert ownership_violations("feature/messaging-proof", paths) == paths
