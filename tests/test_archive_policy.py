from pathlib import Path  # noqa: I001


ROOT = Path(__file__).parents[1]


def test_archive_registry_forbids_reactivation_and_preserves_candidates():
    registry = (ROOT / "docs/ARCHIVED_BRANCHES.md").read_text()
    assert "ARCHIVADA - NO REACTIVAR" in registry
    assert "feature/projects-whiteboard" in registry
    assert "fix/color-palette-regression" in registry


def test_archive_helpers_have_explicit_categories_and_immutable_paths():
    helper = (ROOT / "scripts/archive_branch.sh").read_text()
    hook = (ROOT / "scripts/hooks/pre-push").read_text()
    assert "merged|stale" in helper
    assert "archive/$CATEGORY/" in helper
    assert "archive/stale/*" in hook
    assert "no se sobrescribe" in hook
