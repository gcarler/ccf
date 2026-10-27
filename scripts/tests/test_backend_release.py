"""Release safety tests use temporary repositories and fake runtime processes only."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

SPEC = importlib.util.spec_from_file_location("backend_release", Path(__file__).parents[1] / "backend_release.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


@pytest.fixture
def repo(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "release-test@example.invalid")
    git(repository, "config", "user.name", "Release Test")
    (repository / "backend").mkdir()
    (repository / "backend/main.py").write_text("# first reviewed backend\n")
    for relative in ("backend/api/chat.py", "backend/api/comments.py", "backend/api/workspace_shared/__init__.py", "backend/services/web_push.py"):
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# CCF_RUNTIME_DIR layout supported\n")
    (repository / ".gitignore").write_text(".env\nbackend/.env\nbackend/data\n")
    git(repository, "add", ".")
    git(repository, "commit", "-qm", "first")
    old_sha = git(repository, "rev-parse", "HEAD")
    (repository / "backend/main.py").write_text("# next reviewed backend\n")
    git(repository, "commit", "-qam", "next")
    new_sha = git(repository, "rev-parse", "HEAD")
    git(repository, "update-ref", "refs/remotes/origin/main", new_sha)
    return repository, old_sha, new_sha


def test_release_uses_exact_commit_and_preserves_dirty_runtime(repo, tmp_path):
    repository, old_sha, new_sha = repo
    runtime = tmp_path / "runtime"
    (runtime / "backend/data").mkdir(parents=True)
    (runtime / "backend/data/feature_flags.json").write_text('{"enabled": true}')
    (runtime / ".env").write_text("TEST_SENTINEL=private\n")
    (repository / "backend/main.py").write_text("# concurrent unreviewed edit\n")
    prepared = release.prepare_release(repository, runtime, new_sha)
    source = Path(prepared["source"])
    assert (source / "backend/main.py").read_text() == "# next reviewed backend\n"
    assert (repository / "backend/main.py").read_text() == "# concurrent unreviewed edit\n"
    assert not (source / "backend/data").exists()
    assert (source / ".env").resolve() == runtime / ".env"
    assert git(source, "status", "--porcelain", "--untracked-files=all") == ""
    (source / "backend/main.py").write_text("# dirty release\n")
    with pytest.raises(RuntimeError, match="dirty"):
        release.verify_source(source, new_sha)


def test_release_rejects_unreviewed_commit(repo, tmp_path):
    repository, _, _ = repo
    (repository / "backend/main.py").write_text("# not main\n")
    git(repository, "commit", "-qam", "unreviewed")
    unreviewed = git(repository, "rev-parse", "HEAD")
    with pytest.raises(subprocess.CalledProcessError):
        release.prepare_release(repository, tmp_path / "runtime", unreviewed)



def test_release_rejects_incompatible_state_layout_even_if_on_main(repo, tmp_path):
    repository, _, _ = repo
    (repository / "backend/api/chat.py").write_text("# older source-relative layout\n")
    git(repository, "commit", "-qam", "old state layout")
    sha = git(repository, "rev-parse", "HEAD")
    git(repository, "update-ref", "refs/remotes/origin/main", sha)
    with pytest.raises(RuntimeError, match="shared runtime layout"):
        release.prepare_release(repository, tmp_path / "runtime", sha)

def deploy_mocks(monkeypatch, tmp_path, *, existing=True):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    old = {"sha": "a" * 40, "source": str(tmp_path / "old")}
    new = {"sha": "b" * 40, "source": str(tmp_path / "new")}
    events = []
    monkeypatch.setattr(release, "command", lambda *args, **kw: new["sha"])
    monkeypatch.setattr(release, "verify_source", lambda *a: None)
    monkeypatch.setattr(release, "verify_launcher", lambda *a: None)
    monkeypatch.setattr(release, "prepare_release", lambda repo, runtime, sha: old if sha == old["sha"] else new)
    monkeypatch.setattr(release, "process_pid", lambda runtime: 100)
    monkeypatch.setattr(release, "process_config", lambda runtime: {"pid": 100, "pm2_env": {}})
    monkeypatch.setattr(release, "rebind_launcher", lambda runtime, source, config, *args: events.append("rebind:" + str(source)))
    monkeypatch.setattr(release, "process_environment", lambda pid: {})
    monkeypatch.setattr(release, "backup_database", lambda *a: events.append("backup"))
    monkeypatch.setattr(release, "smoke", lambda *a: events.append("smoke"))
    if existing:
        release.write_release(runtime, old)
    return runtime, old, new, events


def test_success_backs_up_before_pointer_and_restart(monkeypatch, tmp_path):
    runtime, old, new, events = deploy_mocks(monkeypatch, tmp_path)
    real_write = release.write_release
    def record_write(runtime, value):
        events.append("pointer")
        real_write(runtime, value)
    monkeypatch.setattr(release, "write_release", record_write)
    release.deploy(tmp_path, runtime, new["sha"], None)
    assert events == ["backup", "pointer", "rebind:" + new["source"], "smoke"]
    assert release.read_release(runtime) == new
    assert (release.state_dir(runtime) / "current.json").stat().st_mode & 0o777 == 0o600


def test_backup_failure_never_mutates_live_pointer(monkeypatch, tmp_path):
    runtime, old, new, events = deploy_mocks(monkeypatch, tmp_path)
    def broken_backup(*args):
        raise subprocess.CalledProcessError(1, ["pg_dump"])
    monkeypatch.setattr(release, "backup_database", broken_backup)
    with pytest.raises(subprocess.CalledProcessError):
        release.deploy(tmp_path, runtime, new["sha"], None)
    assert events == []
    assert release.read_release(runtime) == old


def test_failed_smoke_restores_previous_reviewed_release(monkeypatch, tmp_path):
    runtime, old, new, events = deploy_mocks(monkeypatch, tmp_path)
    def smoke(runtime, pointer, pid):
        events.append("smoke:" + pointer["sha"])
        if pointer == new:
            raise RuntimeError("failed health")
    monkeypatch.setattr(release, "smoke", smoke)
    with pytest.raises(RuntimeError, match="failed health"):
        release.deploy(tmp_path, runtime, new["sha"], None)
    assert release.read_release(runtime) == old
    assert events == ["backup", "rebind:" + new["source"], "smoke:" + new["sha"], "rebind:" + old["source"], "smoke:" + old["sha"]]


def test_first_adoption_requires_explicit_clean_rollback(monkeypatch, tmp_path):
    runtime, old, new, events = deploy_mocks(monkeypatch, tmp_path, existing=False)
    with pytest.raises(RuntimeError, match="rollback-sha"):
        release.deploy(tmp_path, runtime, new["sha"], None)
    assert events == []
    release.deploy(tmp_path, runtime, new["sha"], old["sha"])
    assert release.read_release(runtime) == new


def test_start_uses_release_source_but_runtime_cwd_and_environment(monkeypatch, repo, tmp_path):
    repository, _, sha = repo
    runtime = tmp_path / "runtime"
    (runtime / "venv/bin").mkdir(parents=True)
    (runtime / "venv/bin/uvicorn").touch()
    prepared = release.prepare_release(repository, runtime, sha)
    release.write_release(runtime, prepared)
    captured = {}
    def fake_exec(path, args, env):
        captured.update(path=path, args=args, env=env, cwd=Path.cwd())
    monkeypatch.setattr(release.os, "execve", fake_exec)
    monkeypatch.chdir(tmp_path)
    release.start(runtime)
    assert captured["cwd"] == runtime
    assert captured["args"][3] == prepared["source"]
    assert captured["env"]["PYTHONPATH"] == prepared["source"]
    assert captured["env"]["CCF_BACKEND_SOURCE_SHA"] == sha
    assert captured["env"]["CCF_RUNTIME_DIR"] == str(runtime)


def test_smoke_rejects_healthy_old_process(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    prepared = {"sha": "a" * 40, "source": "/reviewed/source"}
    monkeypatch.setattr(release, "process_pid", lambda _: 100)
    monkeypatch.setattr(release, "process_environment", lambda _: {})
    monkeypatch.setattr(release.time, "sleep", lambda _: None)
    healthy = Mock()
    monkeypatch.setattr(release, "urlopen", healthy)
    with pytest.raises(RuntimeError, match="provenance"):
        release.smoke(runtime, prepared, 100)
    healthy.assert_not_called()


def test_deployment_lock_prevents_a_second_attempt(monkeypatch, tmp_path):
    import fcntl
    runtime = tmp_path / "runtime"
    directory = release.state_dir(runtime)
    directory.mkdir(parents=True)
    fetch = Mock()
    monkeypatch.setattr(release, "command", fetch)
    with (directory / "deploy.lock").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="lock"):
            release.deploy(tmp_path, runtime, "a" * 40, None)
    fetch.assert_not_called()


def test_starter_shell_executes_reviewed_source_with_canonical_state(repo, tmp_path):
    repository, _, sha = repo
    runtime = tmp_path / "runtime"
    (runtime / "venv/bin").mkdir(parents=True)
    (runtime / "venv/bin/python").symlink_to(sys.executable)
    output = tmp_path / "started.json"
    uvicorn = runtime / "venv/bin/uvicorn"
    uvicorn.write_text(
        f"#!{sys.executable}\nimport json, os, sys\nfrom pathlib import Path\n"
        f"Path({str(output)!r}).write_text(json.dumps(dict(cwd=os.getcwd(), args=sys.argv, "
        "source=os.environ['CCF_BACKEND_SOURCE_DIR'], sha=os.environ['CCF_BACKEND_SOURCE_SHA'])))\n"
    )
    uvicorn.chmod(0o700)
    prepared = release.prepare_release(repository, runtime, sha)
    release.write_release(runtime, prepared)
    env = os.environ.copy()
    env["CCF_RUNTIME_DIR"] = str(runtime)
    subprocess.run(["bash", str(Path(__file__).parents[1] / "start_backend.sh")], env=env, check=True, cwd=tmp_path)
    started = json.loads(output.read_text())
    assert started["cwd"] == str(runtime)
    assert started["sha"] == sha
    assert started["source"] == prepared["source"]
    assert started["args"][2:4] == ["--app-dir", prepared["source"]]


def test_backup_uses_live_settings_overrides_and_keeps_password_off_argv(tmp_path):
    runtime = tmp_path / "runtime"
    (runtime / "venv/bin").mkdir(parents=True)
    (runtime / "venv/bin/python").symlink_to(sys.executable)
    source = tmp_path / "source"
    (source / "backend/core").mkdir(parents=True)
    # Exercise the real configuration class; the backup command is a local stub.
    actual_source = Path(__file__).parents[2]
    (source / "backend/core/config.py").write_text((actual_source / "backend/core/config.py").read_text())
    (source / "scripts").mkdir()
    (runtime / ".env").write_text("DATABASE_URL=postgresql+psycopg2://file_user:file_pw@localhost/file_db\n")
    result = tmp_path / "backup.json"
    stub = source / "scripts/db_backup.sh"
    stub.write_text(
        f"#!{sys.executable}\n"  # Invoked via bash, so use a Python here-document.
        f"{sys.executable} - <<'PYTHON'\nimport json, os\nfrom pathlib import Path\n"
        f"Path({str(result)!r}).write_text(json.dumps(dict(user=os.environ['DB_USER'], "
        "database=os.environ['DB_NAME'], password=os.environ['DB_PASS'], "
        "argv=Path('/proc/' + str(os.getppid()) + '/cmdline').read_text())))\nPYTHON\n"
    )
    live = {"DATABASE_URL": "postgresql+psycopg2://live_user:private-test-sentinel@localhost/live_db", "ENV": "test"}
    release.backup_database(source, runtime, live)
    saved = json.loads(result.read_text())
    assert saved["user"] == "live_user"
    assert saved["database"] == "live_db"
    assert saved["password"] == "private-test-sentinel"
    assert "private-test-sentinel" not in saved["argv"]


def test_backup_uses_runtime_dotenv_without_inheriting_deploy_shell(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    (runtime / "venv/bin").mkdir(parents=True)
    (runtime / "venv/bin/python").symlink_to(sys.executable)
    source = tmp_path / "source"
    (source / "backend/core").mkdir(parents=True)
    # Exercise the real configuration class; the backup command is a local stub.
    actual_source = Path(__file__).parents[2]
    (source / "backend/core/config.py").write_text((actual_source / "backend/core/config.py").read_text())
    (source / "scripts").mkdir()
    (runtime / ".env").write_text("DATABASE_URL=postgresql+psycopg2://file_user:file_pw@localhost/file_db\n")
    result = tmp_path / "backup.json"
    stub = source / "scripts/db_backup.sh"
    stub.write_text(
        f"#!{sys.executable}\n"  # Invoked via bash, so use a Python here-document.
        f"{sys.executable} - <<'PYTHON'\nimport json, os\nfrom pathlib import Path\n"
        f"Path({str(result)!r}).write_text(json.dumps(dict(user=os.environ['DB_USER'], "
        "database=os.environ['DB_NAME'], password=os.environ['DB_PASS'], "
        "argv=Path('/proc/' + str(os.getppid()) + '/cmdline').read_text())))\nPYTHON\n"
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://shell_user:shell_pw@localhost/unrelated_db")
    # This process gets its database from .env; it never exported DATABASE_URL.
    live = {"ENV": "test"}
    release.backup_database(source, runtime, live)
    saved = json.loads(result.read_text())
    assert saved["user"] == "file_user"
    assert saved["database"] == "file_db"
    assert saved["password"] == "file_pw"
    assert "file_pw" not in saved["argv"]


def test_runtime_layout_persists_attachments_keys_and_flags_in_shared_state(tmp_path):
    source = Path(__file__).parents[2]
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    program = '''
import asyncio, io, json, uuid
from pathlib import Path
from types import SimpleNamespace
from starlette.datastructures import UploadFile, Headers
from backend.services import web_push
from backend.api import chat, comments
from backend.api.workspace_shared import _save_workspace_config, _load_workspace_config
runtime = Path(__import__('os').environ['CCF_RUNTIME_DIR'])
web_push.load_or_create_vapid_keys()
assert (runtime / 'backend/data/vapid_keys.json').is_file()
_save_workspace_config({'features_enabled': {'release_test': True}})
assert _load_workspace_config()['features_enabled']['release_test'] is True
assert (runtime / 'backend/data/feature_flags.json').is_file()
actor = SimpleNamespace(id=uuid.uuid4())
chat.get_user_sede_id = lambda db, user: uuid.UUID('11111111-1111-4111-8111-111111111111')
def pdf():
    return UploadFile(io.BytesIO(b'%PDF-1.4\\nfixture'), filename='fixture.pdf', headers=Headers({'content-type': 'application/pdf'}))
asyncio.run(chat.upload_chat_attachment(file=pdf(), conversation_id=None, db=None, current_user=actor))
asyncio.run(comments.upload_comment_attachment(file=pdf(), current_user=actor, db=None))
assert len(list((runtime / 'static/chat_attachments').rglob('*.pdf'))) == 1
assert len(list((runtime / 'static/comment_attachments').glob('*.pdf'))) == 1
'''
    env = os.environ.copy()
    env.update(CCF_RUNTIME_DIR=str(runtime), PYTHONPATH=str(source), DATABASE_URL="sqlite://", ENV="test")
    env.pop("VAPID_PUBLIC_KEY", None)
    env.pop("VAPID_PRIVATE_KEY", None)
    subprocess.run([sys.executable, "-c", program], cwd=tmp_path, env=env, check=True, capture_output=True)


def test_starter_refuses_mutable_checkout_when_release_pointer_is_absent(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    execution = Mock()
    monkeypatch.setattr(release.os, "execve", execution)
    with pytest.raises(RuntimeError, match="No reviewed backend release pointer"):
        release.start(runtime)
    execution.assert_not_called()


def test_private_pm2_rebind_preserves_identity_environment_and_restart_policy(monkeypatch, repo, tmp_path, capsys):
    repository, _, sha = repo
    (repository / "scripts").mkdir()
    (repository / "scripts/start_backend.sh").write_text("#!/bin/sh\nexit 0\n")
    (repository / "scripts/backend_release.py").write_text("# versioned launcher helper\n")
    actual_helper = Path(__file__).parents[1] / "rebind_backend_pm2.cjs"
    (repository / "scripts/rebind_backend_pm2.cjs").write_text(actual_helper.read_text())
    git(repository, "add", "scripts")
    git(repository, "commit", "-qm", "versioned launcher")
    sha = git(repository, "rev-parse", "HEAD")
    git(repository, "update-ref", "refs/remotes/origin/main", sha)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    source = Path(release.prepare_release(repository, runtime, sha)["source"])
    directory = release.state_dir(runtime)
    directory.mkdir(parents=True)
    recorded = tmp_path / "recorded.json"
    config = {
        "name": release.PROCESS_NAME, "pm_id": 7,
        "pm_cwd": str(runtime), "pm_exec_path": str(runtime / "scripts/start_backend.sh"),
        "exec_interpreter": "/bin/bash", "max_restarts": 17, "restart_delay": 2500,
        "max_memory_restart": 2147483648, "autorestart": True,
        "env": {"DATABASE_URL": "postgresql://live:private-sentinel@localhost/live", "UNCHANGED": "yes"},
    }
    recorded.write_text(json.dumps({"config": config, "calls": []}))
    stub = tmp_path / "pm2-stub.cjs"
    stub.write_text("""
const fs = require('node:fs');
const assert = require('node:assert/strict');
const statePath = process.env.TEST_PM2_STATE;
function read() { return JSON.parse(fs.readFileSync(statePath, 'utf8')); }
module.exports = {
  connect(done) { done(null); },
  list(done) {
    const config = read().config;
    done(null, [{name: config.name, pm_id: config.pm_id, pid:123, pm2_env:config}]);
  },
  Client: {
    executeRemote(action, request, done) {
      const state = read();
      assert.equal(action, 'restartProcessId');
      assert.equal(request.id, state.config.pm_id);
      assert.deepEqual(Object.keys(request.env), ['current_conf']);
      Object.assign(state.config, request.env.current_conf);
      state.calls.push({action, id:request.id});
      fs.writeFileSync(statePath, JSON.stringify(state));
      done(null, []);
    },
  },
  disconnect() {},
};
""")
    fake_pm2 = tmp_path / "fake-pm2"
    fake_pm2.write_text(
        f"#!{sys.executable}\nimport json, sys\nfrom pathlib import Path\n"
        f"state = json.loads(Path({str(recorded)!r}).read_text())\n"
        "assert sys.argv[1] == 'jlist'\n"
        "config = state['config']\n"
        "print(json.dumps([dict(name=config['name'], pm_id=config['pm_id'], pid=123, pm2_env=config)]))\n"
    )
    fake_pm2.chmod(0o700)
    monkeypatch.setenv("CCF_PM2_BIN", str(fake_pm2))
    monkeypatch.setenv("CCF_PM2_MODULE", str(stub))
    monkeypatch.setenv("TEST_PM2_STATE", str(recorded))
    monkeypatch.setenv("DATABASE_URL", "sqlite:///unrelated-deploy-test.db")
    release.rebind_launcher(runtime, source, config)
    state = json.loads(recorded.read_text())
    rebound = state["config"]
    assert state["calls"] == [{"action": "restartProcessId", "id": 7}]
    assert rebound["pm_id"] == 7
    assert rebound["pm_exec_path"] == str(source / "scripts/start_backend.sh")
    assert rebound["pm_cwd"] == str(runtime)
    assert rebound["env"] == {**config["env"], "CCF_RUNTIME_DIR": str(runtime)}
    for key in ("max_restarts", "restart_delay", "max_memory_restart", "autorestart", "exec_interpreter"):
        assert rebound[key] == config[key]
    private_path = directory / "ecosystem.backend.json"
    assert private_path.stat().st_mode & 0o777 == 0o600
    assert release.process_config(runtime)["pm2_env"]["pm_id"] == 7
    # Reapply the same clean launcher during rollback; the old config path
    # remains an acceptable bootstrap expectation, without revisiting it.
    release.rebind_launcher(runtime, source, config)
    assert len(json.loads(recorded.read_text())["calls"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "private-sentinel" not in captured.err
    # A public configuration must fail before a daemon RPC is attempted.
    private_path.chmod(0o644)
    failed = subprocess.run(["node", str(actual_helper), str(private_path)], env=os.environ.copy(), capture_output=True, text=True)
    assert failed.returncode == 1
    assert "private-sentinel" not in failed.stdout + failed.stderr
    assert len(json.loads(recorded.read_text())["calls"]) == 2
    private_path.chmod(0o600)
    # A launcher that changed after the snapshot must not receive the RPC.
    state = json.loads(recorded.read_text())
    state["config"]["pm_exec_path"] = str(tmp_path / "unreviewed/scripts/start_backend.sh")
    recorded.write_text(json.dumps(state))
    failed = subprocess.run(["node", str(actual_helper), str(private_path)], env=os.environ.copy(), capture_output=True, text=True)
    assert failed.returncode == 1
    assert len(json.loads(recorded.read_text())["calls"]) == 2
    with pytest.raises(RuntimeError, match="outside managed"):
        release.process_config(runtime)


def test_pm2_request_rejects_other_service_and_invalid_id(tmp_path):
    helper = Path(__file__).parents[1] / "rebind_backend_pm2.cjs"
    program = """
const assert = require('node:assert/strict');
const {buildRestartRequest} = require(process.argv[1]);
for (const candidate of [
  {name:'ccf-frontend-staging',pm_id:7},
  {name:'ccf-backend-staging',pm_id:-1},
  {name:'ccf-backend-staging',pm_id:'7'},
]) {
  assert.throws(() => buildRestartRequest({...candidate, pm_exec_path:'/reviewed/scripts/start_backend.sh',pm_cwd:'/runtime'}));
}
"""
    subprocess.run(["node", "-e", program, str(helper)], check=True, capture_output=True)


def test_preflight_backup_is_verified_before_deploy_continues(monkeypatch, tmp_path):
    sha = "a" * 40
    source = tmp_path / "release"
    events = []
    monkeypatch.setattr(release.sys, "argv", ["backend_release.py", "preflight", sha, "--runtime", str(tmp_path), "--repo", str(tmp_path), "--backup"])
    monkeypatch.setattr(release, "command", lambda *a, **kw: "")
    monkeypatch.setattr(release, "prepare_deployment", lambda *a: ({}, {"source": str(source), "sha": sha}, {"pid": 100}))
    monkeypatch.setattr(release, "process_environment", lambda _: {"LIVE_PROCESS": "yes"})
    monkeypatch.setattr(release, "backup_database", lambda selected_source, runtime, env: events.append((selected_source, env)))
    assert release.main() == 0
    assert events == [(source, {"LIVE_PROCESS": "yes"})]


def test_backend_wrapper_passes_exact_sha_and_rollback_to_real_parser(tmp_path):
    runtime = tmp_path / "runtime"
    (runtime / "venv/bin").mkdir(parents=True)
    result = tmp_path / "parsed.json"
    interpreter = runtime / "venv/bin/python"
    interpreter.write_text(
        f"#!{sys.executable}\nimport importlib.util,json,sys\nfrom pathlib import Path\n"
        "helper = sys.argv[1]\nsys.argv = sys.argv[1:]\n"
        "spec = importlib.util.spec_from_file_location('release', helper)\nmodule = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(module)\n"
        f"module.deploy = lambda repo,runtime,sha,rollback: Path({str(result)!r}).write_text(json.dumps(dict(sha=sha,rollback=rollback,runtime=str(runtime))))\n"
        "raise SystemExit(module.main())\n"
    )
    interpreter.chmod(0o700)
    env = os.environ.copy()
    env["CCF_RUNTIME_DIR"] = str(runtime)
    sha, rollback = "a" * 40, "b" * 40
    subprocess.run(["bash", str(Path(__file__).parents[1] / "deploy_backend.sh"), sha, "--rollback-sha", rollback], env=env, check=True)
    assert json.loads(result.read_text()) == {"sha": sha, "rollback": rollback, "runtime": str(runtime)}
