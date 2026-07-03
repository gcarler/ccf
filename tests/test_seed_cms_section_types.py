"""Tests for scripts/seed_cms_section_types.py.

Hardening contract:
  * Seed populates exactly the canonical list on empty DB, all active.
  * Seed is idempotent across consecutive runs.
  * Manual deletes are restored on re-seed.
  * Admin ``is_active=False`` is preserved on re-seed.
  * Description drift between canonical and DB is corrected on re-seed.
  * ``verify_section_types`` reports zero drift after a clean seed.
  * ``--check`` CLI mode exits 1 on drift and 0 once synced.
"""

from __future__ import annotations

from backend.models_cms import CmsSectionType
from scripts.seed_cms_section_types import (
    EXPECTED_SECTION_TYPES,
    SeedResult,
    VerifyResult,
    apply_section_types,
    main,
    verify_section_types,
)

CANONICAL_NAMES = {name for name, _ in EXPECTED_SECTION_TYPES}
CANONICAL_DESCRIPTIONS = dict(EXPECTED_SECTION_TYPES)


class TestSeedCmsSectionTypes:
    def test_seed_empty_db_populates_catalog(self, db_session):
        """Empty DB becomes exactly N canonical rows, all unique, all active."""
        result = apply_section_types(db_session)

        rows = db_session.query(CmsSectionType).all()
        assert isinstance(result, SeedResult)
        assert result.added == len(EXPECTED_SECTION_TYPES)
        assert result.updated == 0
        assert result.total_after == len(EXPECTED_SECTION_TYPES)

        names = {row.name for row in rows}
        assert names == CANONICAL_NAMES
        assert all(row.is_active for row in rows)
        assert all(
            row.description == CANONICAL_DESCRIPTIONS[row.name] for row in rows
        )

    def test_seed_is_idempotent_on_sequential_runs(self, db_session):
        """Running the seed twice adds 0 and updates 0 on the second pass."""
        first = apply_section_types(db_session)
        second = apply_section_types(db_session)

        assert first.added == len(EXPECTED_SECTION_TYPES)
        assert second.added == 0
        assert second.updated == 0
        assert second.total_after == len(EXPECTED_SECTION_TYPES)

    def test_seed_restores_manually_deleted_row(self, db_session):
        """A row deleted manually between runs is re-inserted on the next run."""
        apply_section_types(db_session)
        target = "countdown"
        deleted = (
            db_session.query(CmsSectionType).filter_by(name=target).delete()
        )
        db_session.commit()
        assert deleted == 1

        result = apply_section_types(db_session)
        assert result.added == 1
        assert result.updated == 0
        assert (
            db_session.query(CmsSectionType).filter_by(name=target).count() == 1
        )

    def test_seed_preserves_admin_deactivation_and_syncs_description(self, db_session):
        """Hardening policy: do NOT touch ``is_active``; DO sync description drift."""
        apply_section_types(db_session)
        hero = db_session.query(CmsSectionType).filter_by(name="hero").first()
        cards = db_session.query(CmsSectionType).filter_by(name="cards").first()
        hero.is_active = False
        cards.description = "STALE DESC FROM PRIOR RELEASE"
        db_session.commit()

        result = apply_section_types(db_session)

        hero = db_session.query(CmsSectionType).filter_by(name="hero").first()
        cards = db_session.query(CmsSectionType).filter_by(name="cards").first()
        assert hero.is_active is False, (
            "Admin deactivation must be respected on subsequent seeds"
        )
        assert cards.description == CANONICAL_DESCRIPTIONS["cards"], (
            "Description drift must be synced to canonical list"
        )
        assert result.added == 0
        assert result.updated == 1

    def test_verify_reports_clean_after_seed(self, db_session):
        """verify_section_types reports no missing and no desc drift post-seed."""
        apply_section_types(db_session)
        result = verify_section_types(db_session)

        assert isinstance(result, VerifyResult)
        assert result.is_synced is True
        assert result.missing == []
        assert result.out_of_sync_desc == []

    def test_cli_check_mode_exits_one_then_zero(self, db_session):
        """``--check`` returns 1 on first run (drift), 0 after a clean seed."""
        assert main(["--check"], db=db_session) == 1
        apply_section_types(db_session)
        assert main(["--check"], db=db_session) == 0

    def test_cli_apply_mode_returns_zero_and_persists(self, db_session):
        """``main([])`` runs the apply path: returns 0 and inserts the catalog."""
        rc = main([], db=db_session)
        assert rc == 0
        assert (
            db_session.query(CmsSectionType).filter_by(name="hero").count() == 1
        )
        assert (
            db_session.query(CmsSectionType).count() == len(EXPECTED_SECTION_TYPES)
        )

    def test_verify_reports_extra_rows_not_in_canonical(self, db_session):
        """Rows in DB that are not in canonical land in ``extra``."""
        apply_section_types(db_session)
        db_session.add(
            CmsSectionType(name="legacy_type", description="orphan", is_active=True)
        )
        db_session.commit()

        result = verify_section_types(db_session)
        assert result.extra == ["legacy_type"]
        # An orphan is informational — sync status remains clean.
        assert result.is_synced is True
        assert result.missing == []
        assert result.out_of_sync_desc == []

    def test_desynced_inactive_row_still_reports_drift(self, db_session):
        """A row with stale description AND ``is_active=False`` still drifts."""
        apply_section_types(db_session)
        cards = db_session.query(CmsSectionType).filter_by(name="cards").first()
        cards.is_active = False
        cards.description = "STALE DESC"
        db_session.commit()

        result = verify_section_types(db_session)
        assert "cards" in result.deactivated
        assert "cards" in result.out_of_sync_desc
        assert result.is_synced is False
        assert main(["--check"], db=db_session) == 1
