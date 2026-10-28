"""Frontend deployment regressions use temporary git/artifacts and fake services."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location("frontend_release", Path(__file__).parents[1] / "frontend_release.py")
frontend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frontend)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


@pytest.fixture
def layout(tmp_path):
    runtime = tmp_path / "runtime"
    front = runtime / "frontend"
    (front / "public").mkdir(parents=True)
    (front / "package.json").write_text('{"name":"test"}\n')
    (front / "package-lock.json").write_text('{"lockfileVersion":3}\n')
    (front / "public/logo.svg").write_text("<svg />\n")
    (front / "next.config.mjs").write_text("export default {old: true};\n")
    (runtime / ".gitignore").write_text("frontend/.next*/\nfrontend/.env.local\n")
    git(runtime, "init", "-q")
    git(runtime, "config", "user.email", "test@example.invalid")
    git(runtime, "config", "user.name", "Deploy Test")
    git(runtime, "add", ".")
    git(runtime, "commit", "-qm", "old deployed code")
    source = tmp_path / "source"
    git(runtime, "worktree", "add", "--detach", str(source), "HEAD")
    (source / "frontend/next.config.mjs").write_text("export default {new: true};\n")
    git(source, "commit", "-qam", "new reviewed config")
    sha = git(source, "rev-parse", "HEAD")
    git(source, "update-ref", "refs/remotes/origin/main", sha)
    for root, build_id in ((runtime, "OLD"), (source, "NEW")):
        (root / "frontend/.next").mkdir()
        (root / "frontend/.next/BUILD_ID").write_text(build_id)
        (root / "frontend/.next/server.js").write_text(build_id)
    return source, runtime, sha


def services(monkeypatch, layout):
    source, runtime, sha = layout
    events = []
    current = {"pid": 100}
    monkeypatch.setattr(frontend, "ensure_no_build_process", lambda: None)
    monkeypatch.setattr(frontend, "registered", lambda runtime: {"pid": current["pid"], "pm2_env": {"pm_cwd": str(runtime / "frontend")}})
    monkeypatch.setattr(frontend, "prepare_environment", lambda *args: ({"KEEP_OLD_BUILD": "1"}, {}))
    def build(*args):
        assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"
        assert "old" in (runtime / "frontend/next.config.mjs").read_text()
        events.append("build")
    monkeypatch.setattr(frontend, "build", build)
    def restart():
        events.append("restart")
        current["pid"] += 1
    monkeypatch.setattr(frontend, "restart", restart)
    monkeypatch.setattr(frontend, "smoke", lambda *args: events.append("smoke"))
    return events


def test_alternate_worktree_deploy_retains_live_backup_until_smoke(monkeypatch, layout):
    source, runtime, sha = layout
    events = services(monkeypatch, layout)
    def smoke(*args):
        events.append("smoke")
        assert (runtime / "frontend/.next-old/BUILD_ID").read_text() == "OLD"
        assert (runtime / "frontend/.next/BUILD_ID").read_text() == "NEW"
        assert "new" in (runtime / "frontend/next.config.mjs").read_text()
        assert "old" in (frontend.state_dir(runtime) / "rollback-config/next.config.mjs").read_text()
    monkeypatch.setattr(frontend, "smoke", smoke)
    frontend.deploy(source, runtime)
    assert events == ["build", "restart", "smoke"]
    assert not (runtime / "frontend/.next-old").exists()
    manifest = json.loads((frontend.state_dir(runtime) / "current.json").read_text())
    assert manifest["sha"] == sha
    assert manifest["build_id"] == "NEW"
    # A second deploy recognizes its own reviewed config even when runtime
    # HEAD could not advance because another module has dirty work.
    frontend.preflight(source, runtime)


def test_alternate_worktree_failure_restores_actual_runtime_artifact_and_config(monkeypatch, layout):
    source, runtime, _ = layout
    events = services(monkeypatch, layout)
    def smoke(*args):
        current = (runtime / "frontend/.next/BUILD_ID").read_text()
        events.append("smoke:" + current)
        if current == "NEW":
            raise RuntimeError("new artifact failed")
        assert "old" in (runtime / "frontend/next.config.mjs").read_text()
    monkeypatch.setattr(frontend, "smoke", smoke)
    with pytest.raises(RuntimeError, match="new artifact failed"):
        frontend.deploy(source, runtime)
    assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"
    assert (runtime / "frontend/.next/server.js").read_text() == "OLD"
    assert "old" in (runtime / "frontend/next.config.mjs").read_text()
    assert events == ["build", "restart", "smoke:NEW", "restart", "smoke:OLD"]
    assert not (frontend.state_dir(runtime) / "current.json").exists()


def test_config_local_edits_are_preserved_and_rejected_before_build(monkeypatch, layout):
    source, runtime, _ = layout
    events = services(monkeypatch, layout)
    path = runtime / "frontend/next.config.mjs"
    path.write_text("// another agent's in-progress changes\n")
    with pytest.raises(RuntimeError, match="local edits"):
        frontend.deploy(source, runtime)
    assert path.read_text() == "// another agent's in-progress changes\n"
    assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"
    assert events == []


@pytest.mark.parametrize("name", ["package.json", "package-lock.json", "public/logo.svg"])
def test_dependency_or_public_asset_mismatch_fails_before_build(monkeypatch, layout, name):
    source, runtime, _ = layout
    events = services(monkeypatch, layout)
    (runtime / "frontend" / name).write_text("unreviewed runtime difference\n")
    with pytest.raises(RuntimeError, match="differ"):
        frontend.deploy(source, runtime)
    assert events == []
    assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"


def test_build_failure_leaves_live_artifact_and_config_intact(monkeypatch, layout):
    source, runtime, _ = layout
    events = services(monkeypatch, layout)
    def build(*args):
        raise subprocess.CalledProcessError(1, ["npm", "run", "build"])
    monkeypatch.setattr(frontend, "build", build)
    with pytest.raises(subprocess.CalledProcessError):
        frontend.deploy(source, runtime)
    assert events == []
    assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"
    assert "old" in (runtime / "frontend/next.config.mjs").read_text()


def test_runtime_global_lock_prevents_another_frontend_deploy(monkeypatch, layout):
    import fcntl
    source, runtime, _ = layout
    events = services(monkeypatch, layout)
    directory = frontend.state_dir(runtime)
    directory.mkdir(parents=True)
    with (directory / "deploy.lock").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="global runtime lock"):
            frontend.deploy(source, runtime)
    assert events == []


def test_failed_promotion_restores_runtime_after_first_rename(monkeypatch, layout):
    source, runtime, _ = layout
    services(monkeypatch, layout)
    real_replace = os.replace
    def replace(before, after):
        if Path(before).name == ".next-build" and Path(after).name == ".next":
            raise OSError("promotion refused")
        return real_replace(before, after)
    monkeypatch.setattr(frontend.os, "replace", replace)
    with pytest.raises(OSError, match="promotion refused"):
        frontend.deploy(source, runtime)
    assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"
    assert "old" in (runtime / "frontend/next.config.mjs").read_text()


def test_next_lock_is_preserved_for_owner_inspection(layout):
    source, runtime, _ = layout
    (runtime / "frontend/.next-command.lock").mkdir()
    with pytest.raises(RuntimeError, match="inspect its owner"):
        frontend.preflight(source, runtime)
    assert (runtime / "frontend/.next-command.lock").is_dir()


def test_build_time_config_edits_are_preserved_and_abort_before_promotion(monkeypatch, layout):
    source, runtime, _ = layout
    events = services(monkeypatch, layout)
    def build(*args):
        events.append("build")
        (runtime / "frontend/next.config.mjs").write_text("// developer edited during build\n")
    monkeypatch.setattr(frontend, "build", build)
    with pytest.raises(RuntimeError, match="local edits"):
        frontend.deploy(source, runtime)
    assert events == ["build"]
    assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"
    assert (runtime / "frontend/next.config.mjs").read_text() == "// developer edited during build\n"


def test_frontend_build_receives_live_process_environment_and_matching_ignored_file(layout, monkeypatch):
    import sys
    source, runtime, _ = layout
    env_file = runtime / "frontend/.env.local"
    env_file.write_text("NEXT_PUBLIC_API_URL=/api\n")
    monkeypatch.setenv("API_PROXY_TARGET", "http://unrelated-build-test.invalid")
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; print('READY', flush=True); time.sleep(20)"],
        env={"PATH": os.environ["PATH"], "API_PROXY_TARGET": "http://127.0.0.1:8000"},
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert child.stdout.readline().strip() == "READY"
        env, hashes = frontend.prepare_environment(source, runtime, child.pid)
        assert env["API_PROXY_TARGET"] == "http://127.0.0.1:8000"
        assert env["KEEP_OLD_BUILD"] == "1"
        assert hashes[".env.local"] == frontend.digest(env_file)
        assert (source / "frontend/.env.local").resolve() == env_file
        assert git(source, "status", "--porcelain", "--untracked-files=all") == ""
    finally:
        child.terminate()
        child.wait(timeout=5)


def test_config_restore_failure_still_attempts_restoring_live_artifact(monkeypatch, layout):
    source, runtime, _ = layout
    events = services(monkeypatch, layout)
    actual_replace = frontend.replace_bytes
    def config_replace(path, data):
        if b"old" in data:
            raise OSError("config filesystem refused restore")
        return actual_replace(path, data)
    monkeypatch.setattr(frontend, "replace_bytes", config_replace)
    def smoke(*args):
        build_id = (runtime / "frontend/.next/BUILD_ID").read_text()
        events.append("smoke:" + build_id)
        if build_id == "NEW":
            raise RuntimeError("candidate failed")
    monkeypatch.setattr(frontend, "smoke", smoke)
    with pytest.raises(RuntimeError, match="deployment and rollback failed"):
        frontend.deploy(source, runtime)
    assert (runtime / "frontend/.next/BUILD_ID").read_text() == "OLD"
    assert (frontend.state_dir(runtime) / "rollback-config/next.config.mjs").read_text() == "export default {old: true};\n"
    assert events == ["build", "restart", "smoke:NEW", "restart", "smoke:OLD"]
