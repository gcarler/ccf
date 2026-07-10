"""Re-publish a public CmsPage from its live ``CmsSection`` rows.

When editors mutate sections via the CMS builder but never press *Publicar*
in the workflow UI, ``/api/cms/v2/public/sites/{site_key}/pages/{slug}``
keeps serving the stale ``CmsPageVersion.snapshot_json``. This script
materializes a fresh ``CmsPageVersion`` from the current non-deleted
sections, repoints ``CmsPage.published_version_id`` at it, and writes an
audit row to ``CmsPublishLog`` so editors can see the re-publish in the
log of the page itself.

Operational script (per REGLAS.md §11). Idempotent — each run creates
exactly one new ``CmsPageVersion`` (version_number = current max + 1) and
flips ``published_version_id``. Safe to rerun.

Usage::

    python3 ccf/scripts/republish_home_cms_snapshot.py
    python3 ccf/scripts/republish_home_cms_snapshot.py faro home
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import backend.models  # noqa: E402  — registers every model
import backend.models_cms as m  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402
from backend.models_shared import _utcnow  # noqa: E402


def _section_payload(row: m.CmsSection) -> dict[str, Any]:
    """Materialize the ``sections`` entry that will be stored in
    ``CmsPageVersion.snapshot_json``. Mirrors the shape consumed by
    ``backend.api.cms_v2._snapshot_section_read`` so the public
    endpoint reconstructs the same ``CmsSectionRead`` we wrote.
    """

    return {
        "section_key": row.section_key,
        "type": row.type,
        "props_json": row.props_json or {},
        "sort_order": row.sort_order if row.sort_order is not None else 0,
        "is_visible": bool(row.is_visible) if row.is_visible is not None else True,
        "status": row.status or "active",
        "locale": row.locale or "es",
        "is_global": bool(row.is_global),
        "global_key": row.global_key,
    }


def _build_snapshot(page: m.CmsPage, section_rows: list[m.CmsSection]) -> dict[str, Any]:
    return {
        "page": {
            "id": str(page.id),
            "slug": page.slug,
            "title": page.title,
            "status": page.status,
            "seo_json": page.seo_json or {},
        },
        "sections": [_section_payload(s) for s in sorted(
            section_rows,
            key=lambda r: (r.sort_order if r.sort_order is not None else 0),
        )],
    }


def republish(site_key: str, slug: str, *, actor: str | None = None) -> int:
    """Create a fresh CmsPageVersion snapshot for (site, slug) and flip
    ``published_version_id``. Returns the new version_number.
    """

    actor_note = actor or "scripts/republish_home_cms_snapshot.py"
    with SessionLocal() as db:
        site = (
            db.query(m.CmsSite)
            .filter(m.CmsSite.site_key == site_key.strip().lower())
            .first()
        )
        if site is None:
            raise SystemExit(f"CMS site {site_key!r} not found")

        page = (
            db.query(m.CmsPage)
            .filter(m.CmsPage.site_id == site.id, m.CmsPage.slug == slug)
            .first()
        )
        if page is None:
            raise SystemExit(f"CmsPage slug={slug!r} not found for site {site_key!r}")

        section_rows = (
            db.query(m.CmsSection)
            .filter(
                m.CmsSection.page_id == page.id,
                m.CmsSection.deleted_at.is_(None),
            )
            .order_by(m.CmsSection.sort_order.asc())
            .all()
        )
        visible = [s for s in section_rows if s.is_visible and (s.status or "active") != "archived"]

        max_v = (
            db.query(m.CmsPageVersion.version_number)
            .filter(m.CmsPageVersion.page_id == page.id)
            .order_by(m.CmsPageVersion.version_number.desc())
            .first()
        )
        next_v = (max_v[0] if max_v else 0) + 1

        snapshot_json = _build_snapshot(page, visible)

        version = m.CmsPageVersion(
            id=uuid.uuid4(),
            page_id=page.id,
            version_number=next_v,
            snapshot_json=snapshot_json,
            notes=f"Re-published via {actor_note}",
        )
        db.add(version)
        db.flush()

        previous_pv = page.published_version_id
        page.published_version_id = version.id

        log = m.CmsPublishLog(
            id=uuid.uuid4(),
            site_id=site.id,
            page_id=page.id,
            entity_type="cms_page_version",
            entity_id=str(version.id),
            action="publish",
            from_status=page.status,
            to_status=page.status,
            metadata_json={
                "version_id": str(version.id),
                "version_number": next_v,
                "previous_version_id": str(previous_pv) if previous_pv else None,
                "source": actor_note,
            },
        )
        db.add(log)
        db.commit()

        print(f"Site: {site_key!r}")
        print(f"Page: {slug!r} (id={page.id})")
        print(f"Visible sections re-snapshotted: {len(visible)} / {len(section_rows)} total")
        for s in visible:
            print(f"  · {s.section_key} ({s.type}) sort={s.sort_order} status={s.status!r} locale={s.locale!r}")
        prev_label = f"was {previous_pv}" if previous_pv else "was unset"
        print(f"Published version: v#{next_v} id={version.id} ({prev_label})")
        print(f"Snapshot bytes: {len(json.dumps(snapshot_json, ensure_ascii=False, default=str))}")
        return next_v


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "site_key",
        nargs="?",
        default="ccf",
        help="CMS site_key (default: ccf).",
    )
    parser.add_argument(
        "slug",
        nargs="?",
        default="home",
        help="CmsPage slug inside the site (default: home).",
    )
    args = parser.parse_args()
    republish(args.site_key, args.slug, actor=_utcnow().isoformat())
    return 0


if __name__ == "__main__":
    sys.exit(main())
