"""Behavioral tests for CCF agent handoffs and terminal task states."""

import json
import subprocess
from pathlib import Path

import pytest

from scripts.ccf_agent_bridge import Bridge, BridgeError


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


@pytest.fixture
def bridge(tmp_path: Path) -> tuple[Bridge, str]:
    sha = make_repo(tmp_path / "repo")
    return Bridge(data_dir=tmp_path / "bridge", repo_root=tmp_path / "repo"), sha


def delivered(bridge: Bridge, event_id: str, actor: str) -> None:
    claimed = bridge.claim_pending()
    assert claimed is not None and claimed["id"] == event_id
    bridge.record_dispatch(event_id, True)
    bridge.acknowledge(event_id, actor)


def test_full_handoff_review_revision_and_done(bridge: tuple[Bridge, str]) -> None:
    store, sha = bridge
    assignment = store.assign("TKT-1", "academy", "Entrega", "Implementar UI", "codex", "agy", [])
    assert store.task("TKT-1")["status"] == "ASSIGNED"
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
    revised = store.submit("TKT-1", "codex", sha, "Accesibilidad corregida", ["evidence.txt"], ["tsc PASS"])
    with pytest.raises(BridgeError, match="confirmar recepción"):
        store.review("TKT-1", "agy", True, 100, "", "Pruebas verificadas")
    delivered(store, revised, "agy")
    with pytest.raises(BridgeError, match="Solo agy"):
        store.review("TKT-1", "codex", True, 100, "", "Pruebas verificadas")
    approved = store.review("TKT-1", "agy", True, 100, "", "Pruebas verificadas")
    assert store.task("TKT-1")["status"] == "APPROVED"
    delivered(store, approved, "codex")
    store.close("TKT-1", "agy", "Integrado y verificado")
    assert store.task("TKT-1")["status"] == "DONE"
    assert store.active_tasks() == []
    assert len(store.latest("audits", "TKT-1")["evidence"]) > 0
    store.assign("TKT-2", "academy", "Otra tarea", "Tarea siguiente", "codex", "agy", [], ["TKT-1"])


def test_no_cross_task_or_unverified_submission(bridge: tuple[Bridge, str]) -> None:
    store, sha = bridge
    assignment = store.assign("TKT-A", "academy", "A", "Primer encargo", "codex", "agy", [])
    with pytest.raises(BridgeError, match="tarea activa"):
        store.assign("TKT-B", "academy", "B", "Segundo encargo", "codex", "agy", [])
    with pytest.raises(BridgeError, match="está ocupado"):
        store.assign("TKT-C", "academy", "C", "Otro agente en el mismo árbol", "agy2", "agy", [])
    with pytest.raises(BridgeError, match="distintos"):
        store.assign("TKT-B", "academy", "B", "Segundo encargo", "agy", "agy", [])
    delivered(store, assignment, "codex")
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
    event = store.assign("TKT-N", "academy", "Notificación", "Entrega notificada", "agy2", "agy", [])
    assert store.claim_pending()["id"] == event
    store.record_dispatch(event, False, "tmux session missing")
    assert store.status()["events"]["FAILED"] == 1
    with pytest.raises(BridgeError, match="todavía no fue enviado"):
        store.acknowledge(event, "agy2")
    store.retry_event(event)
    delivered(store, event, "agy2")
    assert store.task("TKT-N")["status"] == "WORKING"
    assert store.status()["events"]["ACKED"] == 1


def test_one_dispatcher_claims_each_event(bridge: tuple[Bridge, str]) -> None:
    store, _ = bridge
    event = store.assign("TKT-Q", "academy", "Cola", "Sin duplicar envío", "agy2", "agy", [])
    assert store.claim_pending()["id"] == event
    assert store.claim_pending() is None
    store.record_dispatch(event, True)
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
