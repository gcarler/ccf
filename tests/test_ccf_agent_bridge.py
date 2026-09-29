"""Behavioral tests for CCF agent handoffs and terminal task states."""

import json
import os
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from scripts.ccf_agent_bridge import Bridge, BridgeError, build_parser, send_to_tmux


def make_repo(path: Path) -> str:
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "evidence.txt").write_text("verified work\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "evidence.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=Bridge Test", "-c", "user.email=bridge@example.test",
         "commit", "-qm", "test: evidence"], check=True,
    )
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


def make_work_commit(path: Path, filename: str = "evidence.txt") -> str:
    previous = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    (path / filename).write_text(f"work on {filename} after {previous}\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", filename], check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.name=Bridge Test", "-c", "user.email=bridge@example.test",
         "commit", "-qm", "test: work"], check=True,
    )
    return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()


@pytest.fixture
def bridge(tmp_path: Path) -> tuple[Bridge, str]:
    sha = make_repo(tmp_path / "repo")
    return Bridge(data_dir=tmp_path / "bridge", repo_root=tmp_path / "repo"), sha


def delivered(bridge: Bridge, event_id: str, actor: str) -> None:
    claimed = bridge.claim_pending()
    assert claimed is not None and claimed["id"] == event_id
    bridge.record_dispatch(event_id, claimed["claim_token"], True)
    bridge.acknowledge(event_id, actor)


def test_full_handoff_review_revision_and_done(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    assignment = store.assign("TKT-1", "academy", "Entrega", "Implementar UI", "codex", "agy", ["tsc PASS"], coordinator="freebuff")
    assert store.task("TKT-1")["status"] == "ASSIGNED"
    sha = make_work_commit(store.repo_root)
    with pytest.raises(BridgeError, match="confirme primero"):
        store.submit("TKT-1", "codex", sha, "Pantalla lista", ["evidence.txt"], ["tsc PASS"])
    delivered(store, assignment, "codex")
    submission = store.submit("TKT-1", "codex", sha, "Pantalla lista", ["evidence.txt"], ["tsc PASS"])
    with pytest.raises(BridgeError, match="confirmar recepción"):
        store.review("TKT-1", "agy", False, 80, "Corregir accesibilidad", "")
    delivered(store, submission, "agy")
    revision_notice = store.review("TKT-1", "agy", False, 80, "Corregir accesibilidad", "")
    assert store.task("TKT-1")["status"] == "REVISION_REQUIRED"
    delivered(store, revision_notice, "codex")
    with pytest.raises(BridgeError, match="commit nuevo"):
        store.submit("TKT-1", "codex", sha, "Sin cambio nuevo", ["evidence.txt"], ["tsc PASS"])
    revised_sha = make_work_commit(store.repo_root, "accessibility.txt")
    revised = store.submit("TKT-1", "codex", revised_sha, "Accesibilidad corregida", ["accessibility.txt"], ["tsc PASS"])
    with pytest.raises(BridgeError, match="confirmar recepción"):
        store.review("TKT-1", "agy", True, 100, "", "Pruebas verificadas")
    delivered(store, revised, "agy")
    with pytest.raises(BridgeError, match="Solo agy"):
        store.review("TKT-1", "codex", True, 100, "", "Pruebas verificadas")
    approved = store.review("TKT-1", "agy", True, 100, "", "Pruebas verificadas")
    assert store.task("TKT-1")["status"] == "APPROVED"
    with pytest.raises(BridgeError, match="confirmar el dictamen"):
        store.close("TKT-1", "freebuff", "Cierre prematuro")
    delivered(store, approved, "codex")
    with pytest.raises(BridgeError, match="Solo freebuff"):
        store.close("TKT-1", "agy", "Intento del auditor")
    store.close("TKT-1", "freebuff", "Integrado y verificado")
    assert store.task("TKT-1")["status"] == "DONE"
    assert store.active_tasks() == []
    assert len(store.latest("audits", "TKT-1")["evidence"]) > 0
    store.assign("TKT-2", "academy", "Otra tarea", "Tarea siguiente", "codex", "agy", ["criterio"], ["TKT-1"], coordinator="freebuff")
    assert store.task("TKT-2")["depends_on"] == ["TKT-1"]


def test_no_cross_task_or_unverified_submission(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    assignment = store.assign("TKT-A", "academy", "A", "Primer encargo", "codex", "agy", ["criterio"], coordinator="freebuff")
    with pytest.raises(BridgeError, match="tarea activa"):
        store.assign("TKT-B", "academy", "B", "Segundo encargo", "codex", "agy", ["criterio"], coordinator="freebuff")
    with pytest.raises(BridgeError, match="está ocupado"):
        store.assign("TKT-C", "academy", "C", "Otro agente en el mismo árbol", "agy2", "agy", ["criterio"], coordinator="freebuff")
    with pytest.raises(BridgeError, match="distintos"):
        store.assign("TKT-B", "academy", "B", "Segundo encargo", "agy", "agy", ["criterio"], coordinator="freebuff")
    with pytest.raises(BridgeError, match="criterios"):
        store.assign("TKT-B", "academy", "B", "Segundo encargo", "agy2", "agy", [], coordinator="freebuff")
    delivered(store, assignment, "codex")
    sha = make_work_commit(store.repo_root)
    with pytest.raises(BridgeError, match="Solo codex"):
        store.submit("TKT-A", "agy2", sha, "Trabajo", ["evidence.txt"], ["pytest PASS"])
    with pytest.raises(BridgeError, match="SHA completo"):
        store.submit("TKT-A", "codex", sha[:8], "Trabajo", ["evidence.txt"], ["pytest PASS"])
    with pytest.raises(BridgeError, match="no existe"):
        store.submit("TKT-A", "codex", "0" * 40, "Trabajo", ["evidence.txt"], ["pytest PASS"])
    assert store.task("TKT-A")["status"] == "WORKING"
    assert store.latest("submissions", "TKT-A") is None


def test_failed_transport_is_visible_and_retryable(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    event = store.assign("TKT-N", "academy", "Notificación", "Entrega notificada", "agy2", "agy", ["criterio"], coordinator="freebuff")
    claim = store.claim_pending()
    assert claim is not None and claim["id"] == event
    store.record_dispatch(event, claim["claim_token"], False, "tmux session missing")
    assert store.status()["events"]["FAILED"] == 1
    with pytest.raises(BridgeError, match="todavía no fue enviado"):
        store.acknowledge(event, "agy2")
    with pytest.raises(BridgeError, match="destinatario o coordinador"):
        store.retry_event(event, "codex")
    store.retry_event(event, "freebuff")
    delivered(store, event, "agy2")
    assert store.task("TKT-N")["status"] == "WORKING"
    assert store.status()["events"]["ACKED"] == 1


def test_delivery_failure_retries_automatically_after_backoff(bridge, monkeypatch):
    store, _ = bridge
    import scripts.ccf_agent_bridge as bridge_module

    monkeypatch.setattr(bridge_module, "RETRY_DELAYS_SECONDS", (0,))
    event_id = store.assign("TKT-RETRY", "academy", "Reintento", "Entrega", "agy2", "codex",
                            ["criterio"], coordinator="freebuff")
    first = store.claim_pending()
    assert first is not None
    store.record_dispatch(event_id, first["claim_token"], False, "tmux unavailable")
    second = store.claim_pending()
    assert second is not None and second["id"] == event_id
    assert second["attempts"] == 1
    store.record_dispatch(event_id, second["claim_token"], True)
    with store.transaction() as conn:
        conn.execute("UPDATE events SET next_attempt_at='2000-01-01T00:00:00+00:00' WHERE id=?", (event_id,))
    assert store.claim_pending() is not None


def test_ack_timeout_resends_same_event_and_late_ack_is_idempotent(bridge):
    store, _ = bridge
    event_id = store.assign("TKT-ACK-TIMEOUT", "academy", "ACK", "Reentrega", "agy2", "codex",
                            ["criterio"], coordinator="freebuff")
    first = store.claim_pending()
    assert first is not None
    store.record_dispatch(event_id, first["claim_token"], True)
    with store.transaction() as conn:
        conn.execute("UPDATE events SET next_attempt_at='2000-01-01T00:00:00+00:00' WHERE id=?", (event_id,))
    second = store.claim_pending()
    assert second is not None and second["id"] == event_id
    store.acknowledge(event_id, "agy2")
    store.record_dispatch(event_id, second["claim_token"], True)
    assert store.status()["events"]["ACKED"] == 1


def test_queue_activates_dependencies_when_owner_and_worktree_free(bridge):
    store, _ = bridge
    store.assign("TKT-DEP", "academy", "Base", "Prerequisito", "agy2", "codex",
                 ["criterio"], coordinator="freebuff")
    store.enqueue("TKT-QUEUED", "academy", "Dependiente", "Se activa sola", "agy2", "codex",
                  ["criterio"], ["TKT-DEP"], coordinator="freebuff", priority=10)
    assert store.task("TKT-QUEUED")["status"] == "QUEUED"
    assert store.activate_ready() == []
    dependency_event = store.pending_events()[0]["id"]
    delivered(store, dependency_event, "agy2")
    sha = make_work_commit(store.repo_root)
    submission = store.submit("TKT-DEP", "agy2", sha, "Listo", ["evidence.txt"], ["pass"])
    delivered(store, submission, "codex")
    approved = store.review("TKT-DEP", "codex", True, 100, "", "verificado")
    delivered(store, approved, "agy2")
    store.close("TKT-DEP", "freebuff", "Completado")
    assert store.activate_ready() == ["TKT-QUEUED"]
    assert store.task("TKT-QUEUED")["status"] == "ASSIGNED"


def test_queue_reports_cancelled_dependency_and_pause_rejects_enqueue(bridge):
    store, _ = bridge
    store.assign("TKT-CANCEL-DEP", "academy", "Base", "Cancelar", "agy2", "codex",
                 ["criterio"], coordinator="freebuff")
    store.close("TKT-CANCEL-DEP", "freebuff", "Ya no requerida", cancel=True)
    store.enqueue("TKT-BLOCKED", "academy", "Dependiente", "Esperar", "agy2", "codex",
                  ["criterio"], ["TKT-CANCEL-DEP"], coordinator="freebuff")
    assert store.activate_ready() == []
    assert "canceladas" in store.status()["queued_tasks"][0]["activation_error"]
    store.pause("agy", True)
    with pytest.raises(BridgeError, match="pausado"):
        store.enqueue("TKT-PAUSED", "academy", "Pausada", "No encolar", "agy2", "codex",
                      ["criterio"], coordinator="freebuff")


def test_dead_letter_escalates_once_to_coordinator(bridge, monkeypatch):
    store, _ = bridge
    import scripts.ccf_agent_bridge as bridge_module

    monkeypatch.setattr(bridge_module, "MAX_DELIVERY_ATTEMPTS", 1)
    event_id = store.assign("TKT-DEAD", "academy", "Escalamiento", "Reintentos", "agy2", "codex",
                            ["criterio"], coordinator="freebuff")
    claim = store.claim_pending()
    assert claim is not None
    store.record_dispatch(event_id, claim["claim_token"], False, "tmux offline")
    assert store.status()["events"]["DEAD"] == 1
    alerts = [event for event in store.pending_events() if event["kind"] == "BRIDGE_ALERT"]
    assert len(alerts) == 1 and alerts[0]["target"] == "freebuff"
    alert_claim = store.claim_pending()
    assert alert_claim is not None and alert_claim["id"] == alerts[0]["id"]
    store.record_dispatch(alert_claim["id"], alert_claim["claim_token"], False, "coordinator unavailable")
    store.escalate_dead_letters()
    with store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM events WHERE kind='BRIDGE_ALERT'").fetchone()[0] == 1


def test_daemon_heartbeat_and_health_json_argument(bridge):
    store, _ = bridge
    assert store.health()["state"] == "DEGRADED"
    store.heartbeat("test-instance")
    assert store.health()["state"] == "HEALTHY"
    assert store.status()["daemon"]["instance_id"] == "test-instance"
    assert build_parser().parse_args(["health", "--json"]).command == "health"

    event_id = store.assign("TKT-HEALTH", "academy", "Salud", "ACK vencido", "agy2", "codex",
                            ["criterio"], coordinator="freebuff")
    claim = store.claim_pending()
    assert claim is not None
    store.record_dispatch(event_id, claim["claim_token"], True)
    with store.transaction() as conn:
        conn.execute("UPDATE events SET sent_at='2000-01-01T00:00:00+00:00' WHERE id=?", (event_id,))
    assert "delivery_or_ack_overdue" in store.health()["issues"]


def test_one_dispatcher_claims_each_event(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    event = store.assign("TKT-Q", "academy", "Cola", "Sin duplicar envío", "agy2", "agy", ["criterio"], coordinator="freebuff")
    claim = store.claim_pending()
    assert claim is not None and claim["id"] == event
    assert store.claim_pending() is None
    store.record_dispatch(event, claim["claim_token"], True)
    assert store.claim_pending() is None
    store.acknowledge(event, "agy2")


def test_legacy_snapshot_is_preserved_and_can_be_cancelled(tmp_path: Path) -> None:
    data = tmp_path / "bridge"
    data.mkdir()
    task = {"id": "OLD-CLOSURE", "module": "governance", "title": "Cierre redundante", "description": "Fin"}
    (data / "current_task.json").write_text(json.dumps(task), encoding="utf-8")
    (data / "state.json").write_text(json.dumps({"status": "AWAITING_AUDIT"}), encoding="utf-8")
    (data / "last_submission.json").write_text(json.dumps({"task_id": "OLD-CLOSURE", "notes": "Sin SHA"}), encoding="utf-8")
    store = Bridge(data_dir=data, repo_root=tmp_path)
    assert store.task("OLD-CLOSURE")["legacy"] == 1
    with pytest.raises(BridgeError, match="SHA verificable"):
        store.review("OLD-CLOSURE", "agy", True, 100, "", "Revisado")
    store.close("OLD-CLOSURE", "agy", "Tarea duplicada del cierre anterior", cancel=True)
    assert store.task("OLD-CLOSURE")["status"] == "CANCELLED"
    assert json.loads((data / "state.json").read_text(encoding="utf-8"))["status"] == "AWAITING_AUDIT"


def test_submission_requires_new_commit_and_declared_changes(bridge: tuple[Bridge, str]) -> None:
    store, baseline = bridge
    event = store.assign("TKT-E", "academy", "Evidencia", "Cambio verificable", "codex", "agy", ["archivo modificado"], coordinator="freebuff")
    delivered(store, event, "codex")
    with pytest.raises(BridgeError, match="posterior"):
        store.submit("TKT-E", "codex", baseline, "Sin cambios", ["evidence.txt"], ["check"])
    sha = make_work_commit(store.repo_root)
    with pytest.raises(BridgeError, match="no fue modificado"):
        store.submit("TKT-E", "codex", sha, "Archivo falso", ["missing.ts"], ["check"])
    with pytest.raises(BridgeError, match="no fue modificado"):
        store.submit("TKT-E", "codex", sha, "Ruta inválida", ["../evidence.txt"], ["check"])
    make_work_commit(store.repo_root, "later.txt")
    with pytest.raises(BridgeError, match="HEAD actual"):
        store.submit("TKT-E", "codex", sha, "Commit anterior", ["evidence.txt"], ["check"])
    sha = make_work_commit(store.repo_root)
    store.submit("TKT-E", "codex", sha, "Cambio real", ["evidence.txt"], ["check"])


def test_stale_claim_recovers_without_aba(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    event = store.assign("TKT-L", "academy", "Lease", "Recuperar caída", "agy2", "agy", ["criterio"], coordinator="freebuff")
    first = store.claim_pending()
    assert first is not None and first["id"] == event
    with pytest.raises(BridgeError, match="FAILED o SENT"):
        store.retry_event(event, "freebuff")
    with store.transaction() as conn:
        conn.execute("UPDATE events SET claimed_at='2000-01-01T00:00:00+00:00' WHERE id=?", (event,))
    second = store.claim_pending()
    assert second is not None and second["id"] == event
    assert second["claim_token"] != first["claim_token"]
    store.record_dispatch(event, first["claim_token"], True)
    assert store.status()["events"]["SENDING"] == 1
    store.record_dispatch(event, second["claim_token"], True)
    store.acknowledge(event, "agy2")
    assert store.status()["events"]["ACKED"] == 1
    kinds = [entry["kind"] for entry in store.history("TKT-L")]
    assert "LEASE_EXPIRED" in kinds and kinds.count("DISPATCH_CLAIM") == 2


def test_parallel_schema_upgrade_is_serialized(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    with sqlite3.connect(store.db_path) as conn:
        conn.execute("DROP INDEX ix_bridge_events_status_claimed")
        conn.execute("DROP INDEX ix_bridge_events_status_created")
        conn.execute("DROP INDEX ix_bridge_tasks_owner_status")
        conn.execute("DROP INDEX ix_bridge_tasks_worktree_status")
        conn.execute("DROP INDEX ix_bridge_events_status_due")
        conn.execute("DROP INDEX ix_bridge_tasks_queue")
        conn.execute("ALTER TABLE tasks DROP COLUMN coordinator")
        conn.execute("ALTER TABLE tasks DROP COLUMN dependencies_json")
        conn.execute("ALTER TABLE tasks DROP COLUMN baseline_sha")
        conn.execute("ALTER TABLE tasks DROP COLUMN priority")
        conn.execute("ALTER TABLE tasks DROP COLUMN activation_error")
        conn.execute("ALTER TABLE events DROP COLUMN claim_token")
        conn.execute("ALTER TABLE events DROP COLUMN claimed_at")
        conn.execute("ALTER TABLE events DROP COLUMN next_attempt_at")
    def open_bridge(_: int) -> Bridge:
        return Bridge(data_dir=store.data_dir, repo_root=store.repo_root)
    with ThreadPoolExecutor(max_workers=4) as pool:
        opened = list(pool.map(open_bridge, range(8)))
    assert len(opened) == 8
    with store.connect() as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert {"coordinator", "dependencies_json", "baseline_sha", "priority", "activation_error"}.issubset(
            {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
        )
        assert {"claim_token", "claimed_at", "next_attempt_at"}.issubset(
            {row[1] for row in conn.execute("PRAGMA table_info(events)")}
        )


def test_ack_during_dispatch_is_not_lost(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    event = store.assign("TKT-FAST", "academy", "ACK rápido", "Confirmación", "agy2", "codex", ["criterio"], coordinator="agy")
    claim = store.claim_pending()
    assert claim is not None
    store.acknowledge(event, "agy2")
    store.record_dispatch(event, claim["claim_token"], True)
    assert store.status()["events"]["ACKED"] == 1
    assert store.task("TKT-FAST")["status"] == "WORKING"


def test_pause_and_retry_are_journaled(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    store.pause("agy", True)
    store.pause("agy", False)
    event = store.assign("TKT-J", "academy", "Journal", "Eventos", "agy2", "codex", ["criterio"], coordinator="agy")
    claim = store.claim_pending()
    assert claim is not None
    store.record_dispatch(event, claim["claim_token"], False, "session missing")
    store.retry_event(event, "agy")
    operations = store.status()["recent_operations"]
    assert {"PAUSE", "RESUME", "RETRY", "DISPATCH_FAILED"}.issubset({row["kind"] for row in operations})
    retry = next(row for row in operations if row["kind"] == "RETRY")
    assert retry["actor"] == "agy" and "session missing" in retry["detail"]


def test_invalid_snapshot_does_not_mark_import_complete(tmp_path: Path) -> None:
    data = tmp_path / "bridge"
    data.mkdir()
    (data / "current_task.json").write_text("{invalid", encoding="utf-8")
    with pytest.raises(BridgeError, match="snapshot JSON"):
        Bridge(data_dir=data, repo_root=tmp_path)
    (data / "current_task.json").write_text(
        json.dumps({"id": "TKT-RECOVER", "title": "Recuperado", "description": "Desde JSON"}), encoding="utf-8",
    )
    store = Bridge(data_dir=data, repo_root=tmp_path)
    assert store.task("TKT-RECOVER")["id"] == "TKT-RECOVER"


def test_tmux_dispatch_rejects_shell_and_control_text(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "%1 1 bash\n", "")
    monkeypatch.setattr(subprocess, "run", fake_run)
    event = {"id": "a" * 32, "target": "agy2", "message": "# [CCF-BRIDGE] safe"}
    assert send_to_tmux(event)[0] is False
    assert len(calls) == 1
    event["message"] = "# [CCF-BRIDGE] unsafe\ncommand"
    assert send_to_tmux(event)[0] is False
    assert len(calls) == 1


def test_permissions_do_not_change_arbitrary_existing_directory(tmp_path: Path) -> None:
    shared = tmp_path / "bridge"
    shared.mkdir(mode=0o755)
    os.chmod(shared, 0o755)
    store = Bridge(data_dir=shared, repo_root=tmp_path)
    assert shared.stat().st_mode & 0o777 == 0o755
    assert store.db_path.stat().st_mode & 0o777 == 0o600
    original_mode = tmp_path.stat().st_mode & 0o777
    with pytest.raises(BridgeError, match="directorio del puente"):
        Bridge(data_dir=tmp_path, repo_root=tmp_path / "repo")
    assert tmp_path.stat().st_mode & 0o777 == original_mode


def test_sqlite_symlink_is_rejected_without_touching_target(tmp_path: Path) -> None:
    data = tmp_path / "bridge"
    data.mkdir()
    target = tmp_path / "unrelated.txt"
    target.write_text("keep me", encoding="utf-8")
    (data / "bridge.sqlite3").symlink_to(target)
    with pytest.raises(BridgeError, match="enlace simbólico"):
        Bridge(data_dir=data, repo_root=tmp_path)
    assert target.read_text(encoding="utf-8") == "keep me"
