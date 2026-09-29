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
TMUX_AGENT_COMMANDS = {"agy": "agy", "agy2": "agy", "codex": "codex", "freebuff": "node"}


class BridgeError(Exception):
    """An invalid bridge operation; no state has been changed."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            event_columns = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
            if "claim_token" not in event_columns:
                conn.execute("ALTER TABLE events ADD COLUMN claim_token TEXT")
            if "claimed_at" not in event_columns:
                conn.execute("ALTER TABLE events ADD COLUMN claimed_at TEXT")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_events_status_created ON events(status,created_at,id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_events_status_claimed ON events(status,claimed_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_tasks_owner_status ON tasks(owner,status)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_tasks_worktree_status ON tasks(worktree,status)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_bridge_operations_task ON operations(task_id,id)")
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
        conn.execute("UPDATE tasks SET status=?, updated_at=? WHERE id=?", (new, now, task_id))
        conn.execute(
            "INSERT INTO transitions (task_id,old_status,new_status,actor,detail,created_at) VALUES (?,?,?,?,?,?)",
            (task_id, old, new, actor, detail, now),
        )

    @staticmethod
    def _operation(conn: sqlite3.Connection, kind: str, actor: str, detail: str = "",
                   task_id: str | None = None, event_id: str | None = None) -> None:
        safe_detail = "".join(" " if unicodedata.category(char) in {"Cc", "Cf", "Zl", "Zp"} else char
                              for char in detail)[:500]
        conn.execute(
            "INSERT INTO operations (task_id,event_id,kind,actor,detail,created_at) VALUES (?,?,?,?,?,?)",
            (task_id, event_id, kind, actor, safe_detail, utc_now()),
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

    def assign(self, task_id: str, module: str, title: str, description: str, owner: str,
               reviewer: str, criteria: list[str], depends_on: list[str] | None = None,
               worktree: str | None = None, coordinator: str | None = None) -> str:
        owner, reviewer = self._actor(owner), self._actor(reviewer)
        if not coordinator:
            raise BridgeError("La asignación exige un coordinador explícito")
        coordinator = self._actor(coordinator)
        if len({owner, reviewer, coordinator}) != 3:
            raise BridgeError("Coordinador, desarrollador y auditor deben ser distintos")
        if owner not in TMUX_AGENT_COMMANDS or reviewer not in TMUX_AGENT_COMMANDS:
            raise BridgeError("Desarrollador o auditor sin sesión de agente configurada para tmux")
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
        baseline = subprocess.run(
            ["git", "-C", str(worktree_path), "rev-parse", "HEAD"], capture_output=True, text=True, check=False,
        )
        if baseline.returncode != 0 or not COMMIT_RE.fullmatch(baseline.stdout.strip()):
            raise BridgeError("No se pudo fijar el HEAD base del ticket")
        with self.transaction() as conn:
            if conn.execute("SELECT 1 FROM meta WHERE key='paused' AND value='1'").fetchone():
                raise BridgeError("El puente está pausado; no admite nuevas asignaciones")
            if conn.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                raise BridgeError(f"El ID {task_id} ya existe")
            active = conn.execute(
                f"SELECT id FROM tasks WHERE owner=? AND status IN ({','.join('?' for _ in OPEN_STATUSES)}) LIMIT 1",
                (owner, *OPEN_STATUSES),
            ).fetchone()
            if active:
                raise BridgeError(f"{owner} ya tiene la tarea activa {active['id']}")
            workspace_owner = conn.execute(
                f"SELECT id,owner FROM tasks WHERE worktree=? AND status IN ({','.join('?' for _ in OPEN_STATUSES)}) LIMIT 1",
                (str(worktree_path), *OPEN_STATUSES),
            ).fetchone()
            if workspace_owner:
                raise BridgeError(
                    f"El worktree {worktree_path} está ocupado por {workspace_owner['owner']} ({workspace_owner['id']})"
                )
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
                 str(worktree_path), baseline.stdout.strip(), "ASSIGNED", 0, 0, now, now),
            )
            self._transition(conn, task_id, None, "ASSIGNED", coordinator, "Task assigned")
            return self._queue(conn, task_id, owner, "TASK_ASSIGNED",
                               f"Nueva tarea. Worktree: {worktree_path}. "
                               f"Leer: python3 /root/ccf/scripts/ccf_agent_bridge.py get-task --id {task_id}. "
                               f"Entregar: submit --id {task_id} --actor {owner} --commit <SHA40> --files <rutas> "
                               "--check '<verificación>' --notes '<resumen>'")

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
            if event["status"] not in ("SENT", "SENDING"):
                raise BridgeError("El evento todavía no fue enviado; no se puede confirmar")
            conn.execute("UPDATE events SET status='ACKED', acked_at=? WHERE id=?", (utc_now(), event_id))
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
                if task["status"] not in OPEN_STATUSES:
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
                "SELECT id,task_id,target,kind,status,created_at,sent_at,last_error FROM events "
                "WHERE status IN ('SENT','FAILED','SENDING') ORDER BY created_at LIMIT 20"
            ).fetchall()
            return {
                "paused": bool(paused and paused[0] == "1"),
                "active_tasks": self.active_tasks(),
                "events": {row["status"]: row["count"] for row in events},
                "events_needing_attention": [dict(row) for row in attention],
                "recent_operations": [dict(row) for row in conn.execute(
                    "SELECT id,task_id,event_id,kind,actor,detail,created_at FROM operations ORDER BY id DESC LIMIT 20"
                ).fetchall()],
            }

    def history(self, task_id: str) -> list[dict]:
        with closing(self.connect()) as conn:
            self._task(conn, task_id)
            return [dict(row) for row in conn.execute(
                "SELECT id,task_id,event_id,kind,actor,detail,created_at FROM operations "
                "WHERE task_id=? ORDER BY id", (task_id,),
            ).fetchall()]

    def pending_events(self) -> list[dict]:
        with closing(self.connect()) as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM events WHERE status='PENDING' ORDER BY created_at, id"
            ).fetchall()]

    def claim_pending(self) -> dict | None:
        """Claim an event with a lease; expired claims can be delivered again."""
        with self.transaction() as conn:
            cutoff = (datetime.now(timezone.utc) - timedelta(seconds=CLAIM_LEASE_SECONDS)).isoformat()
            expired = conn.execute(
                "SELECT id,task_id FROM events WHERE status='SENDING' AND (claimed_at IS NULL OR claimed_at<?)",
                (cutoff,),
            ).fetchall()
            for stale in expired:
                conn.execute(
                    "UPDATE events SET status='PENDING', claim_token=NULL, claimed_at=NULL, "
                    "last_error='Delivery lease expired; retrying' WHERE id=?", (stale["id"],),
                )
                self._operation(conn, "LEASE_EXPIRED", "bridge", task_id=stale["task_id"], event_id=stale["id"])
            row = conn.execute(
                "SELECT * FROM events WHERE status='PENDING' ORDER BY created_at, id LIMIT 1"
            ).fetchone()
            if not row:
                return None
            token = uuid.uuid4().hex
            conn.execute(
                "UPDATE events SET status='SENDING', claim_token=?, claimed_at=?, attempts=attempts+1 WHERE id=?",
                (token, utc_now(), row["id"]),
            )
            self._operation(conn, "DISPATCH_CLAIM", "bridge", f"attempt={row['attempts'] + 1}",
                            task_id=row["task_id"], event_id=row["id"])
            result = dict(row)
            result["claim_token"] = token
            return result

    def record_dispatch(self, event_id: str, claim_token: str, success: bool, error: str = "") -> None:
        with self.transaction() as conn:
            row = conn.execute("SELECT task_id,status,claim_token FROM events WHERE id=?", (event_id,)).fetchone()
            if not row or row["status"] != "SENDING" or row["claim_token"] != claim_token:
                return
            conn.execute(
                "UPDATE events SET status=?, claim_token=NULL, claimed_at=NULL, sent_at=?, last_error=? WHERE id=?",
                ("SENT" if success else "FAILED", utc_now() if success else None, error or None, event_id),
            )
            self._operation(conn, "DISPATCH_SENT" if success else "DISPATCH_FAILED", "bridge", error,
                            task_id=row["task_id"], event_id=event_id)

    def retry_event(self, event_id: str, actor: str) -> None:
        actor = self._actor(actor)
        with self.transaction() as conn:
            row = conn.execute("SELECT task_id,target,status,last_error FROM events WHERE id=?", (event_id,)).fetchone()
            if not row or row["status"] not in ("FAILED", "SENT"):
                raise BridgeError("Solo se puede reenviar un evento FAILED o SENT sin ACK")
            task = self._task(conn, row["task_id"])
            if actor not in {row["target"], task["coordinator"] or task["reviewer"], "agy"}:
                raise BridgeError("Solo el destinatario o coordinador puede reintentar este evento")
            self._operation(conn, "RETRY", actor, f"previous={row['status']}; error={row['last_error'] or ''}",
                            task_id=row["task_id"], event_id=event_id)
            conn.execute("UPDATE events SET status='PENDING', last_error=NULL WHERE id=?", (event_id,))


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
        ["tmux", "send-keys", "-t", pane_id, "C-m"],
    )
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, str(exc)
        if result.returncode != 0:
            return False, result.stderr.strip() or f"tmux exit={result.returncode}"
    return True, ""


def daemon(bridge: Bridge, interval: float = 1.0, once: bool = False) -> None:
    while True:
        while event := bridge.claim_pending():
            success, error = send_to_tmux(event)
            bridge.record_dispatch(event["id"], event["claim_token"], success, error)
            print(f"{utc_now()} {event['id']} {event['target']} {'SENT' if success else 'FAILED'} {error}", flush=True)
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
    p = sub.add_parser("assign")
    for arg in ("id", "module", "title", "desc"):
        p.add_argument(f"--{arg}", required=True)
    p.add_argument("--owner", default="agy2")
    p.add_argument("--reviewer", required=True)
    p.add_argument("--actor", required=True, help="Coordinador distinto del owner y reviewer")
    p.add_argument("--worktree", help="Raíz Git exclusiva para este ticket; por defecto, el repo actual")
    p.add_argument("--criteria", required=True)
    p.add_argument("--depends-on", action="append", default=[])
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
        elif command in ("pause", "resume"):
            bridge.pause(args.actor, paused=command == "pause")
            result = bridge.status()
        elif command == "status" or command == "init":
            result = bridge.status()
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
        return 0
    except BridgeError as exc:
        print(f"[bridge-error] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
