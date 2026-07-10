"""Regression tests for the public /pastores page pastor→photo consistency.

Bug context (2026-07-07)
------------------------
Earlier the public /pastores page displayed wrong photos for some pastors.
Two root causes had to coexist for the bug to surface:

1. ``StorageService.save_file`` generates random UUID hashes — no
   deterministic mapping between "this is Luis Ricardo's photo" and the
   on-disk filename.
2. Hash-named ``.webp`` files referenced by the seed scripts were never
   re-synced to actual photo bytes, while a parallel set of manually-uploaded
   slug-named ``.jpg`` files were never registered in ``CmsMediaItem``.

These tests verify the post-fix invariants against the public read path the
real frontend hits, so any future regression that re-introduces the
mismatch (e.g. someone overwrites ``pastor['image']`` with a stale URL)
trips exactly one of these assertions.

Strategy
--------
The tests do **not** assume a seeded live DB. They build the canonical
feed rows (CmsSite + CmsPage + CmsPageVersion + CmsSection + CmsMediaItem)
inside a synthetic ``seed_pastors_page`` fixture, then hit the **public**
endpoints the frontend actually consumes:

  * ``GET /api/cms/v2/public/sites/ccf/pastoral-team`` — the structured feed
    consumed by the ``/pastores`` page (Next.js renders the cards from this).
  * ``GET /api/cms/v2/public/sites/ccf/pages/pastors`` — the CMS-rendered
    page whose ``sections[N].props_json.pastors`` carries the same feed.

Both endpoints must agree on the photo URLs, and each URL must:

1. Resolve to a row in ``CmsMediaItem`` whose ``url`` matches.
2. Have an ``alt_text`` (or ``filename`` or any ``tags`` entry) whose
   slugified token set intersects ``{slug tokens of pastor['slug']}`` —
   this is the regression guard against the "image url swapped to an
   unrelated photo" vector.
"""

from __future__ import annotations

import re
import unicodedata
import uuid
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import seed_admin  # noqa: F401  — re-export for ergonomics

# ── Test-local helpers ─────────────────────────────────────────────────────


def _slugify(value: str | None) -> str:
    """Slug that survives diacritics (NFKD + ASCII ignore).

    Mirrors the canonical rule used by ``ccf/scripts/fix_pastor_photos.py``
    and ``backend/crud/cms_pastors_sync.py``. Keeping the same rule in the
    regression test means the slug-tokens we generate will match what the
    production feed uses — no false negatives.
    """
    value = (value or "").strip().lower()
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def _slug_token_set(value: str | None) -> set[str]:
    """Return the set of non-empty slug tokens for a name.

    Multi-word names (`Alex y Elvia`, `Fernando y Mónica`) become multi-token
    sets. ``y`` / ``e`` / ``de`` / ``del`` / ``la`` are filtered out because
    both ``_slugify`` and ``cms_pastors_sync._find_persona_by_name`` drop
    them; reusing the same filter keeps the regression test aligned.
    """
    tokens = {
        tok for tok in _slugify(value).split("-")
        if tok and tok not in {"y", "e", "de", "del", "la"}
    }
    return tokens


def _media_matches_pastor(
    pastor_slug: str,
    pastor_name: str,
    *,
    media_alt_text: str | None,
    media_filename: str | None,
    media_tags: list[str] | None,
) -> bool:
    """Decide whether a ``CmsMediaItem`` row encodes the pastor's identity.

    We accept the union of alt_text / filename / tags — the contract for
    fix scripts is to put the slug or full name into any of those
    fields. Token-set intersection rather than equality is used to
    tolerate plural / accent / second-name variants.
    """
    target_tokens = _slug_token_set(pastor_slug) or _slug_token_set(pastor_name)
    if not target_tokens:
        return False
    haystack: set[str] = set()
    haystack |= _slug_token_set(media_alt_text or "")
    haystack |= _slug_token_set((media_filename or "").rsplit(".", 1)[0])
    for tag in media_tags or []:
        haystack |= _slug_token_set(tag)
    if not haystack:
        return False
    # Intersect; require every token to have at least one match.
    return target_tokens.issubset(haystack)


# ── Fixtures ───────────────────────────────────────────────────────────────


SITE_KEY = "ccf"
PASTORS_PAGE_SLUG = "pastors"


PASTORS_SEED: list[dict[str, str]] = [
    {
        "slug": "luis-ricardo-meza",
        # Truncated from "Luis Ricardo Meza Gutiérrez" so the
        # slugified persona nombre_completo matches the canonical
        # "luis-ricardo-meza" slug (not the full 4-token form).
        # The persona's first_name is still "Luis" and last_name
        # "Ricardo Meza", preserving the public-feed display name.
        "name": "Luis Ricardo Meza",
        "filename": "luis-ricardo-meza.jpg",
        "alt_text": "Luis Ricardo Meza",
        "tags": ["fix", "pastor", "luis-ricardo-meza"],
    },
    {
        "slug": "histar-ariza",
        # Truncated from "Histar Ariza Herrera" so the slugified
        # persona nombre_completo matches the canonical
        # "histar-ariza" slug (not the full 3-token form).
        "name": "Histar Ariza",
        "filename": "histar-ariza.jpg",
        "alt_text": "Histar Ariza",
        "tags": ["fix", "pastor", "histar-ariza"],
    },
    {
        "slug": "alex-y-elvia",
        "name": "Alex y Elvia",
        "filename": "alex-y-elvia.jpg",
        "alt_text": "Alex y Elvia",
        "tags": ["fix", "pastor", "alex-y-elvia"],
    },
    {
        "slug": "camilo-pajaro",
        "name": "Camilo Pájaro",
        "filename": "camilo-pajaro.jpg",
        "alt_text": "Camilo Pájaro",
        "tags": ["fix", "pastor", "camilo-pajaro"],
    },
    {
        "slug": "fernando-y-monica",
        "name": "Fernando y Mónica",
        "filename": "fernando-y-monica.jpg",
        "alt_text": "Fernando y Mónica",
        "tags": ["fix", "pastor", "fernando-y-monica"],
    },
    {
        "slug": "nehemias-morales",
        "name": "Nehemías Morales",
        "filename": "nehemias-morales.jpg",
        "alt_text": "Nehemías Morales",
        "tags": ["fix", "pastor", "nehemias-morales"],
    },
    {
        "slug": "martina-herrera",
        "name": "Martina Herrera",
        "filename": "martina-herrera.jpg",
        "alt_text": "Martina Herrera",
        "tags": ["fix", "pastor", "martina-herrera"],
    },
    {
        "slug": "yair-macea",
        "name": "Yair Macea",
        "filename": "yair-macea.jpg",
        "alt_text": "Yair Macea",
        "tags": ["fix", "pastor", "yair-macea"],
    },
    {
        "slug": "yanedith-wilches",
        "name": "Yanedith Wilches",
        "filename": "yanedith-wilches.jpg",
        "alt_text": "Yanedith Wilches",
        "tags": ["fix", "pastor", "yanedith-wilches"],
    },
]


@pytest.fixture
def seed_pastors_page(db_session):  # noqa: F811  — see conftest fixture
    """Wire up the canonical post-fix DB state for /pastors.

    The fixture registers the pastors page as ``published`` with a single
    ``CmsPageVersion`` snapshot containing the full ``pastors`` section
    payload (slug + name + image_url per pastor). It also creates one
    ``CmsMediaItem`` per pastor with matching alt_text / filename / tags.

    Returns a dict so tests can introspect the synthesized rows directly
    when they need to drive negative tests (mutation → assert failure).

    Note on ``is_main_pastor``
    -------------------------
    The ``is_main_pastor`` flag is asserted via the literal slug
    ``"luis-ricardo-meza"`` (single source of truth, see the
    ``is_main_pastor`` local below). This mirrors the production
    pastoral team where Luis Ricardo Meza is the canonical pastor
    principal — there is no notion of a co-pastor in ``PASTORS_SEED``.
    If a future slug enters the feed as a co-principal pastor, this
    branch must be expanded (likely to a set literal
    ``{MAIN_PASTOR_SLUG, ...}``) so that church_role and is_main_pastor
    stay aligned for both Persona and the section payload.
    """
    from backend import models  # local import: pytest's conftest already loaded modules

    _user, _persona, sede = seed_admin(db_session)

    # 1. Site.
    site = (
        db_session.query(models.CmsSite)
        .filter(models.CmsSite.site_key == SITE_KEY)
        .first()
    )
    if site is None:
        site = models.CmsSite(
            site_key=SITE_KEY,
            name="CCF Test",
            base_path="/",
            is_active=True,
            sede_id=sede.id,
        )
        db_session.add(site)
        db_session.flush()
    elif site.sede_id is None:
        site.sede_id = sede.id

    # 2. Registered media rows (one per pastor). The image URL here is the
    #    the same value that ``build_pastors_section_props`` derives from
    #    ``persona.photo_url`` after a ``fix_pastor_photos.py`` pass — the
    #    randomized UUID-based ``/api/static/cms/pastores/<hex>.webp`` URL.
    media_rows: dict[str, models.CmsMediaItem] = {}
    for entry in PASTORS_SEED:
        media_uuid = uuid.uuid4().hex
        media_url = f"/api/static/cms/pastores/{media_uuid}.webp"
        media = models.CmsMediaItem(
            url=media_url,
            alt_text=entry["alt_text"],
            filename=entry["filename"],
            mime_type="image/webp",
            file_size=102400,
            section="pastores",
            tags=entry["tags"],
            status="active",
            dimensions="1024x1024",
            sede_id=sede.id,
            created_by_persona_id=_persona.id,
        )
        db_session.add(media)
        db_session.flush()
        media_rows[entry["slug"]] = media

    # 3. The /pastors page in published state.
    page = (
        db_session.query(models.CmsPage)
        .filter(models.CmsPage.site_id == site.id, models.CmsPage.slug == PASTORS_PAGE_SLUG)
        .first()
    )
    if page is None:
        page = models.CmsPage(
            site_id=site.id,
            slug=PASTORS_PAGE_SLUG,
            title="Pastores",
            status="draft",
            seo_json={},
        )
        db_session.add(page)
        db_session.flush()
    page.status = "published"

    # 4. Pastors section with the live feed payload.
    pastors_payload = [
        {
            "slug": entry["slug"],
            "name": entry["name"],
            "role": "Pastor Principal" if entry["slug"] == "luis-ricardo-meza" else "Pastor",
            "image": media_rows[entry["slug"]].url,
            "isMain": entry["slug"] == "luis-ricardo-meza",
            "story": "",
            "bio_short": "",
            "bio_full": "",
        }
        for entry in PASTORS_SEED
    ]
    section = (
        db_session.query(models.CmsSection)
        .filter(
            models.CmsSection.page_id == page.id,
            models.CmsSection.section_key == "pastors",
        )
        .first()
    )
    if section is None:
        section = models.CmsSection(
            page_id=page.id,
            section_key="pastors",
            type="feed",
            props_json={"pastors": pastors_payload},
            sort_order=2,
            is_visible=True,
            status="active",
        )
        db_session.add(section)
        db_session.flush()
    else:
        section.props_json = {"pastors": pastors_payload}
        db_session.flush()

    # 5. Pastores are also mirrored as ``Persona`` records with the photo URL
    #    set (= what ``fix_pastor_photos.py`` produces). Without this, the
    #    ``/pastoral-team`` public endpoint would not have anyone to render.
    for entry, media in zip(PASTORS_SEED, [media_rows[e["slug"]] for e in PASTORS_SEED]):
        # Look up an existing pastoral Persona by exact first_name + last_name
        # pair. ``Persona.last_name`` is NOT nullable in the schema, so the
        # ``or None`` fallback from the original fixture was incorrect: Python
        # evaluated ``"" or None`` → ``None`` BEFORE SQLAlchemy ever saw it,
        # generating ``last_name IS NULL`` and breaking persona re-runs. The
        # raw empty-string comparison is safer; on a fresh test DB no match
        # will be returned for an empty last_name (column is non-null).
        first_token, *rest_tokens = entry["name"].split()
        last_token = " ".join(rest_tokens) if rest_tokens else ""
        # Single source of truth for "is this slug the canonical pastor
        # principal?". Computed once per iteration so church_role and
        # is_main_pastor always agree — see docstring above for why this
        # is hard-coded to ``"luis-ricardo-meza"`` rather than a fixture
        # parameter.
        is_main_pastor = entry["slug"] == "luis-ricardo-meza"
        persona = (
            db_session.query(models.Persona)
            .filter(models.Persona.first_name == first_token)
            .filter(models.Persona.last_name == last_token)
            .first()
        )
        if persona is None:
            persona = models.Persona(
                first_name=first_token,
                last_name=last_token,
                # Match the prod contract rather than echoing the display
                # name through ``church_role`` — the public
                # ``_pastoral_role`` precedence on ``Persona.church_role``
                # means a non-canonical role leaked into the response would
                # show up verbatim (``"Alex y Elvia"``) for every non-main
                # pastor in the pastoral-team feed.
                church_role=("Pastor Principal" if is_main_pastor else "Pastor"),
                estado_vital="ACTIVO",
                is_pastoral_leader=True,
                is_main_pastor=is_main_pastor,
                photo_url=media.url,
                # NOTE: ``nombre_completo`` is a ``@hybrid_property`` on
                # Persona (no setter) — it's computed from first_name +
                # last_name. Passing it as a kwarg raises ``AttributeError:
                # can't set attribute``. Assigning the columns above is
                # enough; the getter exposes the joined name on the live
                # object and the public endpoint depends on it.
                sede_id=sede.id,
            )
            db_session.add(persona)
        else:
            persona.is_pastoral_leader = True
            persona.is_main_pastor = persona.is_main_pastor or is_main_pastor
            persona.photo_url = media.url

    # 6. Published version snapshot used by the public page endpoint.
    snapshot = {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": "published",
            "seo_json": page.seo_json or {},
        },
        "sections": [
            {
                "id": str(section.id),
                "section_key": section.section_key,
                "type": section.type,
                "props_json": section.props_json or {},
                "sort_order": section.sort_order,
                "is_visible": section.is_visible,
                "status": section.status or "active",
            }
        ],
    }
    existing_version = (
        db_session.query(models.CmsPageVersion)
        .filter(models.CmsPageVersion.page_id == page.id)
        .order_by(models.CmsPageVersion.version_number.desc())
        .first()
    )
    next_version_number = (existing_version.version_number + 1) if existing_version else 1
    version = models.CmsPageVersion(
        page_id=page.id,
        version_number=int(next_version_number),
        snapshot_json=snapshot,
        notes="Regression test seed for /pastors",
        created_by_persona_id=_persona.id,
    )
    db_session.add(version)
    db_session.flush()
    page.published_version_id = version.id

    db_session.commit()

    return {
        "site": site,
        "page": page,
        "section": section,
        "version": version,
        "media": media_rows,
        "sede": sede,
    }


# ── Tests ──────────────────────────────────────────────────────────────────


PUBLIC_BASE = "/api/cms/v2/public/sites"


def _public_pastoral_team(client, site_key: str = SITE_KEY) -> list[dict[str, Any]]:
    resp = client.get(f"{PUBLIC_BASE}/{site_key}/pastoral-team")
    assert resp.status_code == 200, (
        f"public pastoral-team 200 expected, got {resp.status_code}: {resp.text}"
    )
    return resp.json()


def _public_page_pastors(client, site_key: str = SITE_KEY) -> dict[str, Any]:
    resp = client.get(f"{PUBLIC_BASE}/{site_key}/pages/{PASTORS_PAGE_SLUG}")
    assert resp.status_code == 200, (
        f"public pastors page 200 expected, got {resp.status_code}: {resp.text}"
    )
    return resp.json()


class TestPastorPhotoRegression:
    """Every regression dimension the post-fix pipeline must keep stable.

    Each test below corresponds to one invariant the production feed has to
    satisfy. They run independently so a future PR that breaks one invariant
    (e.g. swaps the alt_text policy) trips the precise test, not a generic
    pass/fail cumulativo.
    """

    # ── I. Helpers compile cleanly (sanity check on rules) ────────────────

    def test_slugify_helpers_handle_accents(self):
        # Pretend someone shaped a pastor with accents + connectors + hyphens.
        assert _slugify("Nehemías Morales") == "nehemias-morales"
        assert _slugify("Fernando y Mónica") == "fernando-y-monica"
        assert _slugify("Luis Ricardo Meza Gutiérrez") == "luis-ricardo-meza-gutierrez"
        assert _slugify("  Alex   y   Elvia  ") == "alex-y-elvia"
        # ``y`` is filtered as a connector — pair-names collapse to their
        # nouns only, matching the canonical rule used in
        # ``cms_pastors_sync._find_persona_by_name``.
        assert _slug_token_set("Alex y Elvia") == {"alex", "elvia"}
        assert _slug_token_set("Yair Macea") == {"yair", "macea"}

    # ── II. Pastoral team endpoint has every seeded pastor ───────────────

    def test_public_pastoral_team_lists_all_seeded_pastors(
        self, client, seed_pastors_page
    ):
        payload = _public_pastoral_team(client)
        slugs_returned = {row["slug"] for row in payload}
        slugs_expected = {entry["slug"] for entry in PASTORS_SEED}
        missing = slugs_expected - slugs_returned
        assert not missing, f"pastoral-team missing pastors: {sorted(missing)}"

    # ── III. Every pastor has a non-empty image URL ──────────────────────

    @pytest.mark.parametrize("pastor_slug", [entry["slug"] for entry in PASTORS_SEED])
    def test_pastor_image_url_is_non_empty(self, client, seed_pastors_page, pastor_slug):
        payload = _public_pastoral_team(client)
        row = next((r for r in payload if r["slug"] == pastor_slug), None)
        assert row is not None, f"{pastor_slug} missing from pastoral-team"
        assert (row.get("photo_url") or "").strip(), (
            f"{pastor_slug} has empty photo_url — feed regression"
        )

    # ── IV. Image URL resolves to a registered CmsMediaItem ──────────────

    @pytest.mark.parametrize("pastor_slug", [entry["slug"] for entry in PASTORS_SEED])
    def test_pastor_image_url_resolves_to_cms_media_item(
        self, client, db_session, seed_pastors_page, pastor_slug
    ):
        from backend import models

        payload = _public_pastoral_team(client)
        row = next(r for r in payload if r["slug"] == pastor_slug)
        image_url = (row.get("photo_url") or "").strip()
        assert image_url, f"{pastor_slug}: empty photo_url"

        media = (
            db_session.query(models.CmsMediaItem)
            .filter(models.CmsMediaItem.url == image_url)
            .first()
        )
        assert media is not None, (
            f"{pastor_slug}: photo_url {image_url!r} has no CmsMediaItem row — "
            f"this is the original 'wrong photo' bug pattern"
        )
        assert (media.status or "").lower() != "archived", (
            f"{pastor_slug}: media archived but still wired into the public feed"
        )

    # ── V. The CmsMediaItem encodes the pastor's identity (THE GUARD) ────

    @pytest.mark.parametrize("pastor_slug", [entry["slug"] for entry in PASTORS_SEED])
    def test_pastor_media_item_encodes_pastor_identity(
        self, client, db_session, seed_pastors_page, pastor_slug
    ):
        from backend import models

        payload = _public_pastoral_team(client)
        row = next(r for r in payload if r["slug"] == pastor_slug)
        image_url = (row.get("photo_url") or "").strip()
        media = (
            db_session.query(models.CmsMediaItem)
            .filter(models.CmsMediaItem.url == image_url)
            .one()
        )

        # The pastor's "logical" name from the feed is the canonical ground
        # truth; the slug is the projection of the name and we tolerate
        # either as the matcher input.
        ok = _media_matches_pastor(
            pastor_slug=row["slug"],
            pastor_name=row["name"],
            media_alt_text=media.alt_text,
            media_filename=media.filename,
            media_tags=list(media.tags or []),
        )
        assert ok, (
            f"{pastor_slug} (name={row['name']!r}) → "
            f"CmsMediaItem(id={media.id}) has alt_text={media.alt_text!r}, "
            f"filename={media.filename!r}, tags={list(media.tags or [])}; "
            f"the media item no longer encodes the pastor's identity — "
            f"the slug ↔ photo mismatch bug is regressing"
        )

    # ── VI. Section → media consistency (CMS-rendered page path) ────────

    def test_pastors_page_section_matches_pastoral_team(
        self, client, seed_pastors_page
    ):
        """The two public endpoints must agree.

        ``/pastoral-team`` is what the Next.js cards consume; the
        ``/pages/pastors`` snapshot is what the SEO/render uses. They
        compute ``pastors[i].image`` from different code paths, so a
        divergence is a regression smell (e.g. one staging seeded and
        the other was never re-published).
        """
        team_slugs_to_images = {
            row["slug"]: (row.get("photo_url") or "").strip()
            for row in _public_pastoral_team(client)
        }
        page_data = _public_page_pastors(client)
        section_pastors: list[dict[str, Any]] = []
        for section in page_data.get("sections") or []:
            props = section.get("props_json") or {}
            if isinstance(props, dict) and isinstance(props.get("pastors"), list):
                section_pastors.extend(props["pastors"])

        page_slug_to_image = {
            row["slug"]: (row.get("image") or "").strip() for row in section_pastors
        }

        # 1. Same set of slugs.
        assert page_slug_to_image.keys() == team_slugs_to_images.keys(), (
            f"section slug set ({sorted(page_slug_to_image)}) diverges from "
            f"pastoral-team slug set ({sorted(team_slugs_to_images)})"
        )

        # 2. Same image URL for every shared slug.
        for slug in sorted(page_slug_to_image):
            assert page_slug_to_image[slug] == team_slugs_to_images[slug], (
                f"{slug}: section image {page_slug_to_image[slug]!r} != "
                f"pastoral-team image {team_slugs_to_images[slug]!r}"
            )

    # ── VII. Negative test — alt-text swap fails the regression ──────────

    def test_alt_text_swap_is_detected_as_regression(
        self, client, db_session, seed_pastors_page
    ):
        """Mutate the CmsMediaItem.alt_text to a non-matching phrase and
        assert the regression trip-wire fires. This is the parametric
        danger case: someone overwrites a media row's alt_text without
        re-publishing, leaving an image url that points to the right file
        but is mis-described."""
        from backend import models

        entry = PASTORS_SEED[0]  # Luis Ricardo Meza
        response_slugs = {row["slug"] for row in _public_pastoral_team(client)}
        assert entry["slug"] in response_slugs, "fixture sanity: anchor row missing"

        media = db_session.query(models.CmsMediaItem).filter(
            models.CmsMediaItem.url.endswith(".webp"),
            models.CmsMediaItem.filename == entry["filename"],
        ).one()
        media.alt_text = "Foto no relacionada — error humano intencional"
        media.filename = "unrelated-archive-shot.webp"
        media.tags = ["archived"]  # drop the pastor-encoding tags too
        db_session.commit()

        # Re-hit the public endpoint and re-evaluate the matcher.
        payload = _public_pastoral_team(client)
        target = next(r for r in payload if r["slug"] == entry["slug"])
        media_row = (
            db_session.query(models.CmsMediaItem)
            .filter(models.CmsMediaItem.url == target["photo_url"])
            .one()
        )
        ok = _media_matches_pastor(
            pastor_slug=target["slug"],
            pastor_name=target["name"],
            media_alt_text=media_row.alt_text,
            media_filename=media_row.filename,
            media_tags=list(media_row.tags or []),
        )
        assert not ok, (
            "regression guard FAILED to detect a deliberate slug↔photo "
            "desync — _media_matches_pastor is too permissive"
        )

    # ── VIII. URL render alignment (drift-free final check) ──────────────

    @pytest.mark.parametrize("pastor_slug", [entry["slug"] for entry in PASTORS_SEED])
    def test_pastor_image_url_is_well_formed_for_static_serving(
        self, client, seed_pastors_page, pastor_slug
    ):
        """The image URL must be served from the assets static endpoint
        expected by the frontend (``/api/static/cms/pastores/...``).

        This catches accidental regressions like rewriting
        ``/api/static/cms/pastores/<uuid>.webp`` to a CDN URL whose path
        no longer matches ``StorageService.save_file``'s contract —
        which would silently break img tags without disturbing the DB.
        """
        payload = _public_pastoral_team(client)
        row = next(r for r in payload if r["slug"] == pastor_slug)
        image_url = (row.get("photo_url") or "").strip()
        assert image_url.startswith("/api/static/cms/pastores/"), (
            f"{pastor_slug}: photo_url {image_url!r} is not a stored pastors "
            f"asset URL — frontend img src would 404"
        )
        # Must end with a benign image extension (webp preferred, jpg/png tolerated).
        ext = Path(image_url).suffix.lower().lstrip(".")
        assert ext in {"webp", "jpg", "jpeg", "png"}, (
            f"{pastor_slug}: photo_url {image_url!r} has unexpected extension "
            f"{ext!r} — StorageService is supposed to optimize to webp"
        )


class TestPastorPhotoRegressionFast:
    """Slugs/alt-text/matcher — pure-Python assertions, no DB required.

    Kept here so ``pytest -k fast`` can regression-check the matcher logic
    without spinning up the SQLAlchemy session in CI environments that
    don't have a translated SQLite UUID column.
    """

    def test_matcher_accepts_well_formed_alt_text(self):
        assert _media_matches_pastor(
            pastor_slug="luis-ricardo-meza",
            pastor_name="Luis Ricardo Meza",
            media_alt_text="Luis Ricardo Meza",
            media_filename="luis-ricardo-meza.webp",
            media_tags=["pastor"],
        )

    def test_matcher_accepts_pertinent_tag_in_tags_list(self):
        assert _media_matches_pastor(
            pastor_slug="fernando-y-monica",
            pastor_name="Fernando y Mónica",
            media_alt_text=None,
            media_filename="fermon.webp",
            media_tags=["fernando-y-monica"],
        )

    def test_matcher_rejects_swapped_alt_text(self):
        assert not _media_matches_pastor(
            pastor_slug="luis-ricardo-meza",
            pastor_name="Luis Ricardo Meza",
            media_alt_text="Camilo Pájaro",
            media_filename="unrelated.webp",
            media_tags=["pastor"],
        )

    def test_matcher_rejects_empty_haystack(self):
        assert not _media_matches_pastor(
            pastor_slug="histar-ariza",
            pastor_name="Histar Ariza",
            media_alt_text="",
            media_filename="",
            media_tags=[],
        )

    def test_matcher_tolerates_diagonal_extensions(self):
        assert _media_matches_pastor(
            pastor_slug="camilo-pajaro",
            pastor_name="Camilo Pájaro",
            media_alt_text="Camilo Pájaro • Pastor",
            media_filename="camilo-pajaro-2026.webp",
            media_tags=["pastores"],
        )
