"""Unit tests for the hardened 3-tier persona-by-name lookup.

Covers ``backend.crud.cms_pastors_sync._find_persona_by_name`` and the
isomorphic ``scripts.fix_pastor_photos.find_pastoral_persona_by_slug``.
The algorithm was hardened in 2026-07 to prevent first-name token-set
collisions (e.g. ``"Maria Martinez"`` picking ``"Ana Maria Martinez"``)
while preserving the original substring-overlap behaviour for cultures
where the public display name uses a middle name (e.g. CMS
``"Camilo Pájaro"`` matching CRM ``"José Camilo Pájaro"``).

Strategy
--------
1. Create a small set of ``Persona`` rows directly via the ``db_session``
   fixture (no CMS bootstrapping needed for the algorithm under test).
2. Call the lookup and assert the right ``Persona`` (or ``None``) is
   returned.
3. Cover exact match, first-name anchor, fallback, diacritic
   normalization, and edge cases (no match, single token, dead
   candidates).
"""

from __future__ import annotations

import uuid

# ── Helpers ────────────────────────────────────────────────────────────


def _make_persona(db, first_name: str, last_name: str, **kwargs):
    """Insert a ``Persona`` row and return the live instance.

    The default ``estado_vital='ACTIVO'`` matches the public-feed
    contract: FALLECIDO personas are excluded from the lookup.
    """
    from backend import models

    persona = models.Persona(
        id=kwargs.pop("id", uuid.uuid4()),
        first_name=first_name,
        last_name=last_name,
        estado_vital=kwargs.pop("estado_vital", "ACTIVO"),
        is_pastoral_leader=kwargs.pop("is_pastoral_leader", False),
        **kwargs,
    )
    db.add(persona)
    db.flush()
    return persona


# ── Tier 1: exact slug match (incl. diacritic normalization) ────────


class TestExactSlugMatch:
    def test_exact_match_returns_persona(self, db_session):
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        target = _make_persona(db_session, "Maria", "Martinez")
        _make_persona(db_session, "Ana", "Lopez")

        result = _find_persona_by_name(db_session, "Maria Martinez")
        assert result is not None
        assert result.id == target.id

    def test_diacritic_normalization_matches_ascii_variant(self, db_session):
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        # DB row has accent (canonical), query is ASCII (lossy import).
        target = _make_persona(db_session, "Camilo", "Pájaro")
        result = _find_persona_by_name(db_session, "Camilo Pajaro")
        assert result is not None
        assert result.id == target.id

    def test_query_with_accent_matches_ascii_db_row(self, db_session):
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        target = _make_persona(db_session, "Nehemias", "Morales")
        result = _find_persona_by_name(db_session, "Nehemías Morales")
        assert result is not None
        assert result.id == target.id


# ── Tier 2: first-name anchor (prevents collisions) ─────────────────


class TestFirstNameAnchor:
    def test_anchor_blocks_maria_martinez_vs_ana_maria_martinez(self, db_session):
        """The classic first-name-substring collision.

        The OLD substring-lookup picked ``Ana Maria Martinez`` for a
        query of ``Maria Martinez`` because both ``maria`` and
        ``martinez`` are substrings of the longer name. The first-name
        anchor (``maria`` == ``maria``) makes the correct target win
        unambiguously.
        """
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        correct = _make_persona(db_session, "Maria", "Martinez")
        _make_persona(db_session, "Ana", "Maria Martinez")

        result = _find_persona_by_name(db_session, "Maria Martinez")
        assert result is not None
        assert result.id == correct.id
        assert result.first_name == "Maria"

    def test_anchor_prefers_exact_target_over_compound_candidate(self, db_session):
        """When 2 candidates both match the anchor, the one with the
        more complete token overlap (full coverage) wins."""
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        # Both first tokens are "Maria"; full-coverage should beat
        # partial overlap.
        full = _make_persona(db_session, "Maria", "Martinez Lopez")
        _make_persona(db_session, "Maria Camila", "Martinez")

        result = _find_persona_by_name(db_session, "Maria Martinez")
        assert result is not None
        assert result.id == full.id


# ── Tier 3: fallback for middle-name-first cultures ─────────────────


class TestMiddleNameFallback:
    def test_fallback_matches_when_first_token_differs(self, db_session):
        """CMS displays ``Camilo Pájaro`` but CRM has ``José Camilo Pájaro``.

        Tier 2's first-token anchor (camilo vs jose) would reject this
        match. Tier 3 (pure token overlap) catches it because both
        slug tokens (``camilo`` and ``pajaro``) are present in the
        candidate's slugified name.
        """
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        crm = _make_persona(db_session, "José", "Camilo Pájaro")
        result = _find_persona_by_name(db_session, "Camilo Pájaro")
        assert result is not None
        assert result.id == crm.id

    def test_tier2_takes_precedence_over_tier3(self, db_session):
        """When both tiers match, Tier 2 (anchor-respecting) wins.

        Verifies the tier ordering: anchor should NOT be silently
        downgraded to fallback when both apply. We construct a case
        where Tier 2 finds the correct person and Tier 3 would also
        find a wrong person, and assert the Tier 2 result is returned.
        """
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        tier2_target = _make_persona(db_session, "Maria", "Martinez")
        # Tier 3 candidate: no anchor match, but full token overlap on
        # last token is also high — should not be selected.
        _make_persona(db_session, "Jose", "Maria Martinez")

        result = _find_persona_by_name(db_session, "Maria Martinez")
        assert result is not None
        assert result.id == tier2_target.id


# ── Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    def test_no_match_returns_none(self, db_session):
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        _make_persona(db_session, "Yair", "Macea")
        result = _find_persona_by_name(db_session, "Pablo Test")
        assert result is None

    def test_empty_query_returns_none(self, db_session):
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        _make_persona(db_session, "Yair", "Macea")
        assert _find_persona_by_name(db_session, "") is None
        assert _find_persona_by_name(db_session, "   ") is None

    def test_fallecido_persona_excluded(self, db_session):
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        _make_persona(
            db_session, "Maria", "Martinez", estado_vital="FALLECIDO"
        )
        result = _find_persona_by_name(db_session, "Maria Martinez")
        assert result is None

    def test_single_token_query_full_coverage(self, db_session):
        """A single-token query ('Yair') should match a multi-token
        persona ('Yair Macea') because the query is fully covered.
        """
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        target = _make_persona(db_session, "Yair", "Macea")
        result = _find_persona_by_name(db_session, "Yair")
        assert result is not None
        assert result.id == target.id

    def test_connector_words_filtered_in_query(self, db_session):
        """``'y'`` / ``'e'`` / ``'de'`` are dropped from query tokens so
        pair names collapse to their nouns (mirrors cms_pastors_sync
        canonical rule)."""
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        target = _make_persona(db_session, "Alex", "y Elvia")
        result = _find_persona_by_name(db_session, "Alex y Elvia")
        assert result is not None
        assert result.id == target.id

    def test_multi_token_query_below_threshold_rejected(self, db_session):
        """A 2-token query that only matches 1 token in the candidate
        should be rejected (preserves original 2-token threshold)."""
        from backend.crud.cms_pastors_sync import _find_persona_by_name

        _make_persona(db_session, "Maria", "Lopez")
        # 'maria' matches, 'gonzalez' does not → score 1 → reject
        result = _find_persona_by_name(db_session, "Maria Gonzalez")
        assert result is None


# ── Isomorphism with the fix-script lookup ───────────────────────────


class TestFixScriptIsomorphism:
    """The same algorithm must yield the same result for both
    ``_find_persona_by_name`` and ``find_pastoral_persona_by_slug`` so
    the public feed and the photo-fix pipeline agree on which Persona
    each pastor display name refers to.
    """

    def test_both_return_same_persona_for_canonical_slug(self, db_session):
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from fix_pastor_photos import find_pastoral_persona_by_slug

        from backend.crud.cms_pastors_sync import _find_persona_by_name

        target = _make_persona(
            db_session, "Camilo", "Pájaro", is_pastoral_leader=True
        )
        # Other leader that would win the wrong-pick if anchor were absent
        _make_persona(
            db_session, "Camilo", "Soto", is_pastoral_leader=True
        )

        from_sync = _find_persona_by_name(db_session, "Camilo Pájaro")
        from_script = find_pastoral_persona_by_slug(
            db_session, "camilo-pajaro"
        )
        assert from_sync is not None and from_script is not None
        assert from_sync.id == from_script.id == target.id

    def test_fix_script_filters_to_pastoral_leaders(self, db_session):
        """Unlike ``_find_persona_by_name``, the script variant only
        considers ``is_pastoral_leader=True``. A non-leader persona
        with the same name must NOT be returned by the script.
        """
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        from fix_pastor_photos import find_pastoral_persona_by_slug

        from backend.crud.cms_pastors_sync import _find_persona_by_name

        # A non-leader with the exact name (sync would pick it; script must not)
        _make_persona(
            db_session, "Camilo", "Pájaro", is_pastoral_leader=False
        )
        leader = _make_persona(
            db_session, "Camilo", "Pájaro", is_pastoral_leader=True
        )

        from_sync = _find_persona_by_name(db_session, "Camilo Pájaro")
        from_script = find_pastoral_persona_by_slug(
            db_session, "camilo-pajaro"
        )
        # Sync is non-deterministic on ties (returns the first it sees);
        # the canonical assertion is that the SCRIPT returns the leader.
        assert from_script is not None
        assert from_script.id == leader.id
        assert from_sync is not None  # sanity: sync returns SOMEONE


# ── C-04 regression: build_pastors_section_props fully sede-scoped ────────


class TestPastorsSectionSedeScope:
    """C-04 fix regression: ``build_pastors_section_props`` must only
    return pastoral leaders of the site's sede, never a cross-sede dump.
    """

    def test_build_with_sede_id_filters_pastors_to_that_sede(self, db_session):
        from backend.crud.cms_pastors_sync import build_pastors_section_props

        sede_a = uuid.uuid4()
        sede_b = uuid.uuid4()
        _make_persona(
            db_session, "Pastor", "A", sede_id=sede_a, is_pastoral_leader=True
        )
        _make_persona(
            db_session, "Pastor", "B", sede_id=sede_b, is_pastoral_leader=True
        )

        result = build_pastors_section_props(db_session, sede_id=sede_a)
        pastors = result["pastors"]
        assert len(pastors) == 1
        assert "Pastor A" == pastors[0]["name"]

    def test_build_with_none_sede_returns_empty(self, db_session):
        # Orphan site (no sede_id) operated by an admin must NOT leak
        # every pastor of every sede — returns an empty team instead.
        from backend.crud.cms_pastors_sync import build_pastors_section_props

        _make_persona(
            db_session,
            "Pastor",
            "Leaked",
            sede_id=uuid.uuid4(),
            is_pastoral_leader=True,
        )

        result = build_pastors_section_props(db_session, sede_id=None)
        assert result == {"pastors": []}

    def test_build_excludes_non_leader_pastors_of_same_sede(self, db_session):
        from backend.crud.cms_pastors_sync import build_pastors_section_props

        sede = uuid.uuid4()
        _make_persona(
            db_session, "Leader", "X", sede_id=sede, is_pastoral_leader=True
        )
        _make_persona(
            db_session, "Member", "Y", sede_id=sede, is_pastoral_leader=False
        )

        result = build_pastors_section_props(db_session, sede_id=sede)
        pastors = result["pastors"]
        assert len(pastors) == 1
        assert pastors[0]["name"] == "Leader X"

