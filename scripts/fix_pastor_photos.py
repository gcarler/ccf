#!/usr/bin/env python3
"""fix_pastor_photos.py — One-shot script to reattach the correct pastor photos
to the public /pastores page in CMS v2.

WHY THIS EXISTS
═══════════════
A staff member manually uploaded the correct pastor photos to
``/uploads/cms/pastores/<slug>.jpg`` on 2026-07-02 as a partial fix for the
public pastors page showing the wrong photos. But those .jpg files were never
registered in ``CmsMediaItem`` (the only key the CMS uses to serve images),
so the public page continued showing the old (incorrect) hash-named .webp
files referenced by the legacy ``page_contents`` payloads.

This script completes the fix end-to-end:

  1. For each (slug, jpg_filename, display_substring) in FIX_MAP:
       a. Reads /uploads/cms/pastores/<slug>.jpg
       b. Pushes it through ``storage_service.save_file`` to receive a fresh,
          optimized .webp with cache-busting URL.
       c. Registers a new ``CmsMediaItem`` (Axioma 3 — ``sede_id`` derived
          server-side from the actor user; idempotent on duplicate URL).
       d. Updates the matching ``persona.photo_url`` (canonical source that
          ``cms_pastors_sync.update_pastors_section_from_profiles`` reads).

  2. Drives the publish workflow via the canonical function:
       ``crud.transition_cms_page_status(action='publish')``
     which (because ``page.slug == "pastors"``) automatically:
       - Re-syncs ``section.props_json.pastors[*].image`` from the freshly
         updated ``Persona.photo_url`` rows.
       - Creates a new ``CmsPageVersion`` snapshot.
       - Sets ``page.published_version_id`` + ``status='published'``.
       - Writes a ``CmsPublishLog`` audit entry with our note.

IDEMPOTENCY
═══════════
At pastor granularity: if ``persona.photo_url`` already equals the freshly
generated URL, that pastor is skipped (no CmsMediaItem duplicate, no
unnecessary re-publish). At workflow granularity: if all pastors are already
on the canonical URLs, the publish step is skipped entirely.

USAGE
═════
    # 1. Preview only (no DB writes):
    DRY_RUN=1 python scripts/fix_pastor_photos.py

    # 2. Apply to a single pastor (e.g. testing the workflow first):
    ONLY=luis-ricardo-meza python scripts/fix_pastor_photos.py

    # 3. Apply to all 9 pastors at once:
    python scripts/fix_pastor_photos.py

PREREQUISITES
═════════════
- The source photos must already be at /uploads/cms/pastores/<slug>.jpg on
  the server (the upload that triggered this fix script).
- Each target pastor must have a ``Persona`` row matching the display
  substring with ``is_pastoral_leader=True`` and ``estado_vital != 'FALLECIDO'``.
- An active admin user with sede is required (canonical email:
  gscarlosernesto@gmail.com, with fallback to any active+sede user).

WHAT IS NOT IN SCOPE
════════════════════
- ``alba-arias``: no manual ``alba-arias.jpg`` was uploaded. This script
  intentionally does not synthesize a photo for Alba. The team should
  upload one explicitly via the admin UI when ready.
- Cleanup of the now-orphan hash-named .webp files: deliberately NOT touched.
  The audit ``scripts/audit_public_media_cms.py`` flags orphans; cleanup is
  a separate one-shot script once you confirm the fix works in production.
- The legacy ``page_contents`` payloads (seed_public_content.py /
  ensure_public_content_blocks.py) are NOT modified; the public /pastores
  page reads from the v2 ``CmsSection``, so the legacy table is dead weight
  post-fix and can be addressed in a separate cleanup task.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ── Project bootstrap (matches the convention used by every other script in ccf/scripts/) ──
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


from backend import crud, models  # noqa: E402
from backend.core.database import Base, SessionLocal, engine  # noqa: E402
from backend.core.storage import storage_service  # noqa: E402

# Schema init for SQLite local dev is intentionally NOT run at import
# time — merely ``import``-ing this module (e.g., from tests or a REPL)
# must NOT materialize tables. See the SQLite guard inside ``main()``,
# which only fires immediately before the first DB session is opened.


SITE_KEY = "ccf"
PAGE_SLUG = "pastors"
UPLOAD_SUBDIR = "cms/pastores"
SOURCE_DIR = _PROJECT_ROOT / "uploads" / "cms" / "pastores"
CANONICAL_ADMIN_EMAIL = "gscarlosernesto@gmail.com"


import functools
import re
import unicodedata


# Slug → .jpg filename on disk. Add or remove entries here; keep them sorted.
# NOTE: 'alba-arias' is intentionally absent because no manual .jpg was
# uploaded — the fix scope is exactly the 9 photos staff already placed on
# disk. Add 'alba' to this list once staff uploads an alba-arias.jpg.
# Placeholders so tests can enumerate the empty map without syntax surprise.
FIX_MAP: list[tuple[str, str]] = [
    ("alex-y-elvia",      "alex-y-elvia.jpg"),
    ("camilo-pajaro",     "camilo-pajaro.jpg"),
    ("fernando-y-monica", "fernando-y-monica.jpg"),
    ("histar-ariza",      "histar-ariza.jpg"),
    ("luis-ricardo-meza", "luis-ricardo-meza.jpg"),
    ("martina-herrera",   "martina-herrera.jpg"),
    ("nehemias-morales",  "nehemias-morales.jpg"),
    ("yair-macea",        "yair-macea.jpg"),
    ("yanedith-wilches",  "yanedith-wilches.jpg"),
]


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


@functools.lru_cache(maxsize=None)
def _slugify(value: str | None) -> str:
    """Mirror of ``backend.crud.cms_pastors_sync._slugify`` — inlined here so
    we avoid pulling in the CRUD module at script-import time (which would
    try to open a DB session during import).

    IMPORTANT difference from a naive ``re.sub(r"[^a-z0-9\\-]", "", ...)``
    approach: this version normalizes accented characters to their ASCII
    base (``í`` → ``i``, ``á`` → ``a``, ``ó`` → ``o``, ``ü`` → ``u``,
    ``ñ`` is preserved per Spanish convention here since the project has
    no ``ñ`` in any pastor name). The naive regex strips the WHOLE
    codepoint entirely, which would turn ``ías`` into ``as`` and break
    matches for ``Nehemías Morales``, ``Camilo Pájaro`` and similar.
    """
    value = (value or "").strip().lower()
    # NFKD decomposition: 'í' → 'i' + combining acute U+0301;
    # then encode('ascii', 'ignore') drops the combining mark,
    # leaving 'i'. This preserves the alphabetic base character.
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[\s_]+", "-", value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-+", "-", value)
    return value.strip("-")


def find_pastoral_persona_by_slug(db, slug: str):
    """Resolve the pastoral leader ``Persona`` for a given canonical slug.

    Three-tier matching (mirrors ``backend.crud.cms_pastors_sync._find_persona_by_name``
    so the two lookups stay isomorphic; see that function for the full
    rationale of each tier). The key difference vs. that function: this
    variant only considers rows where ``is_pastoral_leader=True`` AND
    ``estado_vital != 'FALLECIDO'`` — the public-feed contract.

    1. **Exact slug match** — ``_slugify(persona.nombre_completo) == slug``.
       Strongest signal, used for the canonical case (accent-normalized
       via NFKD so ``Camilo Pajaro`` query matches ``Camilo Pájaro`` DB row).
    2. **First-token anchor + high token overlap** — the first slug-token
       of the query must EQUAL the first slug-token of the persona.
       Prevents ambiguous matches where a multi-word first name (e.g.
       ``"Ana Maria Martinez"``) would otherwise out-score the real
       ``"Maria Martinez"`` target. Score must be ≥ 2 (or full coverage
       for short slugs).
    3. **Pure token overlap fallback** — same ≥ 2 / full-coverage threshold
       without the anchor, so cultures where the public display name
       uses a middle name (e.g. CMS says ``camilo-pajaro`` but CRM has
       ``José Camilo Pájaro``) still resolve correctly.
    """
    target_tokens = [t for t in slug.split("-") if t]
    if not target_tokens:
        return None
    candidates = (
        db.query(models.Persona)
        .filter(
            models.Persona.is_pastoral_leader.is_(True),
            models.Persona.estado_vital != "FALLECIDO",
        )
        .all()
    )

    # Tier 1: Exact slug match.
    for p in candidates:
        if _slugify(p.nombre_completo or "") == slug:
            return p

    # Tier 2: First-token anchor + high token overlap.
    tier2 = None
    tier2_score = 0
    for p in candidates:
        persona_slugified = _slugify(p.nombre_completo or "")
        if not persona_slugified:
            continue
        persona_tokens = persona_slugified.split("-")
        # First-token anchor: query[0] must equal persona[0].
        if target_tokens[0] != persona_tokens[0]:
            continue
        persona_token_set = set(persona_tokens)
        score = sum(1 for t in target_tokens if t in persona_token_set)
        if score >= 2 or score == len(target_tokens):
            if score > tier2_score:
                tier2_score = score
                tier2 = p
    if tier2 is not None:
        return tier2

    # Tier 3 (fallback): pure token overlap with the same threshold.
    best = None
    best_score = 0
    for p in candidates:
        persona_slugified = _slugify(p.nombre_completo or "")
        if not persona_slugified:
            continue
        persona_token_set = set(persona_slugified.split("-"))
        score = sum(1 for t in target_tokens if t in persona_token_set)
        if score > best_score and (score >= 2 or score == len(target_tokens)):
            best_score = score
            best = p
    return best


def find_canonical_admin(db):
    """Resolve which admin ``Usuario`` will own the new ``CmsMediaItem`` rows.

    Axioma 3 — ``CmsMediaItem.sede_id`` is derived server-side by
    ``crud.create_cms_media_item`` from the actor's persona sede; picking a
    user without a sede is fine (superadmin path bypasses scope check) but
    for consistency we prefer the canonical seed admin email first.
    """
    user = (
        db.query(models.Usuario)
        .filter(models.Usuario.email == CANONICAL_ADMIN_EMAIL)
        .first()
    )
    if user is not None:
        return user
    return (
        db.query(models.Usuario)
        .filter(
            models.Usuario.is_active.is_(True),
            models.Usuario.sede_id.isnot(None),
        )
        .first()
    )


def find_pastoral_persona(db, display_substr: str):
    """Loose-match a pastoral ``Persona`` row by ILIKE on ``nombre_completo``.

    Filters to ``is_pastoral_leader=True`` AND ``estado_vital != 'FALLECIDO'``
    so the result is a current, active pastoral leader that should appear on
    the public /pastores page.
    """
    return (
        db.query(models.Persona)
        .filter(
            models.Persona.is_pastoral_leader.is_(True),
            models.Persona.estado_vital != "FALLECIDO",
            models.Persona.nombre_completo.ilike(f"%{display_substr}%"),
        )
        .first()
    )


def slug_to_alt_text(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").title()


def fix_one_pastor(db, slug: str, jpg_filename: str, admin, dry_run: bool):
    """Process a single pastor. Returns ``(mode: str, url: str | None)``.

    Mode values:
      - ``"skip"``       — source file missing OR no matching pastoral Persona
      - ``"same"``       — persona already on a previous run's CmsMediaItem
      - ``"dry"``        — dry-run, no filesystem/DB writes performed
      - ``"changed"``    — wrote new CmsMediaItem + updated persona.photo_url,
                            and ``url`` carries the new public URL.

    SAFETY (post-review hardening): ``storage_service.save_file`` is NOT
    called unless we are committed to writing a new CmsMediaItem. This
    prevents DRY_RUN and idempotent re-runs from generating orphan .webp
    files on disk with random UUID filenames (the original review caught
    this side-effect bug).
    """
    file_path = SOURCE_DIR / jpg_filename
    if not file_path.is_file():
        print(f"  [skip]   {slug}: source file missing at {file_path}")
        return ("skip", None)

    persona = find_pastoral_persona_by_slug(db, slug)
    if persona is None:
        print(
            f"  [skip]   {slug}: no pastoral Persona whose nombre_completo "
            f"matches slug tokens for '{slug}'"
        )
        return ("skip", None)

    current_url = (persona.photo_url or "").strip()
    if current_url:
        existing_media = (
            db.query(models.CmsMediaItem)
            .filter(models.CmsMediaItem.url == current_url)
            .first()
        )
        # Idempotency: if persona already points at a CmsMediaItem we
        # tagged with "fix" on a previous run, treat as already-done and
        # do NOT allocate another random-UUID .webp on disk.
        if existing_media is not None and "fix" in (existing_media.tags or []):
            print(
                f"  [same]   {slug}: persona={persona.id} "
                f"({persona.nombre_completo!r}) already on "
                f"media={existing_media.id} ({current_url})"
            )
            return ("same", current_url)

    if dry_run:
        # Strict mode: do NOT touch the filesystem; just report intent.
        print(
            f"  [dry]    {slug}: would upload {jpg_filename} and register "
            f"CmsMediaItem for persona={persona.id} "
            f"({persona.nombre_completo!r})"
        )
        print(f"           current photo_url: {current_url or '(none)'}")
        return ("dry", None)

    # Now we are committed to writing. Allocate the new optimized .webp.
    content = file_path.read_bytes()
    storage_path = storage_service.save_file(
        content, jpg_filename, subfolder=UPLOAD_SUBDIR
    )
    # ``storage_service.save_file`` returns ``/static/{subfolder}/{name}`` \u2014
    # the path WITHIN the static mount. The app mounts StaticFiles at
    # ``/api/static`` (see backend/app.py: ``app.mount("/api/static", ...)``),
    # so the public URL is the mount path + the storage path's tail. A naive
    # ``f"/api/static{storage_path}"`` would produce
    # ``/api/static/static/cms/pastores/<uuid>.webp`` (DOUBLE static) and
    # the live endpoint would 500 on the wrong URL. Strip the leading
    # ``/static/`` so the public URL is canonical.
    if storage_path.startswith("/static/"):
        relative = storage_path[len("/static/"):]
    else:
        relative = storage_path.lstrip("/")
    new_public_url = f"/api/static/{relative}"

    # CmsMediaItem.url is unique per row. storage_service generates random
    # UUIDs so collisions are statistically zero, but guard anyway.
    existing = (
        db.query(models.CmsMediaItem)
        .filter(models.CmsMediaItem.url == new_public_url)
        .first()
    )
    if existing is None:
        crud.create_cms_media_item(
            db,
            url=new_public_url,
            alt_text=slug_to_alt_text(slug),
            section="pastores",
            tags=["public-site", "fix", slug],
            created_by=admin.id,
            filename=Path(jpg_filename).name,
            mime_type="image/jpeg",
            file_size=len(content),
            actor_user_id=admin.id,
        )
        print(f"  [media+] {slug}: CmsMediaItem registered {new_public_url}")
    else:
        print(f"  [media~] {slug}: reused existing CmsMediaItem {existing.id}")

    persona.photo_url = new_public_url
    print(
        f"  [pers ] {slug}: persona={persona.id} ({persona.nombre_completo!r}) "
        f"photo_url updated"
    )
    return ("changed", new_public_url)


# ────────────────────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reattach staff-uploaded pastor photos to the public /pastores CMS v2 page."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.environ.get("DRY_RUN", "0") == "1",
        help="Print what would happen without writing. Defaults to env DRY_RUN=1.",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=os.environ.get("ONLY", ""),
        help="Comma-separated slugs to process (others are skipped). Defaults to env ONLY.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dry_run = args.dry_run
    only_slugs: set[str] = set()
    if args.only:
        only_slugs = {s.strip() for s in args.only.split(",") if s.strip()}

    # Local-dev convenience (mirrors ``audit_pastor_media_orphans.py``):
    # when the script points at a fresh ``sqlite:///`` path, materialize
    # the schema immediately so the ``crud.get_cms_site_by_key(...)``
    # call below doesn't crash with ``no such table: cms_sites``.
    # Production (PostgreSQL) bypasses this guard entirely — Alembic
    # remains the sole schema owner for prod. If a non-trivial Postgres
    # DB is targeted, the operator must run ``alembic upgrade head``
    # instead; this guard is intentionally local-only.
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)

    print("=" * 78)
    print("fix_pastor_photos.py")
    print(f"  DRY_RUN   = {dry_run}")
    print(f"  ONLY      = {sorted(only_slugs) if only_slugs else '(all FIX_MAP slugs)'}")
    print(f"  SITE_KEY  = {SITE_KEY}")
    print(f"  PAGE_SLUG = {PAGE_SLUG}")
    print(f"  SOURCE    = {SOURCE_DIR}")
    print("=" * 78)
    print()

    if not SOURCE_DIR.is_dir():
        raise SystemExit(f"ERROR: source dir {SOURCE_DIR} does not exist")

    affected: list[tuple[str, str]] = []  # (slug, new_url) actually changed

    with SessionLocal() as db:
        try:
            site = crud.get_cms_site_by_key(db, SITE_KEY)
            if site is None:
                raise SystemExit(f"ERROR: CMS site {SITE_KEY!r} not found")

            page = crud.get_cms_page(db, site.id, PAGE_SLUG)
            if page is None:
                raise SystemExit(
                    f"ERROR: page slug={PAGE_SLUG!r} not found for site {SITE_KEY!r}. "
                    "Run scripts/ensure_public_cms_pastors.py first."
                )

            admin = find_canonical_admin(db)
            if admin is None:
                raise SystemExit(
                    "ERROR: no active admin user with sede found. "
                    f"Either create {CANONICAL_ADMIN_EMAIL!r} or activate any user with sede."
                )
            print(f"Acting as: {admin.email} (user_id={admin.id})")
            print()

            print("─── Per-pastor fixes ───")
            dry_count = 0
            for slug, jpg_filename in FIX_MAP:
                if only_slugs and slug not in only_slugs:
                    print(f"  [-- ]   {slug}: skipped by --only")
                    continue
                mode, new_url = fix_one_pastor(
                    db, slug, jpg_filename, admin, dry_run
                )
                if mode == "changed" and new_url:
                    affected.append((slug, new_url))
                elif mode == "dry":
                    dry_count += 1

            print()
            print("─── Publish ───")
            if dry_run:
                print(
                    f"[DRY_RUN] would publish {dry_count} fix(es); "
                    f"no filesystem or DB writes performed."
                )
                db.rollback()
                return 0

            if not affected:
                print("[no-op] all FIX_MAP slugs already on canonical URLs.")
                db.commit()
                return 0

            print(
                f"[publish] driving transition_cms_page_status(action='publish') "
                f"for {len(affected)} updated pastel pastors…"
            )
            print(
                "  This will: resync section.props_json from personas, "
                "snapshot a new CmsPageVersion, and write a CmsPublishLog entry."
            )
            result = crud.transition_cms_page_status(
                db,
                page,
                action="publish",
                user_id=admin.id,
                notes=(
                    f"fix_pastor_photos.py: reattached {len(affected)} pastor "
                    f"photos ({', '.join(s for s, _ in affected)})"
                ),
            )
            if result is None:
                raise SystemExit("ERROR: transition_cms_page_status returned None")

            print()
            print("─── Summary ───")
            print(f"  page.status             = {result.status}")
            print(f"  page.published_version  = {result.published_version_id}")
            print(f"  pastors reattached      = {len(affected)}")
            print()
            print("New URLs now wired through CmsMediaItem → persona.photo_url →")
            print("CmsSection.props_json.pastors[*].image (via workflow sync):")
            for slug, url in sorted(affected):
                print(f"  - {slug:24s} {url}")
            print()
            print("Next steps:")
            print("  1. Verify curl on the URLs above returns 200 + correct photo bytes.")
            print("  2. Reload https://elfarocc.tech/pastores — pastors should match.")
            print("  3. Run scripts/audit_public_media_cms.py to confirm cleanup targets.")
            return 0

        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main())
