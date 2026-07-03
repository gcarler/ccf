from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

# Locate the project root by walking up until we find the `backend/`
# package. This works whether the script lives in scripts/, scripts/seeding/
# scripts/migrations/, scripts/auditing/ or any other nested folder.
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from sqlalchemy.orm import Session

from backend.core.database import SessionLocal
from backend.models_cms import CmsSectionType

# Canonical section types. Source of truth for `cms_section_types.name`.
# Edit this list when introducing a new section type; the seed applies it
# idempotently and the test in tests/test_seed_cms_section_types.py keeps
# the catalog in sync.
EXPECTED_SECTION_TYPES: list[tuple[str, str]] = [
    ("hero", "Hero banner with title, subtitle, and CTA"),
    ("video_hero", "Hero banner with background video"),
    ("rich_text", "Rich text content block"),
    ("rich_text_columns", "Multi-column rich text layout"),
    ("cards", "Grid of cards with images and descriptions"),
    ("cta_banner", "Call-to-action banner"),
    ("gallery", "Image gallery with lightbox"),
    ("faq", "Accordion-style FAQ section"),
    ("embed", "External content embed (YouTube, Maps, etc.)"),
    ("testimonials", "Customer testimonials carousel"),
    ("stats", "Statistics/numbers display"),
    ("team", "Team members display"),
    ("countdown", "Countdown timer"),
    ("pricing", "Pricing table"),
    ("image_text", "Side-by-side image and text"),
    ("timeline", "Timeline of events"),
    ("icon_grid", "Grid of icons with labels"),
    ("newsletter", "Newsletter signup form"),
    ("popup_banner", "Popup/modal banner"),
    ("button", "Standalone button component"),
    ("toc", "Table of contents"),
    ("divider", "Visual divider/separator"),
    ("collapsible", "Collapsible content section"),
    ("social_links", "Social media links"),
    ("spacer", "Vertical spacing element"),
    ("calendar", "Calendar widget"),
    ("map", "Map embed"),
    ("document_upload", "Document upload area"),
    ("content_blocks", "Reusable content blocks"),
    ("accordion", "Accordion component"),
]


@dataclass
class SeedResult:
    """Outcome of a single apply_section_types() pass."""

    added: int
    updated: int
    # Includes any pre-existing rows not in the canonical list ("extras"
    # reported by verify_section_types). Use len(EXPECTED_SECTION_TYPES)
    # for the canonical row count when asserting "clean state".
    total_after: int


@dataclass
class VerifyResult:
    """Outcome of verify_section_types(). Used by `--check`."""

    missing: list[str] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)
    deactivated: list[str] = field(default_factory=list)
    out_of_sync_desc: list[str] = field(default_factory=list)

    @property
    def is_synced(self) -> bool:
        """True iff every canonical name is present and its description matches.

        ``extra`` and ``deactivated`` are informational only: the canonical
        list may legitimately not supersede admin decisions (e.g. a
        previously-deactivated type) and historical rows may legitimately
        outlive the canonical list. Drift that blocks sync is only missing
        names and divergent descriptions.
        """
        return not (self.missing or self.out_of_sync_desc)


def apply_section_types(db: Session) -> SeedResult:
    """Insert missing sections and sync divergent descriptions.

    Idempotency contract:
      * Insert (``is_active=True``) when name is absent.
      * Update ``description`` when it diverges from the canonical entry.
      * Leave ``is_active`` untouched on existing rows: admin deactivations
        are deliberate state and must not be silently reactivated by a
        deploy seed.

    Single-tenant / single-runner: the read-then-write over the existing
    dict is not concurrency-safe versus a concurrent admin edit. Invoke
    from the deploy gate, not in parallel with manual CMS edits.
    """
    canonical = {name: description for name, description in EXPECTED_SECTION_TYPES}
    existing = {row.name: row for row in db.query(CmsSectionType).all()}

    added = 0
    updated = 0
    for name, description in canonical.items():
        row = existing.get(name)
        if row is None:
            db.add(CmsSectionType(name=name, description=description, is_active=True))
            added += 1
        elif row.description != description:
            row.description = description
            updated += 1

    db.commit()
    total_after = db.query(CmsSectionType).count()
    return SeedResult(added=added, updated=updated, total_after=total_after)


def verify_section_types(db: Session) -> VerifyResult:
    """Compute drift between canonical list and current DB state. Read-only."""
    canonical = {name: description for name, description in EXPECTED_SECTION_TYPES}
    existing = {row.name: row for row in db.query(CmsSectionType).all()}

    return VerifyResult(
        missing=[name for name in canonical if name not in existing],
        extra=[name for name in existing if name not in canonical],
        deactivated=[
            name
            for name, row in existing.items()
            if name in canonical and not row.is_active
        ],
        out_of_sync_desc=[
            name
            for name, row in existing.items()
            if name in canonical and row.description != canonical[name]
        ],
    )


def _format_check_drift(result: VerifyResult) -> list[str]:
    lines: list[str] = []
    if result.missing:
        lines.append(f"Missing ({len(result.missing)}):")
        lines.extend(f"  - {name}" for name in result.missing)
    if result.out_of_sync_desc:
        lines.append(f"Out-of-sync descriptions ({len(result.out_of_sync_desc)}):")
        lines.extend(f"  - {name}" for name in result.out_of_sync_desc)
    if result.extra:
        lines.append(f"Extra (not in canonical) ({len(result.extra)}):")
        lines.extend(f"  - {name}" for name in result.extra)
    if result.deactivated:
        lines.append(f"Deactivated ({len(result.deactivated)}):")
        lines.extend(f"  - {name}" for name in result.deactivated)
    return lines


def main(argv: Sequence[str] | None = None, db: Session | None = None) -> int:
    """CLI entry point. Return code is suitable for a CI/deploy gate.

    Modes:
      * default — apply_section_types(), commit changes, print summary.
      * ``--check`` — verify_section_types(), exit 1 on drift, 0 if synced.

    ``db`` is injectable so tests pass their fixture-backed session
    without the script opening (and closing) the production pool.
    """
    args = list(argv if argv is not None else sys.argv[1:])
    check_only = "--check" in args

    own_session = db is None
    session = db if db is not None else SessionLocal()
    try:
        if check_only:
            result = verify_section_types(session)
            for line in _format_check_drift(result):
                print(line)
            if result.is_synced:
                print(
                    "OK"
                    f" — {len(EXPECTED_SECTION_TYPES)} section types match canonical list."
                )
                return 0
            # Note: even with drift here, the verify report may also list
            # ``extra`` or ``deactivated`` rows — those are informational and
            # do not affect the exit code in this revision.
            print("DRIFT detected. Rerun without --check to apply.")
            return 1

        result = apply_section_types(session)
        print(
            "Seed complete"
            f" — added: {result.added}, updated: {result.updated},"
            f" total: {result.total_after}"
        )
        return 0
    finally:
        if own_session:
            session.close()


if __name__ == "__main__":
    raise SystemExit(main())
