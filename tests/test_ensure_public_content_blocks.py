"""Unit tests for the canonical public-content blocks catalog.

Guards ``scripts/ensure_public_content_blocks.BLOCKS`` — the single source of
truth for the CMS-managed ``PageContent`` blocks used by public pages (and the
object lazily re-exported by ``scripts/seed_public_content``):

* The canonical catalog has EXACTLY 25 keys — a frozen contract. Adding a new
  block is a deliberate act: the key must be added to ``CANONICAL_KEYS`` here
  too.
* Every block is a ``{title, content}`` payload: a non-empty string title and a
  ``content`` value that is either a dict or a list.
* ``content`` is always JSON-serializable — ``main()`` persists it with
  ``json.dumps(payload["content"], ensure_ascii=False)``, so anything
  non-serializable would explode at seed time rather than here.
* High-traffic blocks keep their structural invariants (pastors team with
  Martina Herrera, full nav menu, privacy sections, locations list).
* ``MERGE_BLOCKS`` keys are a subset of ``BLOCKS`` keys — ``main()`` overlays
  merge content onto an existing row; a key missing from ``BLOCKS`` would
  silently create a partial block.

These are pure-data tests: no DB fixture needed.
"""

from __future__ import annotations

import json

from scripts.ensure_public_content_blocks import BLOCKS, MERGE_BLOCKS

# ── Frozen canonical contract ────────────────────────────────────────────
# Exactly 25 blocks. If a new block is added, update this set deliberately.
CANONICAL_KEYS = frozenset(
    {
        "ccf_events_feed",
        "ccf_sermons_feed",
        "ccf_testimonials_hero",
        "ccf_testimonials_feed",
        "ccf_boletin_hero",
        "ccf_pastores_index",
        "ccf_pastores_feed",
        "ccf_courses_feed",
        "ccf_discover_feed",
        "ccf_home_feed",
        "ccf_footer",
        "ccf_mobile_nav",
        "ccf_welcome",
        "ccf_privacy",
        "ccf_home_hero",
        "ccf_about_hero",
        "ccf_about_feed",
        "ccf_pastores_hero",
        "ccf_events_hero",
        "ccf_sermons_hero",
        "ccf_discover_hero",
        "ccf_courses_hero",
        "ccf_locations_hero",
        "ccf_locations_feed",
        "ccf_nav_items",
        "ccf_home_discover_cta",  # Bloque CTA "Conocer a Jesús" en la home — agregado 2026-09-03
    }
)


# The only block whose ``content`` is a list instead of a dict.
CONTENT_IS_LIST = frozenset({"ccf_locations_feed"})


class TestCanonicalCatalogKeys:
    def test_exactly_25_keys(self):
        """El catálogo tiene ahora 26 claves — ccf_home_discover_cta fue agregado deliberadamente 2026-09-03."""
        assert len(BLOCKS) == 26
        assert set(BLOCKS) == CANONICAL_KEYS

    def test_all_keys_use_ccf_prefix(self):
        """Every key follows the ``ccf_<page>_<slot>`` naming convention."""
        assert all(key.startswith("ccf_") for key in BLOCKS)

    def test_keys_are_unique_and_stable_strings(self):
        """Keys are plain strings (stable DB ``page_key`` values)."""
        for key in BLOCKS:
            assert isinstance(key, str) and key


class TestBlockShape:
    def test_every_block_is_title_plus_content(self):
        """No extra top-level keys; title is a non-empty string."""
        for key, payload in BLOCKS.items():
            assert set(payload) == {"title", "content"}, key
            assert isinstance(payload["title"], str) and payload["title"].strip(), key

    def test_content_is_dict_or_list(self):
        """dict for all blocks except the locations feed (list of sedes)."""
        for key, payload in BLOCKS.items():
            content = payload["content"]
            if key in CONTENT_IS_LIST:
                assert isinstance(content, list), key
            else:
                assert isinstance(content, dict), key

    def test_content_is_json_serializable(self):
        """``main()`` persists content via ``json.dumps(..., ensure_ascii=False)``."""
        for key, payload in BLOCKS.items():
            json.dumps(payload["content"], ensure_ascii=False)  # raises if not serializable

    def test_payload_round_trips_through_json(self):
        """Full payload survives a JSON round-trip unchanged."""
        for key, payload in BLOCKS.items():
            clone = json.loads(json.dumps(payload, ensure_ascii=False))
            assert clone == payload, key

    def test_no_empty_content_dicts(self):
        """Every dict-content block actually carries configuration."""
        for key, payload in BLOCKS.items():
            content = payload["content"]
            if isinstance(content, dict):
                assert content, key


class TestKeyStructuralInvariants:
    def test_pastores_feed_has_full_team_with_martina(self):
        """The pastors grid is the canonical 10-member team incl. Martina Herrera."""
        content = BLOCKS["ccf_pastores_feed"]["content"]
        pastors = content["pastors"]
        assert isinstance(pastors, list)
        assert len(pastors) == 10

        slugs = [p["slug"] for p in pastors]
        assert len(slugs) == len(set(slugs)), "pastor slugs must be unique"

        martina = next((p for p in pastors if p["slug"] == "martina-herrera"), None)
        assert martina is not None, "Martina Herrera must be in the canonical team"
        assert martina["name"] == "Martina Herrera"
        assert martina.get("isMain") is True

        # Every pastor entry carries the full card contract.
        for pastor in pastors:
            for field in ("slug", "name", "role", "image", "story"):
                assert pastor.get(field), (field, pastor.get("slug"))

    def test_nav_items_is_the_full_public_menu(self):
        """Top nav exposes all 8 public routes with label + href."""
        items = BLOCKS["ccf_nav_items"]["content"]["items"]
        assert isinstance(items, list)
        assert len(items) == 8
        for item in items:
            assert {"label", "href"} <= set(item), item
        hrefs = [item["href"] for item in items]
        assert len(hrefs) == len(set(hrefs)), "nav hrefs must be unique"

    def test_privacy_has_13_numbered_sections(self):
        """Privacy policy keeps 13 sections with unique anchors 1..13."""
        sections = BLOCKS["ccf_privacy"]["content"]["sections"]
        assert len(sections) == 13
        ids = [s["id"] for s in sections]
        assert len(ids) == len(set(ids)), "section anchors must be unique"
        for index, section in enumerate(sections, start=1):
            assert section["title"].startswith(f"{index}."), section

    def test_locations_feed_is_a_list_of_sedes(self):
        """Sedes list has exactly 3 entries with one main sede."""
        sedes = BLOCKS["ccf_locations_feed"]["content"]
        assert isinstance(sedes, list)
        assert len(sedes) == 3
        mains = [sede for sede in sedes if sede.get("isMain") is True]
        assert len(mains) == 1, "exactly one main sede expected"
        for sede in sedes:
            assert {"name", "address", "phone", "schedule"} <= set(sede), sede

    def test_about_feed_has_six_valores(self):
        """About section keeps the 6 core values numbered 01..06."""
        valores = BLOCKS["ccf_about_feed"]["content"]["valores"]
        assert isinstance(valores, list)
        assert len(valores) == 6
        assert {v["num"] for v in valores} == {"01", "02", "03", "04", "05", "06"}
        for valor in valores:
            assert {"num", "key", "title", "desc"} <= set(valor), valor


class TestMergeBlocks:
    def test_merge_keys_are_subset_of_canonical(self):
        """Merge overlays an existing block; never introduces a partial one."""
        assert set(MERGE_BLOCKS) <= set(BLOCKS)

    def test_merge_blocks_share_canonical_shape(self):
        """Merge payloads follow the same ``{title, content}`` shape."""
        for key, payload in MERGE_BLOCKS.items():
            assert set(payload) == {"title", "content"}, key
            assert isinstance(payload["title"], str) and payload["title"].strip(), key
            json.dumps(payload["content"], ensure_ascii=False)  # must be persistable
