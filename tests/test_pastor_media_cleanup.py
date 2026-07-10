"""Regression tests for ``scripts/cleanup_pastor_media_orphans.py``.

WHY THIS EXISTS
===============
The cleanup script is destructive (it both ``UPDATE``s ``CmsMediaItem``
rows and ``Path.unlink()``s files under ``uploads/<subfolder>/``). Its
correctness hinges on three invariants:

1. **Idempotency.** A clean state must produce an empty plan whether it
   is the first or the hundredth invocation.
2. **Safety rail.** A file whose basename is referenced by any active
   ``CmsMediaItem.url`` is NEVER scheduled for deletion — even if some
   other row has ``filename`` drift pointing at the same basename.
3. **DB-first ordering.** The ``UPDATE`` phase must commit before any
   ``unlink`` runs; a DB failure must roll the file deletes back.

These tests pin the invariants to the live code path so a future
refactor cannot regress them silently. They use the conftest-provided
SQLite-in-memory session (``db_session``) plus a per-test ``tmp_path``
that is monkeypatched into ``settings.uploads_dir`` for EndToEnd runs;
the engine-bound helpers (``_build_plan``, ``_execute_plan``,
``_format_json``, ``_format_human``) are exercised by direct call so we
do not need to mock ``SessionLocal`` for the bulk of the suite.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import uuid as _uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from unittest import mock

import pytest


# ── Project bootstrap (matches the script under test) ──────────────────
_HERE = Path(__file__).resolve()
_CCF_ROOT = _HERE.parents[1]                 # /root/ccf/ccf
_PROJECT_ROOT = _CCF_ROOT.parent             # /root/ccf
_SCRIPTS_DIR = _CCF_ROOT / "scripts"         # /root/ccf/ccf/scripts
for path in (_PROJECT_ROOT, _CCF_ROOT, _SCRIPTS_DIR):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


from backend import models  # noqa: E402  — directory is on sys.path above
# ``ccf/scripts`` is a flat directory (no ``__init__.py``) so the
# cleanup module is imported by its file name, not as ``scripts.<x>``.
import cleanup_pastor_media_orphans as cleanup  # noqa: E402


# ── Constants & helpers ─────────────────────────────────────────────────

SUBFOLDER = "cms/pastores"


def _url_basename(url: str) -> str:
    return url.rsplit("/", 1)[-1] if url else ""


def _write_file(path: Path, content: bytes = b"placeholder-bytes") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@dataclass
class _MediaFactory:
    """Compact builder for ``CmsMediaItem`` rows in tests.

    Centralizing the defaults here keeps the test cases focused on the
    *delta* that matters (which fields differ from baseline) instead of
    repeating the boilerplate.

    ``cms_media_items.created_by_persona_id`` and ``sede_id`` are
    ``NOT NULL`` per the post-2026-07-01 Axioma-3 migration. When the
    caller does not pass them, ``make`` synthesizes a fresh
    ``Persona`` + ``Sede`` pair (cheap — one INSERT each) so tests
    can stay isolated. Tests that care about which persona owns the
    row can pass ``created_by_persona_id=`` and ``sede_id=`` explicitly
    (e.g. when asserting cross-table FK behavior).
    """

    db: object
    _sede_cache: object = None
    _persona_cache: object = None

    def _ensure_anchor(self) -> tuple[object, object]:
        if self._sede_cache is None:
            sede = models.Sede(
                id=_uuid.uuid4(),
                nombre="Sede Test Cleanup",
                ciudad="Bogota",  # NOT NULL per schema
                es_activa=True,
            )
            self.db.add(sede)
            self.db.flush()
            self._sede_cache = sede.id
        if self._persona_cache is None:
            persona = models.Persona(
                id=_uuid.uuid4(),
                first_name="Cleanup",
                last_name="Test",
                email=f"cleanup-{_uuid.uuid4().hex}@test.local",
                sede_id=self._sede_cache,
                estado_vital="ACTIVO",
            )
            self.db.add(persona)
            self.db.flush()
            self._persona_cache = persona.id
        return self._sede_cache, self._persona_cache

    def make(
        self,
        *,
        url: str | None = None,
        filename: str | None = None,
        status: str = "active",
        section: str = "pastores",
        tags: list[str] | None = None,
        sede_id: object | None = None,
        created_by_persona_id: object | None = None,
    ) -> models.CmsMediaItem:
        if sede_id is None or created_by_persona_id is None:
            sede_anchor, persona_anchor = self._ensure_anchor()
        sede_id = sede_id if sede_id is not None else sede_anchor
        created_by_persona_id = (
            created_by_persona_id
            if created_by_persona_id is not None
            else persona_anchor
        )

        uuid = _uuid.uuid4()
        url_str = url or f"/api/static/{SUBFOLDER}/{uuid.hex}.webp"
        filename_str = filename or _url_basename(url_str)
        row = models.CmsMediaItem(
            id=uuid,
            url=url_str,
            alt_text="test",
            filename=filename_str,
            mime_type="image/webp",
            file_size=100,
            section=section,
            tags=list(tags or []),
            status=status,
            sede_id=sede_id,
            created_by_persona_id=created_by_persona_id,
        )
        self.db.add(row)
        self.db.flush()
        return row


@pytest.fixture
def media_factory(db_session):
    return _MediaFactory(db=db_session)


@pytest.fixture
def tmp_uploads(tmp_path, monkeypatch):
    """Temporarily redirect ``settings.uploads_dir`` to a per-test dir.

    The fixture creates ``<tmp>/cms/pastores/`` ready for the cleanup
    script's ``_gather_disk_files`` to enumerate, then mutates the
    ``Settings`` instance returned by ``backend.core.config.get_settings()``
    so its ``uploads_dir`` points at ``tmp_path``. Anything that reads
    from the live cached settings (e.g. ``cleanup.main()``) sees the
    isolated directory.

    The monkeypatch is undone automatically by pytest at teardown so
    the real ``uploads_dir`` is restored before the next test.

    Module surface (verified): ``backend.core.config`` exports the
    ``Settings`` *class* plus the ``get_settings()`` *function* — there
    is no module-level ``settings`` *instance* attribute. Hence the
    `get_settings()` call below instead of ``from ... import settings``.
    """
    uploads_root = tmp_path / "uploads"
    (uploads_root / "cms" / "pastores").mkdir(parents=True)
    from backend.core.config import get_settings as _get_settings
    live = _get_settings()
    monkeypatch.setattr(live, "uploads_dir", str(uploads_root))
    return uploads_root


@pytest.fixture
def patched_main_env(db_session, tmp_uploads, monkeypatch):
    """Configure the cleanup module so ``main()`` runs against the test
    engine and a per-test uploads directory.

    The cleanup script imports ``engine`` and ``SessionLocal`` from
    ``backend.core.database`` at module load time. ``main()`` then
    references those attributes directly (``if engine.dialect.name``,
    ``db_session = SessionLocal()``). Patching the cleanup module's own
    ``engine`` and ``SessionLocal`` attributes is the cleanest way to
    redirect main() at the conftest's in-memory engine without forking
    any production code paths.

    Returns the bare ``tmp_uploads`` for assertions on disk.
    """
    # The conftest's ``Settings`` instance is bound to ENGINE we want.
    from tests.conftest import engine as test_engine
    from tests.conftest import TestingSessionLocal as test_session_factory
    # The conftest engine talks SQLite + the conftest's in-memory schema
    # which the autouse ``_reset_caches_between_tests`` does not touch
    # (no Redis interference).
    monkeypatch.setattr(cleanup, "engine", test_engine)
    monkeypatch.setattr(cleanup, "SessionLocal", test_session_factory)
    return tmp_uploads


# ── Plan-builder tests (pure logic, no DB writes) ──────────────────────


class TestPlanBuilder:
    """Drive ``_build_plan`` directly to verify classification rules.

    These tests never touch a real DB session for *assertions on the
    plan* (the rows passed in are real ORM objects via ``db_session``,
    but the plan is built from a snapshot; no mutation is asserted).
    """

    def test_no_files_no_rows_is_noop(
        self, db_session, tmp_uploads
    ):
        plan = cleanup._build_plan(
            disk_files=[],
            db_rows=[],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan.no_op
        assert plan.n_deletes == 0
        assert plan.n_updates == 0
        # The dataclass field uses ``field(default_factory=list)``, so
        # an empty plan's ``actions`` is an empty list (not a tuple).
        # We assert semantically: no mutating actions in the plan.
        assert all(a.action == "info" for a in plan.actions)
        # The plan object's own .actions is a list; both [] and ()
        # compare equal in spirit. Pin via length instead of structural
        # type so future refactors to either list/tuple/set pass.
        assert len(plan.actions) == 0

    def test_live_webp_file_is_info_only(
        self, db_session, tmp_uploads, media_factory
    ):
        """A webp whose basename is in registered_basenames is protected."""
        # Disk
        live = _write_file(tmp_uploads / SUBFOLDER / "abc123.webp")
        # DB — row whose url ends in /abc123.webp
        row = media_factory.make(
            url="/api/static/cms/pastores/abc123.webp",
            filename="abc123.webp",
        )
        plan = cleanup._build_plan(
            disk_files=[live],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan.n_deletes == 0
        assert plan.n_updates == 0
        info_entries = [a for a in plan.actions if a.action == "info"]
        assert len(info_entries) == 1
        assert info_entries[0].path == str(live)
        assert "CmsMediaItem.url" in (info_entries[0].reason or "")

    def test_orphan_jpg_with_drifted_metadata(
        self, db_session, tmp_uploads, media_factory
    ):
        """The canonical fix scenario:
        ``filename=<slug>.jpg`` but ``url=<uuid>.webp``.
        Plan: 1 delete + 1 update with ``new_filename`` = ``url basename``.
        """
        orphan = _write_file(tmp_uploads / SUBFOLDER / "luis-ricardo-meza.jpg")
        row = media_factory.make(
            url="/api/static/cms/pastores/different_uuid.webp",
            filename="luis-ricardo-meza.jpg",
        )
        plan = cleanup._build_plan(
            disk_files=[orphan],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan.n_deletes == 1
        assert plan.n_updates == 1
        update = next(a for a in plan.actions if a.action == "update_metadata")
        delete = next(a for a in plan.actions if a.action == "delete_file")
        assert update.old_filename == "luis-ricardo-meza.jpg"
        assert update.new_filename == "different_uuid.webp"
        assert update.media_id == str(row.id)
        assert delete.path == str(orphan)

    def test_already_normalized_metadata_is_noop(
        self, db_session, tmp_uploads, media_factory
    ):
        """If filename already equals URL basename AND file is live,
        the plan must contain zero mutating actions.
        """
        live = _write_file(tmp_uploads / SUBFOLDER / "clean_uuid.webp")
        row = media_factory.make(
            url="/api/static/cms/pastores/clean_uuid.webp",
            filename="clean_uuid.webp",
        )
        plan = cleanup._build_plan(
            disk_files=[live],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan.no_op
        # The 1 information entry about the live file is allowed but
        # must be the only thing in the plan.
        info = [a for a in plan.actions if a.action == "info"]
        assert len(info) == 1
        delete = [a for a in plan.actions if a.action == "delete_file"]
        update = [a for a in plan.actions if a.action == "update_metadata"]
        assert delete == []
        assert update == []

    def test_safety_rail_live_file_with_drifted_sibling_row(
        self, db_session, tmp_uploads, media_factory
    ):
        """CRITICAL safety rail: a file whose basename is registered
        (live url) must never appear in ``n_deletes`` even if some
        other row has ``filename`` metadata drift referencing the same
        basename. This is the guard against the producer bug "delete
        the live asset because metadata says another name" — the test
        exists to make that regression loud.

        Note: when the disk file IS live, the script legitimately does
        NOT emit a ``update_metadata`` for the drift row either
        (``live_uuid.webp`` lives on by row_live.url; row_drift's
        ``filename`` drift is informational, not correctness-shaping,
        so leaving it alone is acceptable). The strict invariant we
        pin here is therefore exclusively the absence of deletes.
        """
        live = _write_file(tmp_uploads / SUBFOLDER / "live_uuid.webp")
        # Row A: live — url + filename both match the basename.
        row_live = media_factory.make(
            url="/api/static/cms/pastores/live_uuid.webp",
            filename="live_uuid.webp",
        )
        # Row B: drift — url points elsewhere, but ``filename`` claims
        # the live basename. The script must protect the live file.
        row_drift = media_factory.make(
            url="/api/static/cms/pastores/other_uuid.webp",
            filename="live_uuid.webp",
        )

        plan = cleanup._build_plan(
            disk_files=[live],
            db_rows=[row_live, row_drift],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan.n_deletes == 0, (
            "safety rail FAILED: a file whose basename is referenced by "
            "CmsMediaItem.url must never be in the delete plan"
        )
        # The live file must appear in the plan with action="info",
        # confirming the script recognizes it as live (not orphan).
        infos = [a for a in plan.actions if a.action == "info"]
        assert any(i.path == str(live) for i in infos), (
            "live file must be classified as info (referenced by url), "
            f"got actions: {[a.__dict__ for a in plan.actions]}"
        )
        # And there must be no UPDATE_METADATA attributable to row_drift
        # specifically — re-emphasizes that drift-to-live-file is
        # outside the script's scope (the file is safe by construction).
        updates_for_drift = [
            a for a in plan.actions
            if a.action == "update_metadata" and a.media_id == str(row_drift.id)
        ]
        assert updates_for_drift == [], (
            f"drift row pointing at a live file should not trigger an "
            f"UPDATE; got {updates_for_drift}"
        )

    def test_db_only_drift_without_disk_file(
        self, db_session, tmp_uploads, media_factory
    ):
        """Row drift where the orphaned file is already absent:
        a pure DB-only ``update_metadata`` (no paired ``delete_file``).
        """
        # No file on disk.
        row = media_factory.make(
            url="/api/static/cms/pastores/gone_uuid.webp",
            filename="old_drift.jpg",
        )
        plan = cleanup._build_plan(
            disk_files=[],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan.n_deletes == 0
        assert plan.n_updates == 1
        update = plan.actions[0]
        assert update.old_filename == "old_drift.jpg"
        assert update.new_filename == "gone_uuid.webp"
        assert update.media_id == str(row.id)
        # The ``reason`` is the no-disk variant — readable in audit logs.
        assert "disk file already absent" in (update.reason or "")

    def test_multiple_rows_share_orphan_filename(
        self, db_session, tmp_uploads, media_factory
    ):
        """Defensive case: two rows both have ``filename`` drift to the
        same orphan. The plan must UPDATE both, but ``delete_file`` only
        once (Path.unlink is idempotent; double-delete would otherwise
        silently mask a config bug that emitted duplicates).
        """
        orphan = _write_file(tmp_uploads / SUBFOLDER / "alex-y-elvia.jpg")
        row1 = media_factory.make(
            url="/api/static/cms/pastores/uu_a.webp",
            filename="alex-y-elvia.jpg",
        )
        row2 = media_factory.make(
            url="/api/static/cms/pastores/uu_b.webp",
            filename="alex-y-elvia.jpg",
        )
        plan = cleanup._build_plan(
            disk_files=[orphan],
            db_rows=[row1, row2],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan.n_deletes == 1
        assert plan.n_updates == 2
        updates = [a for a in plan.actions if a.action == "update_metadata"]
        assert updates[0].media_id == str(row1.id)
        assert updates[1].media_id == str(row2.id)
        # Both rows point to their own url basename after update.
        assert updates[0].new_filename == "uu_a.webp"
        assert updates[1].new_filename == "uu_b.webp"


# ── Executor tests (real DB writes, real file mutations in tmpdir) ──────


class TestExecutor:
    """Verify ``_execute_plan`` performs DB-first ordering and idempotency.

    These tests call the real ``_execute_plan`` with the test session
    and a synthetic plan. They confirm post-conditions on disk and in
    the DB so a regression to a "delete-then-write" order (or a missing
    commit) is caught.
    """

    def test_execute_updates_filename_then_unlinks_file(
        self, db_session, tmp_uploads, media_factory
    ):
        """DB-first: after ``_execute_plan``, the row's filename must be
        updated AND the file must be gone from disk. The order matters
        only for failure recovery; the visible post-state is the
        cleanup's contract.
        """
        orphan = _write_file(tmp_uploads / SUBFOLDER / "luis-ricardo-meza.jpg")
        row = media_factory.make(
            url="/api/static/cms/pastores/luis_uuid.webp",
            filename="luis-ricardo-meza.jpg",
        )
        plan = cleanup._build_plan(
            disk_files=[orphan],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        cleanup._execute_plan(db_session, plan)

        db_session.expire_all()
        refreshed = (
            db_session.query(models.CmsMediaItem).filter_by(id=row.id).one()
        )
        assert refreshed.filename == "luis_uuid.webp"
        assert not orphan.exists()

    def test_idempotency_second_run_is_noop(
        self, db_session, tmp_uploads, media_factory
    ):
        """After applying once, rebuilding the plan from the same
        world-state must produce zero mutating actions. Repeated
        ``main`` invocations therefore converge.
        """
        orphan = _write_file(tmp_uploads / SUBFOLDER / "luis-ricardo-meza.jpg")
        row = media_factory.make(
            url="/api/static/cms/pastores/luis_uuid.webp",
            filename="luis-ricardo-meza.jpg",
        )
        plan_first = cleanup._build_plan(
            disk_files=[orphan],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        cleanup._execute_plan(db_session, plan_first)

        # Re-snapshot the world to feed the second plan. The orphan is
        # gone; the row's filename is now in sync with url basename.
        db_session.expire_all()
        refreshed = (
            db_session.query(models.CmsMediaItem).filter_by(id=row.id).one()
        )
        remaining_disk: list[Path] = [
            p for p in tmp_uploads.rglob("*")
            if p.is_file() and p.suffix in {".jpg", ".webp"}
        ]
        plan_second = cleanup._build_plan(
            disk_files=remaining_disk,
            db_rows=[refreshed],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        assert plan_second.no_op, (
            f"idempotency violated: second plan has "
            f"{plan_second.n_deletes} deletes / "
            f"{plan_second.n_updates} updates"
        )

    def test_execute_skips_stale_media_id(
        self, db_session, tmp_uploads, media_factory
    ):
        """If ``media_id`` in an UPDATE action was deleted between plan
        build and exec (e.g. concurrent operation by another process),
        ``db_session.get`` returns ``None`` and the executor emits a
        warning instead of raising. The plan must remain valid for the
        remaining actions.
        """
        # Build a plan against two rows.
        live = _write_file(tmp_uploads / SUBFOLDER / "live.webp")
        orphan1 = _write_file(tmp_uploads / SUBFOLDER / "missing_row.jpg")
        row_live = media_factory.make(
            url="/api/static/cms/pastores/live.webp",
            filename="live.webp",
        )
        row_present = media_factory.make(
            url="/api/static/cms/pastores/present_uuid.webp",
            filename="missing_row.jpg",
        )

        # Build plan from row_present AND a synthetic "ghost" row that
        # we will delete BEFORE executing the plan. We hand-craft the
        # action so the executor must look up by id and find None.
        ghost_uuid = str(_uuid.uuid4())
        ghost_update = cleanup.CleanupAction(
            action="update_metadata",
            path=str(orphan1),
            media_id=ghost_uuid,
            old_filename="never_existed.jpg",
            new_filename="never_made_it.webp",
            reason="ghost row test",
        )
        # Build a normal plan for the present cases first.
        plan = cleanup._build_plan(
            disk_files=[live, orphan1],
            db_rows=[row_live, row_present],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        # Inject the ghost UPDATE so we cover the None branch.
        plan_actions = list(plan.actions) + [ghost_update]
        plan = cleanup.CleanupPlan(
            subfolder=plan.subfolder,
            uploads_dir=plan.uploads_dir,
            db_engine_host=plan.db_engine_host,
            db_engine_database=plan.db_engine_database,
            disk_files_total=plan.disk_files_total,
            db_rows_total=plan.db_rows_total,
            db_rows_active=plan.db_rows_active,
            actions=tuple(plan_actions),
            errors=tuple(plan.errors),
        )

        # Execute — should not raise.
        rows_updated, files_deleted = cleanup._execute_plan(db_session, plan)

        # The present row must still be updated; the ghost must be
        # silently skipped.
        assert rows_updated == 1
        assert files_deleted == 1
        db_session.expire_all()
        refreshed = (
            db_session.query(models.CmsMediaItem)
            .filter_by(id=row_present.id)
            .one()
        )
        assert refreshed.filename == "present_uuid.webp"

    def test_execute_db_commit_failure_leaves_disk_intact(
        self, db_session, tmp_uploads, media_factory
    ):
        """The DB-first invariant: a commit failure must NOT take the
        files with it. We simulate this by mocking ``commit`` to raise
        and confirm ``unlink`` is never executed (raises out of
        ``_execute_plan`` before phase 2 starts).
        """
        orphan = _write_file(tmp_uploads / SUBFOLDER / "luis-ricardo-meza.jpg")
        row = media_factory.make(
            url="/api/static/cms/pastores/luis_uuid.webp",
            filename="luis-ricardo-meza.jpg",
        )
        plan = cleanup._build_plan(
            disk_files=[orphan],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )

        with mock.patch.object(db_session, "commit", side_effect=RuntimeError("simulated")):
            with pytest.raises(RuntimeError, match="simulated"):
                cleanup._execute_plan(db_session, plan)

        # Disk file must still exist.
        assert orphan.is_file(), (
            "DB-first invariant violated: file was deleted despite commit failure"
        )


# ── Output formatting tests ────────────────────────────────────────────


class TestOutputFormatting:
    """Pin the report formats so CI pipelines can grep / parse them."""

    def test_json_output_is_parseable_and_has_summary(
        self, db_session, tmp_uploads, media_factory
    ):
        orphan = _write_file(tmp_uploads / SUBFOLDER / "luis-ricardo-meza.jpg")
        row = media_factory.make(
            url="/api/static/cms/pastores/luis_uuid.webp",
            filename="luis-ricardo-meza.jpg",
        )
        plan = cleanup._build_plan(
            disk_files=[orphan],
            db_rows=[row],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        output = cleanup._format_json(plan, apply_mode=False)
        parsed = json.loads(output)
        assert parsed["apply"] is False
        assert parsed["subfolder"] == SUBFOLDER
        assert "summary" in parsed
        s = parsed["summary"]
        assert s["disk_files_total"] == 1
        assert s["planned_deletes"] == 1
        assert s["planned_updates"] == 1
        assert s["no_op"] is False
        # Each action has the canonical fields.
        action_kinds = {a["action"] for a in parsed["actions"]}
        assert action_kinds == {"delete_file", "update_metadata"}

    def test_json_output_contains_database_metadata(
        self, db_session, tmp_uploads
    ):
        """The DB host/database fields are exposed so CI can confirm
        the script is pointed at the intended cluster.
        """
        plan = cleanup._build_plan(
            disk_files=[],
            db_rows=[],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        parsed = json.loads(cleanup._format_json(plan, apply_mode=True))
        assert "db_engine_host" in parsed
        assert "db_engine_database" in parsed

    def test_human_output_marks_apply_vs_dry_run(
        self, db_session, tmp_uploads
    ):
        plan = cleanup._build_plan(
            disk_files=[],
            db_rows=[],
            uploads_dir=tmp_uploads,
            subfolder=SUBFOLDER,
        )
        dry = cleanup._format_human(plan, apply_mode=False)
        wet = cleanup._format_human(plan, apply_mode=True)
        assert "DRY-RUN" in dry
        assert "APPLY" in wet
        assert dry != wet
        # Both report the configured subfolder.
        assert SUBFOLDER in dry
        assert SUBFOLDER in wet
        assert "cleanup_pastor_media_orphans.py" in dry


# ── End-to-end smoke test (main() with monkeypatched env) ──────────────


class TestMainEndToEnd:
    """A single smoke test driving ``main()`` so the CLI glue
    (argparse, env wiring through ``engine`` and ``SessionLocal``) is
    exercised against a real ``--apply`` cycle on the test engine.

    ``main()`` opens and closes its own session. To keep this test
    hermetic, we monkeypatch ``cleanup.engine`` to the conftest's
    in-memory engine and override ``cleanup.SessionLocal`` so the
    script's ``SessionLocal()`` returns a session bound to the test
    engine. The same fixture also redirects ``settings.uploads_dir``
    to the per-test tmpdir so disk I/O never leaves pytest's sandbox.
    """

    def test_main_apply_full_cycle_then_idempotent(
        self, db_session, patched_main_env, media_factory, capsys
    ):
        # Build the world.
        orphan = _write_file(patched_main_env / SUBFOLDER / "luis-ricardo-meza.jpg")
        live = _write_file(patched_main_env / SUBFOLDER / "live_uuid.webp")
        media_factory.make(
            url="/api/static/cms/pastores/live_uuid.webp",
            filename="live_uuid.webp",
        )
        drift = media_factory.make(
            url="/api/static/cms/pastores/luis_uuid.webp",
            filename="luis-ricardo-meza.jpg",
        )

        # ── Run #1: --apply ── JSON output via contextlib so we don't
        # fight pytest's own stdout capture (capsys already owns it).
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cleanup.main(["--apply", "--json"])
        parsed = json.loads(buf.getvalue())
        assert rc == 0, "main() --apply must exit 0"
        assert parsed["summary"]["planned_deletes"] >= 1
        assert parsed["summary"]["planned_updates"] >= 1
        captures = capsys.readouterr()  # drain pytest's capture buffer

        # Side effects persisted.
        assert not orphan.exists(), "orphan file should have been removed"
        assert live.is_file(), "live .webp must not be touched by cleanup"
        db_session.expire_all()
        refreshed_first = (
            db_session.query(models.CmsMediaItem)
            .filter_by(id=drift.id)
            .one()
        )
        assert refreshed_first.filename == "luis_uuid.webp", (
            f"filename drift not normalized; got {refreshed_first.filename!r}"
        )

        # ── Run #2: idempotency ── re-run --apply. With the world now
        # clean, the plan must be a no-op and exit 0 without touching
        # the live .webp that survived the first run.
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = cleanup.main(["--apply", "--json"])
        parsed2 = json.loads(buf2.getvalue())
        assert rc2 == 0
        assert parsed2["summary"]["no_op"] is True, (
            f"idempotency broke: second run would still act; "
            f"deletes={parsed2['summary']['planned_deletes']} "
            f"updates={parsed2['summary']['planned_updates']}"
        )
        assert parsed2["summary"]["planned_deletes"] == 0
        assert parsed2["summary"]["planned_updates"] == 0
        assert live.is_file(), "live .webp must remain intact after no-op re-run"
        # Refresh from the second session's commit to confirm nothing
        # was orphaned by side effects from a no-op re-run.
        db_session.expire_all()
        refreshed_second = (
            db_session.query(models.CmsMediaItem)
            .filter_by(id=drift.id)
            .one()
        )
        assert refreshed_second.filename == "luis_uuid.webp"
