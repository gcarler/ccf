#!/usr/bin/env python3
"""cleanup_pastor_media_orphans.py — Reconcile the disk and ``cms_media_items``
for ``uploads/cms/pastores``-style folders: delete orphan files (no ``url``
reference) and normalize stale ``CmsMediaItem.filename`` metadata that still
points at a deleted file.

WHY THIS EXISTS
===============
``scripts/fix_pastor_photos.py`` (2026-07-02 + 2026-07-07) ingested the staff-
uploaded slug-named ``.jpg`` pastor photos into ``StorageService.save_file``,
which generated a fresh ``<uuid>.webp`` URL and registered a ``CmsMediaItem``
row. The republished ``/pastores`` page renders the new URLs; the legacy
``.jpg`` files left on disk are now dead weight, and the
``CmsMediaItem.filename`` metadata still says ``<slug>.jpg`` (pointer drift).

This is the cleanup that ``fix_pastor_photos.py`` deliberately left for a
later pass. Idempotent: re-runs after success are no-ops.

WHAT IT DOES
============
For every regular file under ``<uploads>/<subfolder>/``:

1. If the basename is registered by any active ``CmsMediaItem.url`` →
   SKIP. (Those are the live assets.)
2. Otherwise, classify the file as an **orphan** and schedule:
     - ``delete_file`` the disk file.
     - ``update_metadata`` for any ``CmsMediaItem`` row whose
       ``filename`` metadata still points to this basename: rewrite
       it to ``Path(row.url).name`` (= the canonical web asset name).

DRY-RUN BY DEFAULT
==================
Running the script with no flags prints the plan and exits 0. Pass
``--apply`` to actually execute. The DB step uses a real SQLAlchemy
transaction so partial failures roll back cleanly; the disk step uses
per-file ``Path.unlink`` with per-file ``OSError`` capture so a single
permission mishap does not abort the rest of the run.

GUARD-RAILS
===========
* **No deletes outside the configured subfolder.** The default is
  ``cms/pastores``; passing ``--subfolder cms/whatever`` is allowed but
  every target is fully under the directory scanned by the audit. The
  script never walks outside ``<uploads>/<subfolder>/``.
* **Never delete a file referenced by url.** Step 1 above is the gate.
  Even if the audit misclassifies, an active URL → no orphan ⇒ no rm.
* **No create / drop of CmsMediaItem rows.** This script only updates
  one column on existing rows; it intentionally does not insert or
  delete rows so its blast radius is "UPDATE one column on N rows +
  unlink N files".
* **DB-first ordering.** If a per-row UPDATE fails the whole txn rolls
  back; if a per-file ``unlink`` fails we log a warning and continue.
  The surviving state is always either "fully clean" or
  "DB-clean + leftover file" — never "file gone but DB still pointing
  at it", which would be the bad failure mode for live URL consumers.
* **Database banner.** The script prints ``engine.url.host`` /
  ``engine.url.database`` before any action so the operator can see
  whether they're pointing at the right cluster.

USAGE
=====
    # Preview (no DB writes, no rm)
    python scripts/cleanup_pastor_media_orphans.py

    # Execute
    python scripts/cleanup_pastor_media_orphans.py --apply

    # JSON plan for gitops/JQ
    python scripts/cleanup_pastor_media_orphans.py --json | jq .

    # Different subfolder (defaults to cms/pastores)
    python scripts/cleanup_pastor_media_orphans.py --subfolder cms/blog-hero
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ── Project bootstrap (matches convention of every script in ccf/scripts/) ──
_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ``ccf/scripts/`` is a flat directory (no ``__init__.py``) so the audit
# module is not importable as ``backend.scripts.<name>``. Add it to
# ``sys.path`` so we can reuse its helper functions directly. This keeps
# the disk↔DB classification logic in a single place instead of duplicating
# it here.
_SCRIPTS_DIR = _HERE.parent  # /root/ccf/scripts
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from backend.core.config import get_settings  # noqa: E402
from backend.core.database import (  # noqa: E402
    Base,
    SessionLocal,
    engine,
)
import backend.models  # noqa: E402,F401  — register all model classes

# Reuse the audit's discovery path so the disk↔DB logic stays in one place.
# The audit script is the source of truth for "what counts as an orphan".
# These underscore-prefixed names are intentional private surface — by
# importing them here we avoid duplicating the orphan detection rules.
from audit_pastor_media_orphans import (  # type: ignore  # noqa: E402,F401
    OrphanFile,
    _gather_db_rows,
    _gather_disk_files,
)


log = logging.getLogger("cleanup_pastor_media_orphans")


# ── Plan dataclasses ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class CleanupAction:
    """A single planned side-effect, executed by ``--apply``.

    ``action`` is one of:
      - ``"delete_file"``: ``Path.unlink`` the disk file (orphan on disk).
      - ``"update_metadata"``: ``UPDATE cms_media_items SET filename=``.
      - ``"info"``: informational no-op (e.g. "file referenced by url,
        will not delete"). Carried in the plan for transparency.
    """

    action: str
    path: str | None = None
    media_id: str | None = None
    old_filename: str | None = None
    new_filename: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class CleanupPlan:
    subfolder: str
    uploads_dir: str
    db_engine_host: str
    db_engine_database: str
    disk_files_total: int
    db_rows_total: int
    db_rows_active: int
    actions: list[CleanupAction] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def n_deletes(self) -> int:
        return sum(1 for a in self.actions if a.action == "delete_file")

    @property
    def n_updates(self) -> int:
        return sum(1 for a in self.actions if a.action == "update_metadata")

    @property
    def no_op(self) -> bool:
        return self.n_deletes == 0 and self.n_updates == 0


# ── Plan builder ───────────────────────────────────────────────────────────


def _build_plan(
    *,
    disk_files: list[Path],
    db_rows: list,
    uploads_dir: Path,
    subfolder: str,
) -> CleanupPlan:
    """Compute ``CleanupPlan`` from the on-disk + DB state.

    The classification rule mirrors
    ``backend.scripts.audit_pastor_media_orphans._build_report`` — the
    union of basename-from-url-enumeration vs registered rows — but
    here we additionally map each orphan file to its ``filename``
    metadata to know which ``CmsMediaItem.id`` needs a UPDATE.
    """
    db_url = engine.url
    plan = CleanupPlan(
        subfolder=subfolder,
        uploads_dir=str(uploads_dir),
        db_engine_host=getattr(db_url, "host", "") or "",
        db_engine_database=getattr(db_url, "database", "") or "",
        disk_files_total=len(disk_files),
        db_rows_total=len(db_rows),
        db_rows_active=sum(
            1 for r in db_rows if (r.status or "").lower() != "archived"
        ),
    )

    registered_basenames: set[str] = {
        Path(r.url or "").name
        for r in db_rows
        if (r.url or "").strip()
    }

    # Map: filename metadata → list of CmsMediaItem rows. Build BEFORE
    # walking disk_files so we can detect rows whose filename is still
    # a slug .jpg that we want to normalize to the URL basename.
    filename_to_rows: dict[str, list] = {}
    for r in db_rows:
        fn = (r.filename or "").strip()
        if not fn:
            continue
        filename_to_rows.setdefault(fn, []).append(r)

    rows_updated_by_filename_new: set[Any] = set()

    for path in disk_files:
        basename = path.name

        # Guard rail 1: never delete a file referenced by CmsMediaItem.url.
        if basename in registered_basenames:
            plan.actions.append(
                CleanupAction(
                    action="info",
                    path=str(path),
                    reason="basename is referenced by an active CmsMediaItem.url",
                )
            )
            continue

        # Step A: emit UPDATE actions for rows whose filename matches.
        rows_with_filename = filename_to_rows.get(basename, [])
        for row in rows_with_filename:
            expected = Path(row.url or "").name
            if not expected:
                plan.errors.append(
                    f"row id={row.id} has url='' but filename={row.filename}; "
                    "cannot infer canonical name"
                )
                continue
            if expected == (row.filename or "").strip():
                # Already normalized; do not emit a redundant UPDATE.
                plan.actions.append(
                    CleanupAction(
                        action="info",
                        media_id=str(row.id),
                        reason="CmsMediaItem.filename already matches URL basename",
                    )
                )
                continue
            plan.actions.append(
                CleanupAction(
                    action="update_metadata",
                    path=str(path),
                    media_id=str(row.id),
                    old_filename=row.filename,
                    new_filename=expected,
                    reason="filename metadata drift — url already points elsewhere",
                )
            )
            rows_updated_by_filename_new.add(row.id)

        # Step B: emit delete action for the orphan file on disk.
        plan.actions.append(
            CleanupAction(
                action="delete_file",
                path=str(path),
                reason=(
                    f"orphan file (no cms_media_items.url reference); "
                    f"{len(rows_with_filename)} row(s) had filename metadata "
                    f"pointing here"
                ),
            )
        )

    # Catch rows whose filename metadata is drift but disk file is already
    # gone — those are pure DB UPDATEs, no companion delete. They are
    # pleasant edge cases (the file was deleted by hand earlier).
    orphan_drift_rows: list[Any] = []
    for fn, rows in filename_to_rows.items():
        for row in rows:
            if row.id in rows_updated_by_filename_new:
                continue
            expected = Path(row.url or "").name
            if not expected:
                continue
            if expected == (row.filename or "").strip():
                continue
            on_disk = (uploads_dir / subfolder / fn).is_file()
            if on_disk:
                continue  # already handled above
            orphan_drift_rows.append((row, expected))

    for row, expected in orphan_drift_rows:
        plan.actions.append(
            CleanupAction(
                action="update_metadata",
                media_id=str(row.id),
                old_filename=row.filename,
                new_filename=expected,
                reason="filename metadata drift fixed, disk file already absent",
            )
        )

    return plan


# ── Output formatters ──────────────────────────────────────────────────────


def _format_human(plan: CleanupPlan, apply_mode: bool) -> str:
    if engine.dialect.name == "sqlite":
        engine_kind = "SQLite"
    else:
        engine_kind = engine.dialect.name
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append(f"cleanup_pastor_media_orphans.py ({'APPLY' if apply_mode else 'DRY-RUN'})")
    lines.append("=" * 78)
    lines.append(f"  subfolder:           {plan.subfolder}")
    lines.append(f"  uploads_dir:         {plan.uploads_dir}")
    lines.append(f"  DB engine:           {engine_kind}")
    lines.append(f"  DB host:             {plan.db_engine_host}")
    lines.append(f"  DB database:         {plan.db_engine_database}")
    lines.append(
        f"  disk_files_total:    {plan.disk_files_total}"
        f"    db_rows_active: {plan.db_rows_active}"
    )
    lines.append(f"  planned deletes:     {plan.n_deletes}")
    lines.append(f"  planned updates:     {plan.n_updates}")
    lines.append("")

    if plan.no_op:
        lines.append(
            "✅ Nothing to do — every CmsMediaItem.filename matches its "
            "URL basename and there are no orphan files in the subfolder."
        )
        return "\n".join(lines) + "\n"

    # Group actions for legibility.
    deletes = [a for a in plan.actions if a.action == "delete_file"]
    updates = [a for a in plan.actions if a.action == "update_metadata"]
    infos = [a for a in plan.actions if a.action == "info"]

    if updates:
        lines.append(f"Updates ({len(updates)}):")
        lines.append(
            "  " + f"{'media_id':<18} {'old.filename':<35} {'new.filename':<40}"
        )
        for a in updates:
            mid = (a.media_id[:16] + "…") if len(a.media_id or "") > 16 else (
                a.media_id or "-"
            )
            lines.append(
                f"  {mid:<18} "
                f"{a.old_filename or '-':<35} "
                f"{a.new_filename or '-':<40}"
            )
        lines.append("")

    if deletes:
        lines.append(f"Deletes ({len(deletes)}):")
        for a in deletes:
            size_str = ""
            try:
                size = Path(a.path).stat().st_size
                size_str = f"  ({size} bytes)"
            except OSError:
                pass
            lines.append(f"  - {a.path}{size_str}")
        lines.append("")

    if infos:
        preview = infos[:5]
        lines.append(f"Info-only entries ({len(infos)}; first 5):")
        for a in preview:
            lines.append(f"  - {a.reason}")
        if len(infos) > 5:
            lines.append(f"  … {len(infos) - 5} more")
        lines.append("")

    if plan.errors:
        lines.append(f"⚠  Pre-flight errors ({len(plan.errors)}):")
        for err in plan.errors:
            lines.append(f"  - {err}")
        lines.append("")

    if not apply_mode:
        lines.append("Re-run with --apply to execute these actions.")
    return "\n".join(lines) + "\n"


def _format_json(plan: CleanupPlan, apply_mode: bool) -> str:
    payload = {
        "apply": apply_mode,
        "subfolder": plan.subfolder,
        "uploads_dir": plan.uploads_dir,
        "db_engine_host": plan.db_engine_host,
        "db_engine_database": plan.db_engine_database,
        "summary": {
            "disk_files_total": plan.disk_files_total,
            "db_rows_total": plan.db_rows_total,
            "db_rows_active": plan.db_rows_active,
            "planned_deletes": plan.n_deletes,
            "planned_updates": plan.n_updates,
            "no_op": plan.no_op,
        },
        "actions": [asdict(a) for a in plan.actions],
        "errors": list(plan.errors),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ── Executor ───────────────────────────────────────────────────────────────


def _execute_plan(db_session, plan: CleanupPlan) -> tuple[int, int]:
    """Apply ``plan`` to the live system. Returns ``(n_updated, n_deleted)``.

    DB-first ordering:

    1. ``UPDATE cms_media_items SET filename=:new WHERE id=:id`` for every
       ``update_metadata`` action — single SQLAlchemy .commit() at the end.
    2. Per-file ``Path.unlink()`` for every ``delete_file`` action —
       per-file OSError capture so one mistyped perms doesn't cascade.
    """
    rows_updated = 0
    files_deleted = 0

    # ── Phase 1: DB UPDATEs (transactional) ──────────────────────────
    from backend import models

    try:
        for action in plan.actions:
            if action.action != "update_metadata":
                continue
            # Re-resolve the row in the live session (don't trust plans for
            # values that the DB may have changed concurrently).
            row = db_session.get(models.CmsMediaItem, action.media_id)
            if row is None:
                log.warning(
                    "skipping UPDATE for missing media_id=%s", action.media_id
                )
                continue
            row.filename = action.new_filename
            rows_updated += 1
        db_session.commit()
    except Exception:
        log.exception("DB commit failed; rolling back; no files deleted")
        db_session.rollback()
        raise

    # ── Phase 2: disk deletes ────────────────────────────────────────
    for action in plan.actions:
        if action.action != "delete_file":
            continue
        try:
            Path(action.path).unlink(missing_ok=True)
            files_deleted += 1
        except OSError as exc:
            log.warning("failed to delete %s: %s", action.path, exc)
            print(f"  WARN: failed to delete {action.path}: {exc}")

    return rows_updated, files_deleted


# ── CLI ────────────────────────────────────────────────────────────────────


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cleanup_pastor_media_orphans",
        description=(
            "Delete orphan media files in uploads/<subfolder>/ and "
            "normalize CmsMediaItem.filename metadata to URL basename."
        ),
    )
    p.add_argument(
        "--subfolder",
        default="cms/pastores",
        help="Subfolder under uploads/ to reconcile (default: 'cms/pastores').",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help=(
            "Execute the planned DB updates and disk deletes. Without this "
            "flag the script is a read-only dry-run."
        ),
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit a single JSON document instead of a human report.",
    )
    p.add_argument(
        "--include-archived",
        action="store_true",
        help="Include archived CmsMediaItem rows when classifying orphans.",
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase log verbosity (-v INFO, -vv DEBUG).",
    )
    return p


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

    # SQLite guard — mirror the audit script so local-dev runs don't
    # crash with 'no such table: cms_media_items'. Production runs are
    # PostgreSQL via Alembic where this guard is a no-op.
    if engine.dialect.name == "sqlite":
        Base.metadata.create_all(engine)

    settings = get_settings()
    uploads_dir = Path(settings.uploads_dir)

    # ── Phase 1: state discovery ────────────────────────────────────
    try:
        disk_files = _gather_disk_files(uploads_dir, args.subfolder)
    except OSError as exc:
        print(f"ERROR: cannot list {uploads_dir / args.subfolder}: {exc}", file=sys.stderr)
        return 2

    db_session = None
    try:
        db_session = SessionLocal()
        db_rows = _gather_db_rows(
            db_session,
            subfolder=args.subfolder,
            sede_id=None,
            include_archived=args.include_archived,
        )
    except Exception as exc:
        print(f"ERROR: DB query failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if db_session is not None:
            try:
                db_session.close()
            except Exception:
                log.warning("error closing DB session", exc_info=True)

    # ── Phase 2: build plan ─────────────────────────────────────────
    plan = _build_plan(
        disk_files=disk_files,
        db_rows=db_rows,
        uploads_dir=uploads_dir,
        subfolder=args.subfolder,
    )

    # ── Phase 3: report ─────────────────────────────────────────────
    if args.json:
        sys.stdout.write(_format_json(plan, apply_mode=args.apply) + "\n")
    else:
        sys.stdout.write(_format_human(plan, apply_mode=args.apply))

    # ── Phase 4: exit / apply ───────────────────────────────────────
    if not args.apply:
        # Dry-run: exit 0 even with planned actions.
        return 0

    if plan.no_op:
        return 0

    # Apply requires a fresh session — we already closed the discovery
    # session above. Open a new one for the executor.
    apply_session = SessionLocal()
    try:
        rows_updated, files_deleted = _execute_plan(apply_session, plan)
        log.info("APPLY done: %d row(s) updated, %d file(s) deleted",
                 rows_updated, files_deleted)
    except Exception as exc:
        log.exception("apply failed: %s", exc)
        return 2
    finally:
        apply_session.close()

    if not args.json:
        print("=" * 78)
        print("Cleanup result:")
        print(f"  rows_updated:    {rows_updated}")
        print(f"  files_deleted:   {files_deleted}")
        print("=" * 78)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
