#!/usr/bin/env python3
"""Durable, per-ticket coordination for the CCF agent bridge.

The SQLite database is the authority. Legacy JSON files are imported once and
left untouched as a rollback snapshot. Tmux is only a notification transport;
agents acknowledge events explicitly before the bridge treats them as received.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unicodedata
import uuid
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRIDGE_DIR = REPO_ROOT / ".bridge"
OPEN_STATUSES = ("ASSIGNED", "WORKING", "AWAITING_AUDIT", "REVISION_REQUIRED", "APPROVED")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ACTOR_RE = re.compile(r"^[a-zA-Z0-9_-]{2,40}$")
TASK_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,100}$")
CLAIM_LEASE_SECONDS = 60
ACK_TIMEOUT_SECONDS = 120
MAX_DELIVERY_ATTEMPTS = 6
HEARTBEAT_INTERVAL_SECONDS = 5
HEARTBEAT_STALE_SECONDS = 20
RETRY_DELAYS_SECONDS = (5, 15, 45, 120, 300)
BACKUP_INTERVAL_SECONDS = 24 * 60 * 60
BACKUP_STALE_SECONDS = BACKUP_INTERVAL_SECONDS + 2 * 60 * 60
BACKUP_RETENTION = 14
TASK_STALE_SECONDS = 7 * 24 * 60 * 60
TMUX_AGENT_COMMANDS = {"agy": "agy", "agy2": "agy", "codex": "codex", "freebuff": "node"}
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)(\b(?:password|passwd|secret|token|api[_-]?key|authorization)\b\s*[:=]\s*)([^\s,;]+)"
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")


class BridgeError(Exception):
    """An invalid bridge operation; no state has been changed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_detail(value: str) -> str:
    """Redact common credential forms before they reach persistent audit records or logs."""
    redacted = BEARER_RE.sub("Bearer [REDACTED]", value)
    redacted = SECRET_ASSIGNMENT_RE.sub(r"\1[REDACTED]", redacted)
    redacted = JWT_RE.sub("[REDACTED_JWT]", redacted)
    return "".join(" " if unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} else char
                   for char in redacted)[:500]


def after_seconds(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def read_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise BridgeError(f"Snapshot JSON inválido: {path}")
        return data
    except (OSError, ValueError) as exc:
        raise BridgeError(f"No se pudo importar el snapshot JSON {path}: {exc}") from exc


class Bridge:
    def __init__(self, data_dir: Path | None = None, repo_root: Path | None = None):
        self.data_dir = data_dir or Path(os.environ.get("CCF_BRIDGE_DIR", DEFAULT_BRIDGE_DIR))
        self.repo_root = repo_root or REPO_ROOT
        canonical_dir = (self.repo_root / ".bridge").resolve()
        if self.data_dir.name not in {".bridge", "bridge"} or self.data_dir.is_symlink() or self.data_dir.resolve() in {
            Path("/"), Path("/root"), self.repo_root.resolve(),
        }:
            raise BridgeError("El directorio del puente debe ser propio y no un symlink ni una raíz amplia")
        existed = self.data_dir.exists()
        self.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not existed or self.data_dir.resolve() == canonical_dir:
            os.chmod(self.data_dir, 0o700)
        self.db_path = self.data_dir / "bridge.sqlite3"
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        if self.db_path.is_symlink():
            raise BridgeError("La base SQLite del puente no puede ser un enlace simbólico")
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        with closing(self.connect()) as conn, conn:
            try:
                db_fd = os.open(self.db_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            except OSError as exc:
                raise BridgeError(f"No se pudo asegurar la base SQLite del puente: {exc}") from exc
            try:
                os.fchmod(db_fd, 0o600)
            finally:
                os.close(db_fd)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("BEGIN IMMEDIATE")
            schema = """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    module TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    criteria_json TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    coordinator TEXT,
                    dependencies_json TEXT NOT NULL DEFAULT '[]',
                    worktree TEXT NOT NULL,
                    baseline_sha TEXT,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL DEFAULT 0,
                    activation_error TEXT,
                    revision INTEGER NOT NULL DEFAULT 0,
                    legacy INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    revision INTEGER NOT NULL,
                    author TEXT NOT NULL,
                    commit_sha TEXT,
                    notes TEXT NOT NULL,
                    files_json TEXT NOT NULL,
                    checks_json TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    UNIQUE(task_id, revision)
                );
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    revision INTEGER NOT NULL,
                    reviewer TEXT NOT NULL,
                    verdict TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    findings TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    audited_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    revision INTEGER NOT NULL,
                    target TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    message TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    acked_at TEXT,
                    claim_token TEXT,
                    claimed_at TEXT,
                    next_attempt_at TEXT,
                    last_error TEXT
                );
                CREATE TABLE IF NOT EXISTS transitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id),
                    old_status TEXT,
                    new_status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT REFERENCES tasks(id),
                    event_id TEXT REFERENCES events(id),
                    kind TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
            for statement in schema.split(";"):
                if statement.strip():
                    conn.execute(statement)
            task_columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
            if "worktree" not in task_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN worktree TEXT")
                conn.execute("UPDATE tasks SET worktree=? WHERE worktree IS NULL", (str(self.repo_root.resolve()),))
            if "coordinator" not in task_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN coordinator TEXT")
            if "dependencies_json" not in task_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN dependencies_json TEXT NOT NULL DEFAULT '[]'")
            if "baseline_sha" not in task_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN baseline_sha TEXT")
            if "priority" not in task_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN priority INTEGER NOT NULL DEFAULT 0")
            if "activation_error" not in task_columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN activation_error TEXT")
            event_columns = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
            if "claim_token" not in event_columns:
                conn.execute("ALTER TABLE events ADD COLUMN claim_token TEXT")
            if "claimed_at" not in event_columns:
                conn.execute("ALTER TABLE events ADD COLUMN claimed_at TEXT")
            if "next_attempt_at" not in event_columns:
                conn.execute("ALTER TABLE events ADD COLUMN next_attempt_at TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_events_status_created ON events(status,created_at,id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_events_status_claimed ON events(status,claimed_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_events_status_due ON events(status,next_attempt_at,created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_tasks_owner_status ON tasks(owner,status)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_tasks_worktree_status ON tasks(worktree,status)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_tasks_queue ON tasks(status,priority,created_at,id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_operations_task ON operations(task_id,id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_events_task ON events(task_id,id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_audits_task ON audits(task_id,id)")
        self._import_legacy_once()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _import_legacy_once(self) -> None:
        with self.transaction() as conn:
            if conn.execute("SELECT 1 FROM meta WHERE key='legacy_imported'").fetchone():
                return
            task = read_json(self.data_dir / "current_task.json")
            state = read_json(self.data_dir / "state.json")
            if task.get("id"):
                status = state.get("status", "DEV_WORKING")
                status = {
                    "DEV_WORKING": "WORKING", "AUDITING": "AWAITING_AUDIT",
                    "IDLE": "CANCELLED", "APPROVED": "APPROVED",
                }.get(status, status)
                if status not in (*OPEN_STATUSES, "DONE", "CANCELLED"):
                    status = "WORKING"
                task_id = str(task["id"])
                submission = read_json(self.data_dir / "last_submission.json")
                has_submission = submission.get("task_id") == task_id
                revision = 1 if has_submission else 0
                now = utc_now()
                conn.execute(
                    "INSERT OR IGNORE INTO tasks "
                    "(id,module,title,description,criteria_json,owner,reviewer,worktree,status,revision,legacy,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (task_id, task.get("module") or "unknown", task.get("title") or task_id,
                     task.get("description") or "", json.dumps(task.get("acceptance_criteria") or []),
                     "agy2", "agy", str(self.repo_root.resolve()), status, revision, 1,
                     task.get("assigned_at") or now, now),
                )
                if has_submission:
                    conn.execute(
                        "INSERT OR IGNORE INTO submissions (task_id,revision,author,commit_sha,notes,files_json,checks_json,submitted_at) VALUES (?,?,?,?,?,?,?,?)",
                        (task_id, revision, submission.get("submitted_by") or "agy2", None,
                         submission.get("notes") or "", json.dumps(submission.get("files_modified") or []),
                         "[]", submission.get("submitted_at") or now),
                    )
                self._transition(conn, task_id, None, status, "migration", "Imported legacy JSON snapshot")
            conn.execute("INSERT INTO meta VALUES ('legacy_imported', ?)", (utc_now(),))

    @staticmethod
    def _actor(actor: str) -> str:
        if not ACTOR_RE.fullmatch(actor):
            raise BridgeError("Actor inválido")
        return actor

    @staticmethod
    def _task(conn: sqlite3.Connection, task_id: str) -> sqlite3.Row:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise BridgeError(f"Tarea desconocida: {task_id}")
        return row

    @staticmethod
    def _transition(conn: sqlite3.Connection, task_id: str, old: str | None, new: str, actor: str, detail: str) -> None:
        now = utc_now()
        detail = safe_detail(detail)
        conn.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?", (new, now, task_id))
        conn.execute(
            "INSERT INTO transitions (task_id,old_status,new_status,actor,detail,created_at) VALUES (?,?,?,?,?,?)",
            (task_id, old, new, actor, detail, now),
        )

    @staticmethod
    def _operation(conn: sqlite3.Connection, kind: str, actor: str, detail: str = "",
                   task_id: str | None = None, event_id: str | None = None) -> None:
        conn.execute(
            "INSERT INTO operations (task_id,event_id,kind,actor,detail,created_at) VALUES (?,?,?,?,?,?)",
            (task_id, event_id, kind, actor, safe_detail(detail), utc_now()),
        )

    @staticmethod
    def _queue(conn: sqlite3.Connection, task_id: str, target: str, kind: str, text: str,
               revision: int = 0) -> str:
        event_id = uuid.uuid4().hex
        raw_message = (
            f"[CCF-BRIDGE] {kind} {task_id}: {text} | "
            f"ack: python3 /root/ccf/scripts/ccf_agent_bridge.py ack --event {event_id} --actor {target}"
        )
        message = "# " + "".join(
            " " if unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} else char
            for char in raw_message
        )
        conn.execute(
            "INSERT INTO events (id,task_id,revision,target,kind,message,created_at) VALUES (?,?,?,?,?,?,?)",
            (event_id, task_id, revision, target, kind, message, utc_now()),
        )
        return event_id

    def verify_commit(self, sha: str, worktree: Path, baseline: str | None, files: list[str]) -> str:
        sha = sha.lower()
        if not COMMIT_RE.fullmatch(sha):
            raise BridgeError("--commit exige SHA completo de 40 caracteres")
        result = subprocess.run(
            ["git", "-C", str(worktree), "cat-file", "-t", sha],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0 or result.stdout.strip() != "commit":
            raise BridgeError(f"El commit {sha} no existe en este repositorio")
        tip = subprocess.run(
            ["git", "-C", str(worktree), "rev-parse", "HEAD"], capture_output=True, text=True, check=False,
        )
        if tip.returncode != 0 or tip.stdout.strip() != sha:
            raise BridgeError("El commit entregado debe ser el HEAD actual del worktree asignado")
        if subprocess.run(
            ["git", "-C", str(worktree), "merge-base", "--is-ancestor", sha, "HEAD"], check=False,
        ).returncode != 0:
            raise BridgeError("El commit no pertenece a la rama actual del worktree asignado")
        if baseline and (sha == baseline or subprocess.run(
            ["git", "-C", str(worktree), "merge-base", "--is-ancestor", baseline, sha], check=False,
        ).returncode != 0):
            raise BridgeError("El commit debe ser posterior al HEAD registrado al asignar el ticket")
        changed = subprocess.run(
            ["git", "-C", str(worktree), "diff-tree", "--root", "--first-parent", "--no-commit-id", "--name-only", "-r", sha],
            capture_output=True, text=True, check=False,
        )
        if changed.returncode != 0:
            raise BridgeError("No se pudieron comprobar los archivos del commit")
        changed_files = set(changed.stdout.splitlines())
        for file in files:
            path = PurePosixPath(file)
            if path.is_absolute() or ".." in path.parts or str(path) != file or file not in changed_files:
                raise BridgeError(f"El archivo declarado no fue modificado por el commit: {file}")
        return sha

    def _task_spec(self, task_id: str, title: str, description: str, owner: str,
                   reviewer: str, criteria: list[str], worktree: str | None,
                   coordinator: str | None) -> tuple[str, str, str, Path]:
        owner, reviewer = self._actor(owner), self._actor(reviewer)
        if not coordinator:
            raise BridgeError("La asignación exige un coordinador explícito")
        coordinator = self._actor(coordinator)
        if len({owner, reviewer, coordinator}) != 3:
            raise BridgeError("Coordinador, desarrollador y auditor deben ser distintos")
        if any(actor not in TMUX_AGENT_COMMANDS for actor in (owner, reviewer, coordinator)):
            raise BridgeError("Coordinador, desarrollador o auditor sin sesión de agente configurada para tmux")
        if not TASK_ID_RE.fullmatch(task_id) or not title.strip() or not description.strip():
            raise BridgeError("ID, título y descripción son obligatorios")
        if not criteria or any(not criterion.strip() for criterion in criteria):
            raise BridgeError("La asignación exige criterios de aceptación verificables")
        worktree_path = Path(worktree or self.repo_root).resolve()
        if not worktree_path.is_dir():
            raise BridgeError(f"Worktree inexistente: {worktree_path}")
        git_check = subprocess.run(
            ["git", "-C", str(worktree_path), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        )
        if git_check.returncode != 0 or Path(git_check.stdout.strip()).resolve() != worktree_path:
            raise BridgeError(f"La ruta no es raíz de un worktree Git: {worktree_path}")
        return owner, reviewer, coordinator, worktree_path

    @staticmethod
    def _head(worktree_path: Path) -> str:
        baseline = subprocess.run(
            ["git", "-C", str(worktree_path), "rev-parse", "HEAD"], capture_output=True, text=True, check=False,
        )
        if baseline.returncode != 0 or not COMMIT_RE.fullmatch(baseline.stdout.strip()):
            raise BridgeError("No se pudo fijar el HEAD base del ticket")
        return baseline.stdout.strip()

    @staticmethod
    def _active_conflicts(conn: sqlite3.Connection, owner: str, worktree_path: Path) -> tuple[str | None, str | None]:
        active = conn.execute(
            f"SELECT id FROM tasks WHERE owner=? AND status IN ({','.join('?' for _ in OPEN_STATUSES)}) LIMIT 1",
            (owner, *OPEN_STATUSES),
        ).fetchone()
        workspace_owner = conn.execute(
            f"SELECT id FROM tasks WHERE worktree=? AND status IN ({','.join('?' for _ in OPEN_STATUSES)}) LIMIT 1",
            (str(worktree_path), *OPEN_STATUSES),
        ).fetchone()
        return (active["id"] if active else None, workspace_owner["id"] if workspace_owner else None)

    @staticmethod
    def _assignment_event(conn: sqlite3.Connection, task_id: str, owner: str, worktree_path: Path) -> str:
        return Bridge._queue(
            conn, task_id, owner, "TASK_ASSIGNED",
            f"Nueva tarea. Worktree: {worktree_path}. "
            f"Leer: python3 /root/ccf/scripts/ccf_agent_bridge.py get-task --id {task_id}. "
            f"Entregar: submit --id {task_id} --actor {owner} --commit <SHA40> --files <rutas> "
            "--check '<verificación>' --notes '<resumen>'",
        )

    def _escalate_dead_event(self, conn: sqlite3.Connection, event_id: str, task_id: str,
                             target: str, kind: str) -> None:
        if kind == "BRIDGE_ALERT":
            return
        alert = conn.execute(
            "SELECT created_at FROM operations WHERE event_id=? AND kind='DEAD_LETTER_ALERT' "
            "ORDER BY id DESC LIMIT 1", (event_id,),
        ).fetchone()
        retry = conn.execute(
            "SELECT created_at FROM operations WHERE event_id=? AND kind='RETRY' "
            "ORDER BY id DESC LIMIT 1", (event_id,),
        ).fetchone()
        if alert and (not retry or alert["created_at"] >= retry["created_at"]):
            return
        task = self._task(conn, task_id)
        coordinator = task["coordinator"] or task["reviewer"]
        if coordinator == target:
            coordinator = next(agent for agent in TMUX_AGENT_COMMANDS if agent != target)
        alert_id = self._queue(
            conn, task_id, coordinator, "BRIDGE_ALERT",
            f"El aviso {event_id} ({kind}) agotó sus reintentos. Revisar status y get-history --id {task_id}.",
            task["revision"],
        )
        self._operation(conn, "DEAD_LETTER_ALERT", "bridge", f"alert={alert_id}",
                        task_id=task_id, event_id=event_id)

    def escalate_dead_letters(self) -> None:
        with self.transaction() as conn:
            dead = conn.execute(
                "SELECT id,task_id,target,kind FROM events WHERE status='DEAD' ORDER BY created_at,id"
            ).fetchall()
            for event in dead:
                self._escalate_dead_event(conn, event["id"], event["task_id"],
                                          event["target"], event["kind"])

    def assign(self, task_id: str, module: str, title: str, description: str, owner: str,
               reviewer: str, criteria: list[str], depends_on: list[str] | None = None,
               worktree: str | None = None, coordinator: str | None = None) -> str:
        owner, reviewer, coordinator, worktree_path = self._task_spec(
            task_id, title, description, owner, reviewer, criteria, worktree, coordinator,
        )
        baseline = self._head(worktree_path)
        with self.transaction() as conn:
            if conn.execute("SELECT 1 FROM meta WHERE key='paused' AND value='1'").fetchone():
                raise BridgeError("El puente está pausado; no admite nuevas asignaciones")
            if conn.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                raise BridgeError(f"El ID {task_id} ya existe")
            active, workspace_owner = self._active_conflicts(conn, owner, worktree_path)
            if active:
                raise BridgeError(f"{owner} ya tiene la tarea activa {active}")
            if workspace_owner:
                raise BridgeError(f"El worktree {worktree_path} está ocupado por {workspace_owner}")
            for dependency in depends_on or []:
                dep = self._task(conn, dependency)
                if dep["status"] != "DONE":
                    raise BridgeError(f"Dependencia {dependency} aún no está DONE")
            now = utc_now()
            conn.execute(
                "INSERT INTO tasks "
                "(id,module,title,description,criteria_json,owner,reviewer,coordinator,dependencies_json,worktree,baseline_sha,status,revision,legacy,created_at,updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (task_id, module, title, description, json.dumps(criteria), owner, reviewer, coordinator,
                 json.dumps(depends_on or []),
                 str(worktree_path), baseline, "ASSIGNED", 0, 0, now, now),
            )
            self._transition(conn, task_id, None, "ASSIGNED", coordinator, "Task assigned")
            return self._assignment_event(conn, task_id, owner, worktree_path)

    def enqueue(self, task_id: str, module: str, title: str, description: str, owner: str,
                reviewer: str, criteria: list[str], depends_on: list[str] | None = None,
                worktree: str | None = None, coordinator: str | None = None, priority: int = 0) -> None:
        owner, reviewer, coordinator, worktree_path = self._task_spec(
            task_id, title, description, owner, reviewer, criteria, worktree, coordinator,
        )
        if not 0 <= priority <= 100:
            raise BridgeError("La prioridad debe estar entre 0 y 100")
        dependencies = depends_on or []
        if len(set(dependencies)) != len(dependencies) or task_id in dependencies:
            raise BridgeError("Dependencias repetidas o autorreferencia")
        with self.transaction() as conn:
            if conn.execute("SELECT 1 FROM meta WHERE key='paused' AND value='1'").fetchone():
                raise BridgeError("El puente está pausado; no admite nuevas tareas en cola")
            if conn.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                raise BridgeError(f"El ID {task_id} ya existe")
            for dependency in dependencies:
                self._task(conn, dependency)
            now = utc_now()
            conn.execute(
                "INSERT INTO tasks "
                "(id,module,title,description,criteria_json,owner,reviewer,coordinator,dependencies_json,worktree,"
                "status,priority,revision,legacy,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (task_id, module, title, description, json.dumps(criteria), owner, reviewer, coordinator,
                 json.dumps(dependencies), str(worktree_path), "QUEUED", priority, 0, 0, now, now),
            )
            self._transition(conn, task_id, None, "QUEUED", coordinator, "Task enqueued")
            self._operation(conn, "ENQUEUED", coordinator, f"priority={priority}", task_id=task_id)

    def activate_ready(self) -> list[str]:
        """Activate ready queued tasks atomically, respecting owner and worktree ownership."""
        activated: list[str] = []
        with self.transaction() as conn:
            if conn.execute("SELECT 1 FROM meta WHERE key='paused' AND value='1'").fetchone():
                return activated
            queued = conn.execute(
                "SELECT * FROM tasks WHERE status='QUEUED' ORDER BY priority DESC,created_at,id"
            ).fetchall()
            for task in queued:
                dependency_rows = [self._task(conn, dependency)
                                   for dependency in json.loads(task["dependencies_json"])]
                terminal_dependencies = [row["id"] for row in dependency_rows
                                         if row["status"] in {"CANCELLED"}]
                if terminal_dependencies:
                    message = f"Dependencias canceladas: {', '.join(terminal_dependencies)}"
                    if task["activation_error"] != message:
                        conn.execute("UPDATE tasks SET activation_error=?,updated_at=? WHERE id=?",
                                     (message, utc_now(), task["id"]))
                        self._operation(conn, "ACTIVATION_BLOCKED", "bridge", message, task_id=task["id"])
                    continue
                if any(row["status"] != "DONE" for row in dependency_rows):
                    continue
                worktree_path = Path(task["worktree"])
                if any(self._active_conflicts(conn, task["owner"], worktree_path)):
                    continue
                try:
                    if not worktree_path.is_dir() or subprocess.run(
                        ["git", "-C", str(worktree_path), "rev-parse", "--show-toplevel"],
                        capture_output=True, text=True, check=False,
                    ).stdout.strip() != str(worktree_path):
                        raise BridgeError("Worktree no disponible o ya no es la raíz Git asignada")
                    baseline = self._head(worktree_path)
                except BridgeError as exc:
                    if task["activation_error"] != str(exc):
                        conn.execute("UPDATE tasks SET activation_error=?,updated_at=? WHERE id=?",
                                     (str(exc), utc_now(), task["id"]))
                        self._operation(conn, "ACTIVATION_BLOCKED", "bridge", str(exc), task_id=task["id"])
                    continue
                conn.execute("UPDATE tasks SET baseline_sha=?,activation_error=NULL WHERE id=?", (baseline, task["id"]))
                self._transition(conn, task["id"], "QUEUED", "ASSIGNED", "bridge", "Dependencies complete; slot available")
                event_id = self._assignment_event(conn, task["id"], task["owner"], worktree_path)
                self._operation(conn, "AUTO_ASSIGNED", "bridge", f"event={event_id}", task_id=task["id"])
                activated.append(task["id"])
        return activated

    def acknowledge(self, event_id: str, actor: str) -> None:
        actor = self._actor(actor)
        with self.transaction() as conn:
            event = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
            if not event:
                raise BridgeError("Evento desconocido")
            if event["target"] != actor:
                raise BridgeError("Este evento corresponde a otro agente")
            if event["status"] == "ACKED":
                return
            if event["status"] not in ("SENT", "SENDING") and not event["sent_at"]:
                raise BridgeError("El evento todavía no fue enviado; no se puede confirmar")
            conn.execute(
                "UPDATE events SET status='ACKED', acked_at=?,next_attempt_at=NULL,claim_token=NULL,claimed_at=NULL "
                "WHERE id=?", (utc_now(), event_id),
            )
            self._operation(conn, "ACK", actor, task_id=event["task_id"], event_id=event_id)
            task = self._task(conn, event["task_id"])
            if event["kind"] == "TASK_ASSIGNED" and task["status"] == "ASSIGNED":
                self._transition(conn, task["id"], "ASSIGNED", "WORKING", actor, "Assignment acknowledged")

    def submit(self, task_id: str, actor: str, commit: str, notes: str,
               files: list[str], checks: list[str]) -> str:
        actor = self._actor(actor)
        if not notes.strip() or not files or not checks:
            raise BridgeError("La entrega exige notas, archivos y al menos un check")
        with self.transaction() as conn:
            task = self._task(conn, task_id)
            if actor != task["owner"]:
                raise BridgeError(f"Solo {task['owner']} puede entregar esta tarea")
            if task["status"] not in ("WORKING", "REVISION_REQUIRED"):
                raise BridgeError(f"No se puede entregar desde {task['status']}; confirme primero la asignación")
            sha = self.verify_commit(commit, Path(task["worktree"]), task["baseline_sha"], files)
            previous = conn.execute(
                "SELECT commit_sha FROM submissions WHERE task_id=? ORDER BY revision DESC LIMIT 1", (task_id,),
            ).fetchone()
            if previous and previous["commit_sha"] == sha:
                raise BridgeError("Una revisión rechazada exige un commit nuevo")
            if not task["legacy"]:
                received = conn.execute(
                    "SELECT 1 FROM events WHERE task_id=? AND kind='TASK_ASSIGNED' AND status='ACKED'",
                    (task_id,),
                ).fetchone()
                if not received:
                    raise BridgeError("La asignación no tiene ACK del responsable")
            revision = task["revision"] + 1
            conn.execute(
                "INSERT INTO submissions (task_id,revision,author,commit_sha,notes,files_json,checks_json,submitted_at) VALUES (?,?,?,?,?,?,?,?)",
                (task_id, revision, actor, sha, notes.strip(), json.dumps(files), json.dumps(checks), utc_now()),
            )
            conn.execute("UPDATE tasks SET revision=? WHERE id=?", (revision, task_id))
            self._transition(conn, task_id, task["status"], "AWAITING_AUDIT", actor, f"Submitted revision {revision}: {sha}")
            return self._queue(conn, task_id, task["reviewer"], "SUBMISSION_READY",
                               f"rev {revision}, commit {sha[:12]}. Ver: python3 /root/ccf/scripts/ccf_agent_bridge.py "
                               f"get-submission --id {task_id}. Dictamen: approve --id {task_id} --actor {task['reviewer']} "
                               "--score 100 --evidence '<pruebas>' o reject --score <0-99> --findings '<hallazgos>'; "
                               "el siguiente ticket se asigna aparte",
                               revision)

    def review(self, task_id: str, actor: str, approved: bool, score: int,
               findings: str, evidence: str) -> str:
        actor = self._actor(actor)
        if approved and (score != 100 or not evidence.strip()):
            raise BridgeError("Aprobar exige --score 100 y --evidence")
        if not approved and (score < 0 or score >= 100 or not findings.strip()):
            raise BridgeError("Rechazar exige score 0-99 y hallazgos")
        with self.transaction() as conn:
            task = self._task(conn, task_id)
            if actor != task["reviewer"]:
                raise BridgeError(f"Solo {task['reviewer']} puede auditar esta tarea")
            if task["status"] != "AWAITING_AUDIT":
                raise BridgeError(f"No se puede auditar desde {task['status']}")
            submission = conn.execute(
                "SELECT * FROM submissions WHERE task_id=? AND revision=?", (task_id, task["revision"])
            ).fetchone()
            if not submission or not submission["commit_sha"]:
                raise BridgeError("Entrega sin SHA verificable; requiere nueva entrega con evidencia")
            if not task["legacy"]:
                received = conn.execute(
                    "SELECT 1 FROM events WHERE task_id=? AND revision=? AND kind='SUBMISSION_READY' AND status='ACKED'",
                    (task_id, task["revision"]),
                ).fetchone()
                if not received:
                    raise BridgeError("El auditor debe confirmar recepción de la entrega")
            new_status = "APPROVED" if approved else "REVISION_REQUIRED"
            conn.execute(
                "INSERT INTO audits (task_id,revision,reviewer,verdict,score,findings,evidence,audited_at) VALUES (?,?,?,?,?,?,?,?)",
                (task_id, task["revision"], actor, new_status, score, findings, evidence, utc_now()),
            )
            self._transition(conn, task_id, task["status"], new_status, actor, evidence or findings)
            return self._queue(conn, task_id, task["owner"], new_status,
                               f"Dictamen disponible. Ver: python3 /root/ccf/scripts/ccf_agent_bridge.py get-audit --id {task_id}",
                               task["revision"])

    def close(self, task_id: str, actor: str, resolution: str, cancel: bool = False) -> None:
        actor = self._actor(actor)
        if not resolution.strip():
            raise BridgeError("El cierre exige una razón o evidencia de integración")
        with self.transaction() as conn:
            task = self._task(conn, task_id)
            closer = task["coordinator"] or task["reviewer"]
            if actor != closer:
                raise BridgeError(f"Solo {closer} puede cerrar esta tarea")
            if cancel:
                if task["status"] not in (*OPEN_STATUSES, "QUEUED"):
                    raise BridgeError(f"No se puede cancelar desde {task['status']}")
                new_status = "CANCELLED"
            else:
                if task["status"] != "APPROVED":
                    raise BridgeError("Solo una tarea APPROVED puede pasar a DONE")
                if task["coordinator"] and not conn.execute(
                    "SELECT 1 FROM events WHERE task_id=? AND revision=? AND kind='APPROVED' AND status='ACKED'",
                    (task_id, task["revision"]),
                ).fetchone():
                    raise BridgeError("El desarrollador debe confirmar el dictamen antes del cierre")
                new_status = "DONE"
            self._transition(conn, task_id, task["status"], new_status, actor, resolution.strip())
            self._queue(conn, task_id, task["owner"], "TASK_CLOSED", f"{new_status}; consulta get-task --id {task_id}",
                        task["revision"])

    def pause(self, actor: str, paused: bool) -> None:
        if self._actor(actor) != "agy":
            raise BridgeError("Solo el coordinador agy puede pausar o reanudar")
        with self.transaction() as conn:
            conn.execute("INSERT INTO meta (key,value) VALUES ('paused',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                         ("1" if paused else "0",))
            self._operation(conn, "PAUSE" if paused else "RESUME", actor)

    def task(self, task_id: str) -> dict:
        with closing(self.connect()) as conn:
            row = self._task(conn, task_id)
            result = dict(row)
            result["acceptance_criteria"] = json.loads(result.pop("criteria_json"))
            result["depends_on"] = json.loads(result.pop("dependencies_json"))
            return result

    def active_tasks(self) -> list[dict]:
        with closing(self.connect()) as conn:
            rows = conn.execute(
                f"SELECT id,owner,reviewer,coordinator,worktree,status,revision,updated_at FROM tasks "
                f"WHERE status IN ({','.join('?' for _ in OPEN_STATUSES)}) ORDER BY updated_at DESC",
                OPEN_STATUSES,
            ).fetchall()
            return [dict(row) for row in rows]

    def latest(self, table: str, task_id: str) -> dict | None:
        if table not in {"submissions", "audits"}:
            raise BridgeError("Tabla inválida")
        with closing(self.connect()) as conn:
            row = conn.execute(f"SELECT * FROM {table} WHERE task_id=? ORDER BY id DESC LIMIT 1", (task_id,)).fetchone()
            result = dict(row) if row else None
            if result:
                for key in ("files_json", "checks_json"):
                    if key in result:
                        result[key[:-5]] = json.loads(result.pop(key))
            return result

    def status(self) -> dict:
        with closing(self.connect()) as conn:
            paused = conn.execute("SELECT value FROM meta WHERE key='paused'").fetchone()
            events = conn.execute("SELECT status,COUNT(*) AS count FROM events GROUP BY status").fetchall()
            attention = conn.execute(
                "SELECT id,task_id,target,kind,status,attempts,created_at,sent_at,claimed_at,next_attempt_at,last_error "
                "FROM events WHERE status IN ('SENT','FAILED','SENDING','DEAD') ORDER BY created_at LIMIT 20"
            ).fetchall()
            queued = conn.execute(
                "SELECT id,owner,reviewer,coordinator,worktree,priority,dependencies_json,activation_error,created_at "
                "FROM tasks WHERE status='QUEUED' ORDER BY priority DESC,created_at,id LIMIT 50"
            ).fetchall()
            stale_cutoff = (datetime.now(timezone.utc) - timedelta(seconds=TASK_STALE_SECONDS)).isoformat()
            stalled = conn.execute(
                f"SELECT id,owner,reviewer,coordinator,status,updated_at FROM tasks "
                f"WHERE status IN ({','.join('?' for _ in OPEN_STATUSES)}) AND updated_at<=? "
                "ORDER BY updated_at LIMIT 50",
                (*OPEN_STATUSES, stale_cutoff),
            ).fetchall()
            heartbeat = conn.execute("SELECT value FROM meta WHERE key='daemon_heartbeat'").fetchone()
            heartbeat_at = json.loads(heartbeat["value"])["at"] if heartbeat else None
            heartbeat_age = ((datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat_at)).total_seconds()
                             if heartbeat_at else None)
            queued_details: list[dict] = []
            for row in queued:
                item = dict(row)
                dependencies = json.loads(item.pop("dependencies_json"))
                item["depends_on"] = dependencies
                reasons = []
                owner_conflict, worktree_conflict = self._active_conflicts(
                    conn, item["owner"], Path(item["worktree"]),
                )
                if owner_conflict:
                    reasons.append("owner_busy")
                if worktree_conflict:
                    reasons.append("worktree_busy")
                waiting = [dependency for dependency in dependencies
                           if self._task(conn, dependency)["status"] != "DONE"]
                if waiting:
                    reasons.append("dependencies_waiting:" + ",".join(waiting))
                if item["activation_error"]:
                    reasons.append(item["activation_error"])
                item["blocked_by"] = reasons
                queued_details.append(item)
            return {
                "paused": bool(paused and paused[0] == "1"),
                "active_tasks": self.active_tasks(),
                "stalled_tasks": [dict(row) for row in stalled],
                "queued_tasks": queued_details,
                "events": {row["status"]: row["count"] for row in events},
                "events_needing_attention": [dict(row) for row in attention],
                "daemon": {
                    "state": "HEALTHY" if heartbeat_age is not None and heartbeat_age <= HEARTBEAT_STALE_SECONDS
                    else "STALE" if heartbeat_age is not None else "NOT_STARTED",
                    "heartbeat_at": heartbeat_at,
                    "heartbeat_age_seconds": round(heartbeat_age, 1) if heartbeat_age is not None else None,
                    "instance_id": json.loads(heartbeat["value"])["instance_id"] if heartbeat else None,
                },
                "recent_operations": [dict(row) for row in conn.execute(
                    "SELECT id,task_id,event_id,kind,actor,detail,created_at FROM operations ORDER BY id DESC LIMIT 20"
                ).fetchall()],
            }

    def health(self) -> dict:
        status = self.status()
        ack_cutoff = (datetime.now(timezone.utc) - timedelta(seconds=ACK_TIMEOUT_SECONDS)).isoformat()
        lease_cutoff = (datetime.now(timezone.utc) - timedelta(seconds=CLAIM_LEASE_SECONDS)).isoformat()
        with closing(self.connect()) as conn:
            overdue = conn.execute(
                "SELECT COUNT(*) FROM events WHERE "
                "(status='SENT' AND sent_at<=?) OR "
                "(status='SENDING' AND (claimed_at IS NULL OR claimed_at<=?))",
                (ack_cutoff, lease_cutoff),
            ).fetchone()[0]
            backup = conn.execute("SELECT value FROM meta WHERE key='bridge_backup_at'").fetchone()
            backup_file = conn.execute("SELECT value FROM meta WHERE key='bridge_backup_path'").fetchone()
        backup_at = backup["value"] if backup else None
        backup_age = ((datetime.now(timezone.utc) - datetime.fromisoformat(backup_at)).total_seconds()
                      if backup_at else None)
        backup_path = Path(backup_file["value"]) if backup_file else None
        backup_valid = False
        if backup_path and backup_path.parent == self.data_dir / "backups" and \
                not backup_path.is_symlink() and backup_path.is_file():
            try:
                with closing(sqlite3.connect(f"{backup_path.resolve().as_uri()}?mode=ro", uri=True)) as snapshot:
                    backup_valid = snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            except sqlite3.Error:
                backup_valid = False
        issues = []
        if status["daemon"]["state"] != "HEALTHY":
            issues.append(f"daemon_{status['daemon']['state'].lower()}")
        if status["events"].get("DEAD", 0):
            issues.append("dead_letters")
        if status["events"].get("FAILED", 0):
            issues.append("delivery_failures_retrying")
        if overdue:
            issues.append("delivery_or_ack_overdue")
        if status["stalled_tasks"]:
            issues.append("tasks_stalled")
        if backup_age is None or backup_age > BACKUP_STALE_SECONDS:
            issues.append("backup_stale")
        elif not backup_valid:
            issues.append("backup_unavailable_or_invalid")
        return {"state": "HEALTHY" if not issues else "DEGRADED", "issues": issues,
                "daemon": status["daemon"], "events": status["events"],
                "backup": {"state": "FRESH" if backup_age is not None and
                           backup_age <= BACKUP_STALE_SECONDS and backup_valid
                           else "STALE" if backup_age is not None else "NEVER",
                           "last_at": backup_at,
                           "age_seconds": round(backup_age, 1) if backup_age is not None else None,
                           "path": str(backup_path) if backup_path else None,
                           "integrity_ok": backup_valid},
                "attention": status["events_needing_attention"],
                "queued": len(status["queued_tasks"])}

    def escalate_stalled_tasks(self) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=TASK_STALE_SECONDS)).isoformat()
        with self.transaction() as conn:
            stalled = conn.execute(
                f"SELECT id,owner,reviewer,coordinator,status,revision,updated_at FROM tasks "
                f"WHERE status IN ({','.join('?' for _ in OPEN_STATUSES)}) AND updated_at<=?",
                (*OPEN_STATUSES, cutoff),
            ).fetchall()
            for task in stalled:
                already_alerted = conn.execute(
                    "SELECT 1 FROM operations WHERE task_id=? AND kind='TASK_STALE_ALERT' AND created_at>=? LIMIT 1",
                    (task["id"], task["updated_at"]),
                ).fetchone()
                if already_alerted:
                    continue
                coordinator = task["coordinator"] or task["reviewer"]
                event_id = self._queue(
                    conn, task["id"], coordinator, "BRIDGE_ALERT",
                    f"La tarea {task['id']} no cambia de estado desde hace siete días; revisar owner {task['owner']}.",
                    task["revision"],
                )
                self._operation(conn, "TASK_STALE_ALERT", "bridge", f"event={event_id}; updated_at={task['updated_at']}",
                                task_id=task["id"], event_id=event_id)

    def backup(self) -> dict:
        backup_dir = self.data_dir / "backups"
        if backup_dir.is_symlink():
            raise BridgeError("El directorio de respaldos no puede ser un enlace simbólico")
        backup_dir.mkdir(mode=0o700, parents=False, exist_ok=True)
        os.chmod(backup_dir, 0o700)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        destination_path = backup_dir / f"bridge-{stamp}.sqlite3"
        created_backup_file = False
        try:
            destination_fd = os.open(
                destination_path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600,
            )
            created_backup_file = True
            os.close(destination_fd)
            with closing(self.connect()) as source, closing(sqlite3.connect(destination_path)) as destination:
                source.backup(destination)
                if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise BridgeError("El respaldo SQLite no pasó integrity_check")
            backup_fd = os.open(destination_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                os.fchmod(backup_fd, 0o600)
            finally:
                os.close(backup_fd)
        except Exception:
            if created_backup_file and destination_path.exists() and not destination_path.is_symlink():
                destination_path.unlink()
            raise
        backup_at = utc_now()
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO meta (key,value) VALUES ('bridge_backup_at',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (backup_at,),
            )
            conn.execute(
                "INSERT INTO meta (key,value) VALUES ('bridge_backup_path',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(destination_path),),
            )
            self._operation(conn, "BACKUP_CREATED", "bridge", destination_path.name)
        candidates = sorted(
            path for path in backup_dir.glob("bridge-????????T????????????Z.sqlite3")
            if path.is_file() and not path.is_symlink()
        )
        for stale in candidates[:-BACKUP_RETENTION]:
            stale.unlink()
        return {"path": str(destination_path), "created_at": backup_at,
                "retained": min(len(candidates), BACKUP_RETENTION)}

    def backup_if_due(self) -> dict | None:
        with closing(self.connect()) as conn:
            last = conn.execute("SELECT value FROM meta WHERE key='bridge_backup_at'").fetchone()
        if last and (datetime.now(timezone.utc) - datetime.fromisoformat(last["value"])).total_seconds() < BACKUP_INTERVAL_SECONDS:
            return None
        return self.backup()

    def history(self, task_id: str) -> list[dict]:
        with closing(self.connect()) as conn:
            self._task(conn, task_id)
            operations = [
                {**dict(row), "record_type": "OPERATION"}
                for row in conn.execute(
                    "SELECT id,task_id,event_id,kind,actor,detail,created_at FROM operations "
                    "WHERE task_id=?", (task_id,),
                ).fetchall()
            ]
            transitions = [
                {**dict(row), "record_type": "TRANSITION", "event_id": None,
                 "kind": "STATUS_TRANSITION"}
                for row in conn.execute(
                    "SELECT id,task_id,old_status,new_status,actor,detail,created_at FROM transitions "
                    "WHERE task_id=?", (task_id,),
                ).fetchall()
            ]
            records = operations + transitions
            return sorted(records, key=lambda row: (row["created_at"], row["record_type"], row["id"]))

    def pending_events(self) -> list[dict]:
        with closing(self.connect()) as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM events WHERE status='PENDING' ORDER BY created_at, id"
            ).fetchall()]

    def heartbeat(self, instance_id: str) -> None:
        with self.transaction() as conn:
            payload = json.dumps({"at": utc_now(), "instance_id": instance_id, "pid": os.getpid()})
            conn.execute(
                "INSERT INTO meta (key,value) VALUES ('daemon_heartbeat',?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (payload,),
            )

    def claim_pending(self) -> dict | None:
        """Claim an event with a lease; expired claims can be delivered again."""
        with self.transaction() as conn:
            now = utc_now()
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=CLAIM_LEASE_SECONDS)).isoformat()
            expired = conn.execute(
                "SELECT id,task_id,attempts FROM events WHERE status='SENDING' AND (claimed_at IS NULL OR claimed_at<?)",
                (cutoff,),
            ).fetchall()
            for stale in expired:
                if stale["attempts"] >= MAX_DELIVERY_ATTEMPTS:
                    conn.execute(
                        "UPDATE events SET status='DEAD',claim_token=NULL,claimed_at=NULL,next_attempt_at=NULL,"
                        "last_error='Delivery lease expired; retry limit reached' WHERE id=?", (stale["id"],),
                    )
                    self._operation(conn, "DEAD_LETTER", "bridge", "lease expired",
                                    task_id=stale["task_id"], event_id=stale["id"])
                    event = conn.execute("SELECT target,kind FROM events WHERE id=?", (stale["id"],)).fetchone()
                    self._escalate_dead_event(conn, stale["id"], stale["task_id"],
                                              event["target"], event["kind"])
                    continue
                conn.execute(
                    "UPDATE events SET status='PENDING',claim_token=NULL,claimed_at=NULL,next_attempt_at=?,"
                    "last_error='Delivery lease expired; retrying' WHERE id=?", (now, stale["id"]),
                )
                self._operation(conn, "LEASE_EXPIRED", "bridge", task_id=stale["task_id"], event_id=stale["id"])
            overdue = conn.execute(
                "SELECT id,task_id,attempts FROM events WHERE status='SENT' AND "
                "(next_attempt_at IS NOT NULL AND next_attempt_at<=? OR "
                "next_attempt_at IS NULL AND sent_at<=?)",
                (now, (datetime.now(timezone.utc) - timedelta(seconds=ACK_TIMEOUT_SECONDS)).isoformat()),
            ).fetchall()
            for stale in overdue:
                if stale["attempts"] >= MAX_DELIVERY_ATTEMPTS:
                    conn.execute(
                        "UPDATE events SET status='DEAD',next_attempt_at=NULL,last_error='ACK timeout; retry limit reached' "
                        "WHERE id=?", (stale["id"],),
                    )
                    self._operation(conn, "DEAD_LETTER", "bridge", "ACK timeout",
                                    task_id=stale["task_id"], event_id=stale["id"])
                    event = conn.execute("SELECT target,kind FROM events WHERE id=?", (stale["id"],)).fetchone()
                    self._escalate_dead_event(conn, stale["id"], stale["task_id"],
                                              event["target"], event["kind"])
                else:
                    conn.execute(
                        "UPDATE events SET status='PENDING',next_attempt_at=?,last_error='ACK timeout; resending' "
                        "WHERE id=?", (now, stale["id"]),
                    )
                    self._operation(conn, "ACK_TIMEOUT", "bridge", task_id=stale["task_id"], event_id=stale["id"])
            row = conn.execute(
                "SELECT * FROM events WHERE status IN ('PENDING','FAILED') AND "
                "(next_attempt_at IS NULL OR next_attempt_at<=?) ORDER BY created_at,id LIMIT 1", (now,),
            ).fetchone()
            if not row:
                return None
            if row["attempts"] >= MAX_DELIVERY_ATTEMPTS:
                conn.execute("UPDATE events SET status='DEAD',next_attempt_at=NULL WHERE id=?", (row["id"],))
                self._operation(conn, "DEAD_LETTER", "bridge", "retry limit reached",
                                task_id=row["task_id"], event_id=row["id"])
                self._escalate_dead_event(conn, row["id"], row["task_id"], row["target"], row["kind"])
                return None
            token = uuid.uuid4().hex
            conn.execute(
                "UPDATE events SET status='SENDING',claim_token=?,claimed_at=?,next_attempt_at=NULL,attempts=attempts+1 "
                "WHERE id=?", (token, now, row["id"]),
            )
            self._operation(conn, "DISPATCH_CLAIM", "bridge", f"attempt={row['attempts'] + 1}",
                            task_id=row["task_id"], event_id=row["id"])
            result = dict(row)
            result["claim_token"] = token
            return result

    def record_dispatch(self, event_id: str, claim_token: str, success: bool, error: str = "") -> None:
        error = safe_detail(error)
        with self.transaction() as conn:
            row = conn.execute(
                "SELECT task_id,status,claim_token,attempts,target,kind FROM events WHERE id=?", (event_id,),
            ).fetchone()
            if not row or row["status"] != "SENDING" or row["claim_token"] != claim_token:
                return
            exhausted = not success and row["attempts"] >= MAX_DELIVERY_ATTEMPTS
            next_attempt = (after_seconds(ACK_TIMEOUT_SECONDS) if success else
                            after_seconds(RETRY_DELAYS_SECONDS[min(row["attempts"] - 1, len(RETRY_DELAYS_SECONDS) - 1)])
                            if not exhausted else None)
            conn.execute(
                "UPDATE events SET status=?,claim_token=NULL,claimed_at=NULL,"
                "sent_at=CASE WHEN ? THEN ? ELSE sent_at END,next_attempt_at=?,last_error=? WHERE id=?",
                ("SENT" if success else "DEAD" if exhausted else "FAILED", success,
                 utc_now() if success else None, next_attempt, error or None, event_id),
            )
            self._operation(conn, "DISPATCH_SENT" if success else "DISPATCH_FAILED", "bridge", error,
                            task_id=row["task_id"], event_id=event_id)
            if exhausted:
                self._operation(conn, "DEAD_LETTER", "bridge", error,
                                task_id=row["task_id"], event_id=event_id)
                self._escalate_dead_event(conn, event_id, row["task_id"], row["target"], row["kind"])

    def retry_event(self, event_id: str, actor: str) -> None:
        actor = self._actor(actor)
        with self.transaction() as conn:
            row = conn.execute("SELECT task_id,target,status,last_error FROM events WHERE id=?", (event_id,)).fetchone()
            if not row or row["status"] not in ("FAILED", "SENT", "DEAD"):
                raise BridgeError("Solo se puede reenviar un evento FAILED o SENT sin ACK, o DEAD")
            task = self._task(conn, row["task_id"])
            if actor not in {row["target"], task["coordinator"] or task["reviewer"], "agy"}:
                raise BridgeError("Solo el destinatario o coordinador puede reintentar este evento")
            self._operation(conn, "RETRY", actor, f"previous={row['status']}; error={row['last_error'] or ''}",
                            task_id=row["task_id"], event_id=event_id)
            conn.execute(
                "UPDATE events SET status='PENDING',attempts=0,next_attempt_at=NULL,last_error=NULL WHERE id=?",
                (event_id,),
            )


def send_to_tmux(event: dict) -> tuple[bool, str]:
    target = event["target"]
    expected_command = TMUX_AGENT_COMMANDS.get(target)
    if not ACTOR_RE.fullmatch(target) or not expected_command:
        return False, "Sesión tmux inválida"
    if not event["message"].startswith("# [CCF-BRIDGE]") or any(
        unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} for char in event["message"]
    ):
        return False, "Mensaje del puente inseguro para tmux"
    try:
        panes = subprocess.run(
            ["tmux", "list-panes", "-t", target, "-F", "#{pane_id} #{pane_active} #{pane_current_command}"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if panes.returncode != 0:
        return False, panes.stderr.strip() or "Sesión tmux no disponible"
    pane_rows = [line.split() for line in panes.stdout.splitlines() if line.strip()]
    active = next((row[0] for row in pane_rows if len(row) == 3 and row[1] == "1" and row[2] == expected_command), None)
    pane_id = active
    if not pane_id:
        return False, "La sesión tmux no tiene panel activo del agente esperado"
    buffer_name = f"ccf_{event['id'][:24]}"
    commands = (
        ["tmux", "set-buffer", "-b", buffer_name, "--", event["message"]],
        ["tmux", "paste-buffer", "-b", buffer_name, "-d", "-t", pane_id],
    )
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
        if result.returncode != 0:
            return False, result.stderr.strip() or f"tmux exit={result.returncode}"
    time.sleep(0.25)
    for enter_key in ("C-m", "Enter"):
        subprocess.run(["tmux", "send-keys", "-t", pane_id, enter_key], capture_output=True, text=True, timeout=5, check=False)
    return True, ""


def daemon(bridge: Bridge, interval: float = 1.0, once: bool = False) -> None:
    instance_id = uuid.uuid4().hex
    last_heartbeat = 0.0
    last_backup_check = 0.0
    last_maintenance = 0.0
    while True:
        now_monotonic = time.monotonic()
        if not once and now_monotonic - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
            bridge.heartbeat(instance_id)
            last_heartbeat = time.monotonic()
        if once or now_monotonic - last_maintenance >= HEARTBEAT_INTERVAL_SECONDS:
            bridge.activate_ready()
            bridge.escalate_dead_letters()
            bridge.escalate_stalled_tasks()
            last_maintenance = time.monotonic()
        if time.monotonic() - last_backup_check >= 60:
            try:
                backup = bridge.backup_if_due()
                if backup:
                    print(f"{utc_now()} BACKUP_CREATED {backup['path']}", flush=True)
            except (BridgeError, OSError, sqlite3.Error, ValueError) as exc:
                print(f"{utc_now()} BACKUP_FAILED {exc}", file=sys.stderr, flush=True)
            last_backup_check = time.monotonic()
        while event := bridge.claim_pending():
            success, error = send_to_tmux(event)
            bridge.record_dispatch(event["id"], event["claim_token"], success, error)
            print(f"{utc_now()} {event['id']} {event['target']} {'SENT' if success else 'FAILED'} {safe_detail(error)}", flush=True)
            if not once:
                bridge.heartbeat(instance_id)
                last_heartbeat = time.monotonic()
        if once:
            return
        time.sleep(max(interval, 0.2))


def _resolve_id(bridge: Bridge, task_id: str | None) -> str:
    if task_id:
        return task_id
    active = bridge.active_tasks()
    if len(active) != 1:
        raise BridgeError("Indique --id: hay cero o varias tareas activas")
    return active[0]["id"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Puente CCF por ticket, con ACK y auditoría independiente")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("assign", "enqueue"):
        p = sub.add_parser(name)
        for arg in ("id", "module", "title", "desc"):
            p.add_argument(f"--{arg}", required=True)
        p.add_argument("--owner", default="agy2")
        p.add_argument("--reviewer", required=True)
        p.add_argument("--actor", required=True, help="Coordinador distinto del owner y reviewer")
        p.add_argument("--worktree", help="Raíz Git exclusiva para este ticket; por defecto, el repo actual")
        p.add_argument("--criteria", required=True)
        p.add_argument("--depends-on", action="append", default=[])
        if name == "enqueue":
            p.add_argument("--priority", type=int, default=0, help="0-100; mayor prioridad primero")
    p = sub.add_parser("submit")
    for arg in ("id", "actor", "commit", "notes", "files"):
        p.add_argument(f"--{arg}", required=True)
    p.add_argument("--check", action="append", required=True)
    for name in ("approve", "reject"):
        p = sub.add_parser(name)
        p.add_argument("--id", required=True)
        p.add_argument("--actor", required=True)
        p.add_argument("--score", required=True, type=int)
        if name == "approve":
            p.add_argument("--evidence", required=True)
        else:
            p.add_argument("--findings", required=True)
    for name in ("close", "cancel"):
        p = sub.add_parser(name)
        p.add_argument("--id", required=True)
        p.add_argument("--actor", required=True)
        p.add_argument("--reason", required=True)
    p = sub.add_parser("ack")
    p.add_argument("--event", required=True)
    p.add_argument("--actor", required=True)
    for name in ("get-task", "get-submission", "get-audit"):
        sub.add_parser(name).add_argument("--id")
    sub.add_parser("status")
    sub.add_parser("health").add_argument("--json", action="store_true", help="Emitir resultado JSON (formato predeterminado)")
    sub.add_parser("backup", help="Crear y verificar un respaldo SQLite consistente")
    sub.add_parser("activate-ready")
    for name in ("pause", "resume"):
        sub.add_parser(name).add_argument("--actor", required=True)
    p = sub.add_parser("retry")
    p.add_argument("--event", required=True)
    p.add_argument("--actor", required=True)
    sub.add_parser("get-history").add_argument("--id", required=True)
    p = sub.add_parser("daemon")
    p.add_argument("--interval", "--poll-interval", type=float, default=1.0)
    p.add_argument("--once", action="store_true")
    sub.add_parser("init")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bridge = Bridge()
        command = args.command
        if command == "assign":
            event = bridge.assign(args.id, args.module, args.title, args.desc, args.owner,
                                  args.reviewer, [v.strip() for v in args.criteria.split(";") if v.strip()],
                                  args.depends_on, args.worktree, args.actor)
            result: object = {"task_id": args.id, "event_id": event, "status": "ASSIGNED"}
        elif command == "enqueue":
            bridge.enqueue(args.id, args.module, args.title, args.desc, args.owner,
                           args.reviewer, [v.strip() for v in args.criteria.split(";") if v.strip()],
                           args.depends_on, args.worktree, args.actor, args.priority)
            result = {"task_id": args.id, "status": "QUEUED"}
        elif command == "submit":
            event = bridge.submit(args.id, args.actor, args.commit, args.notes,
                                  [v.strip() for v in args.files.split(",") if v.strip()], args.check)
            result = {"task_id": args.id, "event_id": event, "status": "AWAITING_AUDIT"}
        elif command in ("approve", "reject"):
            event = bridge.review(args.id, args.actor, command == "approve", args.score,
                                  getattr(args, "findings", ""), getattr(args, "evidence", ""))
            result = {"task_id": args.id, "event_id": event, "status": "APPROVED" if command == "approve" else "REVISION_REQUIRED"}
        elif command in ("close", "cancel"):
            bridge.close(args.id, args.actor, args.reason, cancel=command == "cancel")
            result = {"task_id": args.id, "status": "DONE" if command == "close" else "CANCELLED"}
        elif command == "ack":
            bridge.acknowledge(args.event, args.actor)
            result = {"event_id": args.event, "status": "ACKED"}
        elif command == "retry":
            bridge.retry_event(args.event, args.actor)
            result = {"event_id": args.event, "status": "PENDING"}
        elif command == "get-history":
            result = bridge.history(args.id)
        elif command == "activate-ready":
            result = {"activated_tasks": bridge.activate_ready()}
        elif command in ("pause", "resume"):
            bridge.pause(args.actor, paused=command == "pause")
            result = bridge.status()
        elif command == "status" or command == "init":
            result = bridge.status()
        elif command == "health":
            result = bridge.health()
        elif command == "backup":
            try:
                result = bridge.backup()
            except (OSError, sqlite3.Error) as exc:
                raise BridgeError(f"No se pudo crear el respaldo SQLite: {exc}") from exc
        elif command == "get-task":
            result = bridge.task(_resolve_id(bridge, args.id))
        elif command == "get-submission":
            result = bridge.latest("submissions", _resolve_id(bridge, args.id))
        elif command == "get-audit":
            result = bridge.latest("audits", _resolve_id(bridge, args.id))
        elif command == "daemon":
            daemon(bridge, args.interval, args.once)
            return 0
        else:
            raise BridgeError(f"Comando no reconocido: {command}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 3 if command == "health" and result["state"] != "HEALTHY" else 0
    except BridgeError as exc:
        print(f"[bridge-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
