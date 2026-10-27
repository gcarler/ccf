#!/usr/bin/env python3
"""Build reviewed frontend source and atomically deploy its artifact to PM2 cwd."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

NAME = "ccf-frontend-staging"
CONFIG_NAMES = ("next.config.mjs", "next.config.js", "next.config.ts")
ENV_NAMES = (".env", ".env.local", ".env.production", ".env.production.local")


def command(*args: str) -> str:
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()


def state_dir(runtime: Path) -> Path:
    return runtime.parent / f"{runtime.name}-runtime" / "frontend"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(directory: Path) -> dict[str, str]:
    result = {}
    if directory.exists():
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise RuntimeError("Public asset symlinks require a separate reviewed rollout")
            if path.is_file():
                result[str(path.relative_to(directory))] = digest(path)
    return result


def registered(runtime: Path) -> dict:
    entries = json.loads(command(os.environ.get("CCF_PM2_BIN", "pm2"), "jlist"))
    matches = [entry for entry in entries if entry.get("name") == NAME]
    if len(matches) != 1 or Path(matches[0]["pm2_env"]["pm_cwd"]).resolve() != runtime / "frontend":
        raise RuntimeError("Exactly one frontend PM2 process must use the canonical frontend cwd")
    if int(matches[0].get("pid") or 0) <= 0:
        raise RuntimeError("Frontend PM2 process must be running before deploy")
    return matches[0]


def preflight(source: Path, runtime: Path) -> tuple[str, dict[str, bytes]]:
    sha = command("git", "-C", str(source), "rev-parse", "HEAD")
    command("git", "-C", str(source), "merge-base", "--is-ancestor", sha, "origin/main")
    if command("git", "-C", str(source), "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Frontend build source must be clean")
    if source == runtime:
        raise RuntimeError("Use a separate clean frontend worktree; the served artifact must survive build failure")
    front, live = source / "frontend", runtime / "frontend"
    for name in ("package.json", "package-lock.json"):
        if not (front / name).is_file() or not (live / name).is_file() or digest(front / name) != digest(live / name):
            raise RuntimeError("Frontend dependency manifests differ; deploy dependencies in a separate reviewed rollout")
    if tree_digest(front / "public") != tree_digest(live / "public"):
        raise RuntimeError("Frontend public assets differ; an explicit reviewed assets rollout is required")
    source_configs = {name for name in CONFIG_NAMES if (front / name).is_file()}
    live_configs = {name for name in CONFIG_NAMES if (live / name).is_file()}
    if source_configs != live_configs:
        raise RuntimeError("Next config filenames changed; an explicit runtime configuration rollout is required")
    manifest_path = state_dir(runtime) / "current.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    config_backups = {}
    for name in live_configs:
        if (live / name).is_symlink():
            raise RuntimeError("Runtime Next config symlinks require a separate reviewed rollout")
        current = (live / name).read_bytes()
        committed = subprocess.run(["git", "-C", str(runtime), "show", f"HEAD:frontend/{name}"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        known_hash = manifest.get("config_hashes", {}).get(name)
        if current != committed and digest(live / name) != known_hash:
            raise RuntimeError("Next config contains local edits; preserving it and refusing deploy")
        config_backups[name] = current
    for path in (front / ".next-command.lock", live / ".next-command.lock"):
        if path.exists():
            raise RuntimeError("A Next command lock exists; inspect its owner before another build")
    return sha, config_backups


def ensure_no_build_process() -> None:
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            args = [part.decode() for part in (entry / "cmdline").read_bytes().split(b"\0") if part]
        except (OSError, UnicodeError):
            continue
        if not args:
            continue
        binary = Path(args[0]).name
        node_build = binary in {"node", "nodejs"} and (
            any(Path(arg).name == "build-safe.mjs" for arg in args[1:])
            or (any(Path(arg).name == "next" for arg in args[1:]) and "build" in args[1:])
            or (any(Path(arg).name == "npm-cli.js" for arg in args[1:]) and args[-2:] == ["run", "build"])
        )
        if node_build or args[0] == "npm run build":
            raise RuntimeError("Another frontend build is running; preserve its process and lock")


def prepare_environment(source: Path, runtime: Path, pid: int) -> tuple[dict[str, str], dict[str, str]]:
    env = dict(part.decode().split("=", 1) for part in Path(f"/proc/{pid}/environ").read_bytes().split(b"\0") if b"=" in part)
    fingerprints = {}
    for name in ENV_NAMES:
        target = runtime / "frontend" / name
        copy = source / "frontend" / name
        if target.is_file():
            if command("git", "-C", str(source), "ls-files", "--", f"frontend/{name}"):
                raise RuntimeError("Frontend environment configuration must be ignored state")
            command("git", "-C", str(source), "check-ignore", f"frontend/{name}")
            if copy.exists() or copy.is_symlink():
                if not copy.is_symlink() or copy.resolve() != target.resolve():
                    raise RuntimeError("Frontend release has an unexpected environment file")
            else:
                copy.symlink_to(target)
            fingerprints[name] = digest(target)
        elif copy.exists() or copy.is_symlink():
            raise RuntimeError("Frontend release environment differs from the runtime")
    env["KEEP_OLD_BUILD"] = "1"
    env["CI"] = "1"
    return env, fingerprints


def build(source: Path, runtime: Path, env: dict[str, str]) -> None:
    log_path = state_dir(runtime) / "build.log"
    with log_path.open("w") as log:
        os.chmod(log_path, 0o600)
        # This affects dependency hook installation only. Existing repository
        # commit/push hooks and all CI gates remain enabled.
        install_env = {**env, "HUSKY": "0"}
        subprocess.run(["npm", "ci", "--legacy-peer-deps", "--include=dev"], cwd=source / "frontend", env=install_env, check=True, stdout=log, stderr=log)
        for package in ("next", "react", "react-dom"):
            expected = json.loads((source / "frontend/node_modules" / package / "package.json").read_text())["version"]
            installed = json.loads((runtime / "frontend/node_modules" / package / "package.json").read_text())["version"]
            if expected != installed:
                raise RuntimeError("Runtime Next/React dependencies differ from the reviewed lockfile installation")
        subprocess.run(["npm", "run", "build"], cwd=source / "frontend", env=env, check=True, stdout=log, stderr=log)


def replace_bytes(path: Path, data: bytes) -> None:
    # Unique staging files preserve any preexisting work by another operator.
    descriptor, temporary_name = tempfile.mkstemp(prefix=".next-config-deploy-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def restart() -> None:
    command(os.environ.get("CCF_PM2_BIN", "pm2"), "restart", NAME)


def smoke(runtime: Path, prior_pid: int) -> None:
    port = int(os.environ.get("FRONTEND_PORT", "3000"))
    for _ in range(15):
        try:
            if int(registered(runtime)["pid"]) != prior_pid:
                with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                    if response.status == 200:
                        return
        except (RuntimeError, OSError, ValueError, subprocess.CalledProcessError):
            pass
        time.sleep(1)
    raise RuntimeError("Frontend did not pass a new-process HTTP 200 smoke")


def deploy(source: Path, runtime: Path) -> None:
    directory = state_dir(runtime)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (directory / "deploy.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another frontend deployment holds the global runtime lock") from exc
        sha, configs = preflight(source, runtime)
        ensure_no_build_process()
        process = registered(runtime)
        pid = int(process["pid"])
        env, env_hashes = prepare_environment(source, runtime, pid)
        build(source, runtime, env)
        # Build scripts may generate files; source/config checks must still hold.
        if preflight(source, runtime)[1] != configs:
            raise RuntimeError("Runtime Next configuration changed during build")
        if env_hashes != {name: digest(runtime / "frontend" / name) for name in env_hashes}:
            raise RuntimeError("Runtime frontend environment changed during build")
        front = runtime / "frontend"
        staged = front / ".next-build"
        live = front / ".next"
        backup = front / ".next-old"
        if staged.exists() or staged.is_symlink() or backup.exists() or backup.is_symlink():
            raise RuntimeError("Live frontend staging/rollback artifact already exists; preserve it for review")
        if live.is_symlink() or not (live / "BUILD_ID").is_file() or not (source / "frontend/.next/BUILD_ID").is_file():
            raise RuntimeError("Both current and candidate frontend must have a valid build artifact")
        try:
            shutil.copytree(source / "frontend/.next", staged)
        except BaseException:
            if staged.exists():
                shutil.rmtree(staged)
            raise
        pid = int(registered(runtime)["pid"])
        build_id = (staged / "BUILD_ID").read_text().strip()
        previous_manifest = (directory / "current.json").read_bytes() if (directory / "current.json").exists() else None
        rollback_configs = directory / "rollback-config"
        rollback_configs.mkdir(exist_ok=True, mode=0o700)
        for name, data in configs.items():
            path = rollback_configs / name
            path.write_bytes(data)
            os.chmod(path, 0o600)
        promoted = False
        try:
            for name in configs:
                replace_bytes(front / name, (source / "frontend" / name).read_bytes())
            os.replace(live, backup)
            promoted = True
            os.replace(staged, live)
            restart()
            smoke(runtime, pid)
            manifest = {"sha": sha, "build_id": build_id, "config_hashes": {name: digest(front / name) for name in configs}}
            temporary = directory / "current.json.new"
            temporary.write_text(json.dumps(manifest))
            os.chmod(temporary, 0o600)
            os.replace(temporary, directory / "current.json")
        except BaseException:
            rollback_errors = []
            for name, data in configs.items():
                try:
                    replace_bytes(front / name, data)
                except Exception as error:
                    rollback_errors.append(error)
            if promoted:
                try:
                    if live.exists():
                        shutil.rmtree(live)
                    os.replace(backup, live)
                    restart()
                    smoke(runtime, pid)
                except Exception as error:
                    rollback_errors.append(error)
            if previous_manifest is not None:
                try:
                    (directory / "current.json").write_bytes(previous_manifest)
                except Exception as error:
                    rollback_errors.append(error)
            if rollback_errors:
                raise RuntimeError("Frontend deployment and rollback failed; inspect preserved artifact/config backups") from rollback_errors[0]
            raise
        finally:
            if staged.exists():
                shutil.rmtree(staged)
        # The actual runtime backup survives until the live smoke succeeds.
        shutil.rmtree(backup)
        print(f"Frontend artifact {build_id} deployed from reviewed SHA {sha}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, default=Path("/root/ccf"))
    args = parser.parse_args()
    try:
        deploy(args.source.resolve(), args.runtime.resolve())
        return 0
    except RuntimeError as exc:
        print(f"Frontend deploy failed: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("Frontend deploy failed; inspect private build log and preserved rollback artifacts", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
