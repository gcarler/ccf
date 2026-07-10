#!/usr/bin/env python3
"""Audit pastor-media orphans & broken references.

Background (2026-07-07): the public /pastores page used to display wrong
photos for some pastors. The post-mortem showed two classes of leftover:

  - **Orphans** — files uploaded to ``/uploads/cms/pastores/`` via
    StorageService, but not registered in ``cms_media_items.url``. Their
    URL was hardcoded by hand into the seed scripts and lost track of
    when the actual content moved around the disk.
  - **Broken references** — ``CmsMediaItem`` rows whose ``url`` points to
    a filename that no longer exists (e.g. admin cleaned up disk by
    hand without archiving the row).

This script reconciles the on-disk uploads directory against the
``cms_media_items`` table and reports both classes. It is safe to run
anywhere with filesystem + DB access (cron, manual operator audit,
post-deploy smoke test) and exits non-zero only when ``--fail-on-orphan``
is set and orphan/broken rows are present.

Multi-Tenant safety (Axioma 3)
------------------------------
``CmsMediaItem.sede_id`` is required post 2026-07-01 migration. When run
with ``--sede-id`` the audit is scoped to that sede (correctness widget
per-tenant). Without it, the audit reports per-sede aggregates so a SRE
can spot leak patterns at a glance. The on-disk filesystem side is
tenant-agnostic because uploads_dir is platform-wide; only the DB side is
opt-in per-sede.

Exit codes
----------
  0   Healthy (no orphans, no broken refs) — even with --fail-on-orphan.
  1   At least one orphan or broken ref; use ``--json`` to machine-parse.
  2   Operational error (DB / I/O); stderr explains.

Examples
--------
::

    # Default: human-readable report, exits 0 even with orphans
    python scripts/audit_pastor_media_orphans.py

    # Cron mode: exit 1 if anything is wrong
    python scripts/audit_pastor_media_orphans.py --fail-on-orphan

    # JSON for downstream tooling (PagerDuty alerts, dashboards)
    python scripts/audit_pastor_media_orphans.py --json | jq .orphans

    # Scan a different subfolder + only one sede
    python scripts/audit_pastor_media_orphans.py \\
        --subfolder cms/blog-hero --sede-id <UUID>
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import sys
import uuid as _uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

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


log = logging.getLogger("audit_pastor_media_orphans")


# ── CLI argument parsing ───────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="audit_pastor_media_orphans",
        description=(
            "Reconcile uploads/cms/.../ on disk against cms_media_items. "
            "Reports orphan files and broken DB references."
        ),
    )
    p.add_argument(
        "--subfolder",
        default="cms/pastores",
        help=(
            "Subfolder under uploads/ to audit (default: 'cms/pastores'). "
            "E.g. 'cms/blog-hero', 'cms/events', 'cms/general'."
        ),
    )
    p.add_argument(
        "--sede-id",
        default=None,
        help=(
            "Optional UUID; if set, only CmsMediaItem rows belonging to "
            "the given sede are considered (Axioma 3 multi-tenant)."
        ),
    )
    p.add_argument(
        "--include-archived",
        action="store_true",
        help=(
            "Include CmsMediaItem rows with status='archived' when "
            "reporting broken refs (default excludes them)."
        ),
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit a single JSON object to stdout instead of a human report.",
    )
    p.add_argument(
        "--fail-on-orphan",
        action="store_true",
        help="Exit 1 if any orphan files or broken refs are present.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Default. Audit is non-mutating; the flag exists for "
            "consistency with other scripts."
        ),
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v INFO, -vv DEBUG).",
    )
    return p


# ── Domain dataclasses ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class OrphanFile:
    """File on disk with no matching ``CmsMediaItem`` row."""

    path: str
    size_bytes: int
    mtime_iso: str


@dataclass(frozen=True)
class BrokenRef:
    """``CmsMediaItem`` row whose URL points to a missing on-disk file."""

    media_id: str
    url: str
    expected_path: str
    sede_id: str | None
    status: str


@dataclass(frozen=True)
class AuditReport:
    subfolder: str
    uploads_dir: str
    disk_files_total: int
    db_rows_total: int
    db_rows_active: int
    orphans: list[OrphanFile] = field(default_factory=list)
    broken: list[BrokenRef] = field(default_factory=list)
    by_sede: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        return not self.orphans and not self.broken


# ── Discovery helpers ──────────────────────────────────────────────────────


def _gather_disk_files(uploads_dir: Path, subfolder: str) -> list[Path]:
    """Return regular files in ``<uploads_dir>/<subfolder>/``.

    Hidden directories (``.git``, ``@eaDir`` synology garbage, etc.) are
    skipped. Files we cannot ``stat`` are skipped with a warning rather
    than failing the whole audit — the script is a smoke test, not a
    disk integrity check.
    """
    target = uploads_dir / subfolder
    if not target.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(target.iterdir()):
        if path.name.startswith("."):
            # hidden / dotfiles; not real assets
            continue
        try:
            if path.is_file():
                out.append(path)
            elif path.is_dir():
                # Subdirectory dump: list one level deep but don't recurse
                # — uploads_service doesn't create nested directories today,
                # so this is a defensive no-op rather than intended behavior.
                for nested in sorted(path.iterdir()):
                    if nested.is_file() and not nested.name.startswith("."):
                        out.append(nested)
        except OSError as exc:
            log.warning("skipping unreadable path %s: %s", path, exc)
    return out


def _gather_db_rows(
    db_session,
    *,
    subfolder: str,
    sede_id: str | None,
    include_archived: bool,
) -> list:
    """Load ``CmsMediaItem`` rows whose ``url`` references ``subfolder``.

    The URL convention is ``/api/static/<subfolder>/<basename>`` — see
    ``StorageService.save_file``. We match ``LIKE '/api/static/<subfolder>/%'``
    because the trailing uuid can have arbitrary extensions
    (``.webp``/``.jpg``/``.png``) per optimizer output.
    """
    from backend import models  # imported lazily to keep cold-start cheap

    pattern = f"/api/static/{subfolder}/%"
    query = db_session.query(models.CmsMediaItem).filter(
        models.CmsMediaItem.url.like(pattern)
    )
    if not include_archived:
        query = query.filter(models.CmsMediaItem.status != "archived")
    if sede_id is not None:
        try:
            parsed_sede = _uuid.UUID(str(sede_id))
        except (ValueError, TypeError) as exc:
            raise SystemExit(
                f"ERROR: invalid --sede-id {sede_id!r}: {exc}", code=2
            ) from exc
        query = query.filter(models.CmsMediaItem.sede_id == parsed_sede)
    return query.all()


# ── Reconciliation ─────────────────────────────────────────────────────────


def _registered_basenames(db_rows) -> set[str]:
    """Return the set of basenames referenced by any CmsMediaItem.url.

    We deliberately use ONLY ``Path(row.url).name`` and NOT ``row.filename``.
    The frontend serves URLs — the canonical contract is ``/api/static/<sub>/<uuid>.<ext>``.
    ``row.filename`` is informational metadata (the *originally uploaded*
    filename). Mixing the two would mask real orphans:

      * ``fix_pastor_photos.py`` creates rows with ``filename`` set to the
        manually-uploaded ``<slug>.jpg`` (the original) and ``url`` set to
        the optimized ``<uuid>.webp``.
      * The ``<slug>.jpg`` file on disk is dead weight post-fix — it isn't
        referenced by any URL. It SHOULD show as an orphan so ops can
        cleanup.

    Using URL-derived names only is the right contract: a file is "live"
    iff at least one row's URL points to it.
    """
    return {Path(row.url or "").name for row in db_rows if (row.url or "").strip()}


def _build_report(
    disk_files: Iterable[Path],
    db_rows,
    *,
    uploads_dir: Path,
    subfolder: str,
) -> AuditReport:
    """Compute the diff: orphan files and broken references."""
    disk_basenames: set[str] = {p.name for p in disk_files}
    registered_basenames = _registered_basenames(db_rows)

    orphans: list[OrphanFile] = []
    for path in disk_files:
        if path.name in registered_basenames:
            continue
        try:
            stat = path.stat()
            orphans.append(
                OrphanFile(
                    path=str(path),
                    size_bytes=stat.st_size,
                    mtime_iso=_dt.datetime.fromtimestamp(
                        stat.st_mtime
                    ).isoformat(timespec="seconds"),
                )
            )
        except OSError as exc:
            log.warning("could not stat orphan %s: %s", path, exc)

    broken: list[BrokenRef] = []
    by_sede: dict[str, dict[str, int]] = {}
    for row in db_rows:
        url = row.url or ""
        basename = Path(url).name
        matched_on_disk = (
            basename in disk_basenames
            and (uploads_dir / subfolder / basename).is_file()
        )
        if not matched_on_disk:
            broken.append(
                BrokenRef(
                    media_id=str(row.id),
                    url=url,
                    expected_path=str(uploads_dir / subfolder / basename),
                    sede_id=str(row.sede_id) if row.sede_id else None,
                    status=str(row.status or ""),
                )
            )
        # Aggregate per-sede for the report.
        bucket = by_sede.setdefault(
            str(row.sede_id) if row.sede_id else "<orphan-sede>",
            {"rows": 0, "broken": 0, "active": 0},
        )
        bucket["rows"] += 1
        if (row.status or "").lower() != "archived":
            bucket["active"] += 1
        if not matched_on_disk:
            bucket["broken"] += 1

    active_total = sum(1 for r in db_rows if (r.status or "").lower() != "archived")
    return AuditReport(
        subfolder=subfolder,
        uploads_dir=str(uploads_dir),
        disk_files_total=len(disk_files),
        db_rows_total=len(db_rows),
        db_rows_active=active_total,
        orphans=orphans,
        broken=broken,
        by_sede=by_sede,
    )


# ── Reporting ──────────────────────────────────────────────────────────────


def _format_human(report: AuditReport) -> str:
    lines: list[str] = []
    lines.append(f"Audit subfolder: {report.subfolder}")
    lines.append(f"Uploads dir:     {report.uploads_dir}")
    lines.append(
        f"Disk files:      {report.disk_files_total}    "
        f"DB rows: {report.db_rows_total} (active: {report.db_rows_active})"
    )

    if report.by_sede:
        lines.append("")
        lines.append("Per-sede breakdown:")
        header = f"  {'sede':<38} {'rows':>5} {'active':>7} {'broken':>7}"
        lines.append(header)
        for sede, counts in sorted(report.by_sede.items()):
            lines.append(
                f"  {sede:<38} {counts['rows']:>5} "
                f"{counts['active']:>7} {counts['broken']:>7}"
            )

    if report.orphans:
        lines.append("")
        lines.append(
            f"⚠  {len(report.orphans)} orphan file(s) on disk "
            "(no matching CmsMediaItem):"
        )
        for orphan in report.orphans[:50]:
            lines.append(
                f"  - {orphan.path}  "
                f"({orphan.size_bytes} bytes, mtime={orphan.mtime_iso})"
            )
        if len(report.orphans) > 50:
            lines.append(f"  … {len(report.orphans) - 50} more (truncated)")

    if report.broken:
        lines.append("")
        lines.append(
            f"⚠  {len(report.broken)} broken DB reference(s):"
        )
        for ref in report.broken[:50]:
            raw = ref.media_id
            truncated_id = raw if len(raw) <= 12 else f"{raw[:8]}…{raw[-4:]}"
            lines.append(
                f"  - id={truncated_id:<14} status={ref.status:<10} "
                f"url={ref.url}  expected at {ref.expected_path}"
            )
        if len(report.broken) > 50:
            lines.append(f"  … {len(report.broken) - 50} more (truncated)")

    if report.is_healthy:
        lines.append("")
        lines.append("✅ OK — every disk file has a CmsMediaItem row and every URL is on disk.")
    else:
        lines.append("")
        lines.append("Action: review orphans (delete or register) and broken refs (re-upload or archive).")

    return "\n".join(lines)


def _format_json(report: AuditReport) -> str:
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


# ── Entrypoint ─────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    level = logging.WARNING
    if args.verbose >= 2:
        level = logging.DEBUG
    elif args.verbose == 1:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )

    try:
        from backend.core.config import get_settings
        from backend.core.database import (
            Base,
            SessionLocal,
            engine,
        )
        # Local-dev convenience: when running against a fresh ``sqlite:///``
        # path (typical of ``cli smoke`` or unpublished test DBs) the script
        # would otherwise crash with ``no such table: cms_media_items``.
        # Production runs are PostgreSQL via Alembic, where this guard is a
        # no-op. Calling ``Base.metadata.create_all`` here is belt-and-
        # suspenders for SQLite ONLY — Postgres tables stay under Alembic's
        # exclusive control.
        import backend.models  # noqa: F401  — register all model classes
        if engine.dialect.name == "sqlite":
            Base.metadata.create_all(engine)
    except Exception as exc:  # pragma: no cover - ops path
        print(f"ERROR: cannot import backend: {exc}", file=sys.stderr)
        return 2

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)

    # ── Phase 1: filesystem discovery ───────────────────────────────────
    try:
        disk_files = _gather_disk_files(uploads_dir, args.subfolder)
    except OSError as exc:
        print(
            f"ERROR: cannot list {uploads_dir / args.subfolder}: {exc}",
            file=sys.stderr,
        )
        return 2

    # ── Phase 2: DB discovery ───────────────────────────────────────────
    db_session: Any  # SQLAlchemy ``Session``. Type annotation kept loose
                    # because the ``Any`` import only takes effect under
                    # ``from __future__ import annotations`` (active here)
                    # and pulling the concrete type adds coupling to
                    # ``sqlalchemy.orm.Session`` for a tiny benefit.
    db_rows: list
    db_session = None
    try:
        db_session = SessionLocal()
        db_rows = _gather_db_rows(
            db_session,
            subfolder=args.subfolder,
            sede_id=args.sede_id,
            include_archived=args.include_archived,
        )
    except Exception as exc:
        print(f"ERROR: DB query failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if db_session is not None:
            try:
                db_session.close()
            except Exception:  # pragma: no cover - defensive
                log.warning("error closing DB session", exc_info=True)

    # ── Phase 3: reconciliation ─────────────────────────────────────────
    report = _build_report(
        disk_files,
        db_rows,
        uploads_dir=uploads_dir,
        subfolder=args.subfolder,
    )

    # ── Phase 4: report ────────────────────────────────────────────────
    if args.json:
        sys.stdout.write(_format_json(report) + "\n")
    else:
        sys.stdout.write(_format_human(report) + "\n")

    # ── Phase 5: exit code ──────────────────────────────────────────────
    if args.fail_on_orphan and not report.is_healthy:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
