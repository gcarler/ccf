#!/usr/bin/env python3
"""Deploy a reviewed backend commit without using the mutable runtime checkout."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

PROCESS_NAME = "ccf-backend-staging"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


def command(*args: str, env: dict[str, str] | None = None) -> str:
    return subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env).stdout.strip()


def state_dir(runtime: Path) -> Path:
    return runtime.parent / f"{runtime.name}-runtime" / "backend"


def read_release(runtime: Path) -> dict[str, str] | None:
    pointer = state_dir(runtime) / "current.json"
    return json.loads(pointer.read_text()) if pointer.exists() else None


def write_release(runtime: Path, release: dict[str, str]) -> None:
    directory = state_dir(runtime)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = directory / "current.json.new"
    with temporary.open("w") as stream:
        os.chmod(temporary, 0o600)
        json.dump(release, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, directory / "current.json")


def verify_source(source: Path, sha: str) -> None:
    if not SHA_PATTERN.fullmatch(sha):
        raise RuntimeError("A full lowercase commit SHA is required")
    if command("git", "-C", str(source), "rev-parse", "HEAD") != sha:
        raise RuntimeError("Release HEAD does not match its recorded SHA")
    if command("git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Release source is dirty; refusing to load it")
    if not (source / "backend" / "main.py").is_file():
        raise RuntimeError("Release has no backend entrypoint")


def prepare_release(repo: Path, runtime: Path, sha: str) -> dict[str, str]:
    if not SHA_PATTERN.fullmatch(sha):
        raise RuntimeError("A full lowercase commit SHA is required")
    command("git", "-C", str(repo), "merge-base", "--is-ancestor", sha, "origin/main")
    source = runtime.parent / f"{runtime.name}-releases" / "backend" / sha
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        command("git", "-C", str(repo), "worktree", "add", "--detach", str(source), sha)
    verify_source(source, sha)
    # Older source-relative layouts would detach VAPID/workspace state and
    # attachments on rollback. They cannot be safe release targets here.
    runtime_paths = (
        "backend/api/chat.py", "backend/api/comments.py",
        "backend/api/workspace_shared/__init__.py", "backend/services/web_push.py",
    )
    if any(not (source / path).is_file() or "CCF_RUNTIME_DIR" not in (source / path).read_text() for path in runtime_paths):
        raise RuntimeError("Release does not support the shared runtime layout; choose a compatible rollback SHA")
    # These locations are deliberately ignored state, never tracked source.
    # In particular root/static contains tracked assets and must not be replaced.
    for relative in (".env", "backend/.env"):
        target = runtime / relative
        link = source / relative
        if not target.exists():
            continue
        tracked = command("git", "-C", str(source), "ls-files", "--", relative)
        if tracked:
            raise RuntimeError(f"Shared state unexpectedly tracked: {relative}")
        command("git", "-C", str(source), "check-ignore", relative)
        if link.is_symlink() and link.resolve() == target.resolve():
            continue
        if link.exists() or link.is_symlink():
            raise RuntimeError(f"Unexpected release state at {relative}")
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=target.is_dir())
    verify_source(source, sha)
    return {"sha": sha, "source": str(source)}


def pm2_binary() -> str:
    return os.environ.get("CCF_PM2_BIN", "pm2")


def process_config(runtime: Path) -> dict:
    entries = json.loads(command(pm2_binary(), "jlist"))
    matches = [entry for entry in entries if entry.get("name") == PROCESS_NAME]
    if len(matches) != 1:
        raise RuntimeError("Exactly one backend process must already be registered with PM2")
    process = matches[0]
    config = process["pm2_env"]
    launcher = Path(config["pm_exec_path"]).resolve()
    canonical_launcher = runtime / "scripts" / "start_backend.sh"
    if launcher != canonical_launcher:
        source = launcher.parent.parent
        sha = source.name
        managed = runtime.parent / f"{runtime.name}-releases" / "backend" / sha
        if source != managed or launcher != source / "scripts" / "start_backend.sh":
            raise RuntimeError("PM2 entrypoint is outside managed backend releases")
        verify_source(source, sha)
        command("git", "-C", str(source), "merge-base", "--is-ancestor", sha, "origin/main")
    if Path(config["pm_cwd"]).resolve() != runtime:
        raise RuntimeError("PM2 cwd differs from the canonical runtime")
    pid = int(process.get("pid") or 0)
    if pid <= 0:
        raise RuntimeError("Backend PM2 process is not running")
    return process


def process_pid(runtime: Path) -> int:
    return int(process_config(runtime)["pid"])


def verify_launcher(source: Path) -> None:
    files = (source / "scripts/start_backend.sh", source / "scripts/backend_release.py", source / "scripts/rebind_backend_pm2.cjs")
    if any(not path.is_file() for path in files):
        raise RuntimeError("Release has no complete versioned backend launcher/helper for rollback")
    command("bash", "-n", str(files[0]))
    command(sys.executable, "-c", "import pathlib,sys; compile(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[1], 'exec')", str(files[1]))
    command("node", "--check", str(files[2]))


def rebind_launcher(runtime: Path, source: Path, config: dict, expected_launcher: Path | None = None) -> None:
    """Update only this PM2 app, preserving its env and supervision policy."""
    launcher = source / "scripts" / "start_backend.sh"
    verify_launcher(source)
    # Keep the snapshot private; only the specific native restart RPC can
    # change pm_exec_path on an existing PM2 app without deleting its pm_id.
    updated = dict(config)
    updated.update(pm_exec_path=str(launcher), pm_cwd=str(runtime))
    updated["env"] = {**config.get("env", {}), "CCF_RUNTIME_DIR": str(runtime)}
    path = state_dir(runtime) / "ecosystem.backend.json"
    with path.open("w") as stream:
        os.chmod(path, 0o600)
        expected = [config.get("pm_exec_path")]
        if expected_launcher is not None:
            expected.append(str(expected_launcher))
        json.dump({"apps": [updated], "expected_exec_paths": expected}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    command("node", str(source / "scripts" / "rebind_backend_pm2.cjs"), str(path))


def process_environment(pid: int) -> dict[str, str]:
    return dict(item.decode().split("=", 1) for item in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0") if b"=" in item)


def backup_database(source: Path, runtime: Path, process_env: dict[str, str]) -> None:
    # Settings resolves .env with exactly the currently running process's
    # environment overrides. No credential is printed or passed on argv.
    program = '''
import os, subprocess, sys
from pathlib import Path
from sqlalchemy.engine import make_url
sys.path.insert(0, sys.argv[1])
from backend.core.config import Settings
runtime = Path(sys.argv[2])
settings = Settings(_env_file=str(runtime / ".env"))
url = make_url(settings.database_url)
if url.get_backend_name() != "postgresql":
    raise SystemExit("Backend deploy backup requires PostgreSQL")
env = os.environ.copy()
env.update(DB_HOST=url.host or "127.0.0.1", DB_PORT=str(url.port or 5432),
           DB_USER=url.username or "", DB_NAME=url.database or "", DB_PASS=url.password or "",
           BACKUP_DIR=sys.argv[3])
subprocess.run(["bash", sys.argv[1] + "/scripts/db_backup.sh"], env=env, check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
'''
    # The deploy shell may target another database. Only the live process's
    # exported settings may override runtime/.env for this backup.
    env = dict(process_env)
    env["PYTHONPATH"] = str(source)
    python = runtime / "venv" / "bin" / "python"
    subprocess.run([str(python), "-c", program, str(source), str(runtime), str(state_dir(runtime) / "backups")],
                   check=True, env=env, cwd=runtime, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def smoke(runtime: Path, release: dict[str, str], previous_pid: int) -> None:
    port = int(os.environ.get("BACKEND_PORT", "8000"))
    for _ in range(20):
        try:
            pid = process_pid(runtime)
            env = process_environment(pid)
            if pid != previous_pid and env.get("CCF_BACKEND_SOURCE_SHA") == release["sha"] and env.get("CCF_BACKEND_SOURCE_DIR") == release["source"]:
                if Path(f"/proc/{pid}/cwd").resolve() != runtime:
                    raise RuntimeError("Backend runtime cwd changed")
                with urlopen(f"http://127.0.0.1:{port}/healthz", timeout=2) as response:
                    if response.status == 200:
                        return
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError):
            pass
        time.sleep(1)
    raise RuntimeError("Backend failed release provenance or HTTP 200 smoke")


def prepare_deployment(repo: Path, runtime: Path, sha: str, rollback_sha: str | None) -> tuple[dict[str, str], dict[str, str], dict]:
    old = read_release(runtime)
    if old is None:
        if not rollback_sha:
            raise RuntimeError("First deployment requires --rollback-sha with a reviewed stable commit")
        old = prepare_release(repo, runtime, rollback_sha)
    else:
        confirmed = prepare_release(repo, runtime, old["sha"])
        if old != confirmed:
            raise RuntimeError("Previous release pointer does not match the managed release path")
    new = prepare_release(repo, runtime, sha)
    verify_launcher(Path(old["source"]))
    verify_launcher(Path(new["source"]))
    registered = process_config(runtime)
    return old, new, registered


def deploy(repo: Path, runtime: Path, sha: str | None, rollback_sha: str | None) -> None:
    directory = state_dir(runtime)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "deploy.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another backend deployment holds the lock") from exc
        command("git", "-C", str(repo), "fetch", "origin", "main")
        sha = sha or command("git", "-C", str(repo), "rev-parse", "origin/main")
        old, new, registered = prepare_deployment(repo, runtime, sha, rollback_sha)
        pid = int(registered["pid"])
        backup_database(Path(new["source"]), runtime, process_environment(pid))
        print(f"Verified database backup; deploying backend SHA {sha}", flush=True)
        # All preparation and the backup finish before the first live mutation.
        try:
            write_release(runtime, new)
            rebind_launcher(runtime, Path(new["source"]), registered["pm2_env"])
            smoke(runtime, new, pid)
            command(pm2_binary(), "save")
        except BaseException:
            try:
                write_release(runtime, old)
                rebind_launcher(runtime, Path(old["source"]), registered["pm2_env"], Path(new["source"]) / "scripts/start_backend.sh")
                smoke(runtime, old, pid)
                command(pm2_binary(), "save")
            except Exception as rollback_error:
                raise RuntimeError("Deploy and rollback failed; inspect PM2 logs") from rollback_error
            raise
        print(f"Backend HTTP 200 and process provenance verified: {sha}")


def start(runtime: Path) -> None:
    release = read_release(runtime)
    if release is None:
        raise RuntimeError("No reviewed backend release pointer; run the deployment helper before starting")
    source = Path(release["source"])
    verify_source(source, release["sha"])
    uvicorn = runtime / "venv" / "bin" / "uvicorn"
    if not uvicorn.is_file():
        raise RuntimeError("Runtime venv has no uvicorn executable")
    os.chdir(runtime)
    env = os.environ.copy()
    env.update(PYTHONPATH=str(source), ENV_FILE=str(runtime / "backend" / ".env"), CCF_RUNTIME_DIR=str(runtime),
               CCF_BACKEND_SOURCE_DIR=str(source), CCF_BACKEND_SOURCE_SHA=release["sha"])
    os.execve(str(uvicorn), [str(uvicorn), "backend.main:app", "--app-dir", str(source),
                           "--host", "127.0.0.1", "--port", os.environ.get("BACKEND_PORT", "8000")], env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("start", "deploy", "preflight"))
    parser.add_argument("sha", nargs="?")
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--rollback-sha")
    parser.add_argument("--backup", action="store_true", help="Verify a database backup during preflight")
    args = parser.parse_args()
    try:
        if args.operation == "start":
            start(args.runtime.resolve())
        elif args.operation == "preflight":
            command("git", "-C", str(args.repo.resolve()), "fetch", "origin", "main")
            sha = args.sha or command("git", "-C", str(args.repo.resolve()), "rev-parse", "origin/main")
            _, new, process = prepare_deployment(args.repo.resolve(), args.runtime.resolve(), sha, args.rollback_sha)
            if args.backup:
                backup_database(Path(new["source"]), args.runtime.resolve(), process_environment(int(process["pid"])))
            print("Backend source, launcher, rollback and PM2 preflight passed")
        else:
            deploy(args.repo.resolve(), args.runtime.resolve(), args.sha, args.rollback_sha)
        return 0
    except RuntimeError as exc:
        print(f"Backend release operation failed: {exc}", file=sys.stderr)
        return 1
    except (subprocess.CalledProcessError, OSError, ValueError):
        # Child process diagnostics can contain a database URL or PM2 env.
        # Keep those private; the step/exit code still fails closed.
        print("Backend release operation failed; verify source, backup, PM2 configuration and private logs", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
