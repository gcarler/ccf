#!/usr/bin/env python3
"""Audit and migrate legacy chat attachment URLs.

The command is intentionally non-destructive by default. It only rewrites a
``ChatMessage.attachment_url`` when all of the following are true:

* the message belongs to a valid ``dm_<conversation_uuid>`` room;
* every conversation participant resolves to a Persona with one tenant sede;
* the URL contains a valid sede bucket and filename; and
* the physical file exists below ``static/chat_attachments``.

Ambiguous references, missing files, cross-sede conversations and external URLs
are never changed. Every report item includes the original URL so an operator
can perform a logical rollback by restoring that value if required.

Usage::

    python scripts/migrate_chat_attachment_urls.py
    python scripts/migrate_chat_attachment_urls.py --apply
    python scripts/migrate_chat_attachment_urls.py --rollback /tmp/report.json

``--apply`` is the only flag that writes to the database. The script never
removes database rows or files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

_HERE = Path(__file__).resolve()
_PROJECT_ROOT = next(
    (p for p in _HERE.parents if (p / "backend" / "__init__.py").is_file()),
    None,
)
if _PROJECT_ROOT is None:
    raise RuntimeError(f"backend package not found above {_HERE}")
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import backend.models as models  # noqa: E402
from backend.core.database import SessionLocal  # noqa: E402

_BUCKET_RE = re.compile(r"^[0-9a-fA-F-]{36}$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,254}$")
_PROTECTED_PREFIXES = ("/chat/attachments/", "/api/chat/attachments/")
_LEGACY_PREFIX = "/static/chat_attachments/"


@dataclass(frozen=True)
class AttachmentReference:
    """A syntactically valid local attachment reference."""

    kind: str
    conversation_id: uuid.UUID | None
    sede_bucket: str
    filename: str


@dataclass(frozen=True)
class ConversationBinding:
    """Tenant binding inferred from a DM conversation."""

    conversation_id: uuid.UUID
    sede_bucket: str


@dataclass
class MigrationDecision:
    message_id: str
    original_url: str
    candidate_url: str | None
    conversation_id: str | None
    sede_bucket: str | None
    filename: str | None
    reason: str
    action: str
    file_exists: bool
    applied: bool = False


def _parse_uuid(value: str | None) -> uuid.UUID | None:
    try:
        return uuid.UUID(value) if value is not None else None
    except (TypeError, ValueError, AttributeError):
        return None


def _valid_bucket(value: str) -> bool:
    return value == "_global" or bool(_BUCKET_RE.fullmatch(value))


def _valid_filename(value: str) -> bool:
    return bool(_FILENAME_RE.fullmatch(value))


def parse_attachment_reference(raw_url: str) -> tuple[AttachmentReference | None, str | None]:
    """Parse a local URL without making an authorization decision."""

    if not raw_url:
        return None, "empty_url"

    try:
        parsed = urlsplit(raw_url)
    except ValueError:
        return None, "invalid_reference"
    if parsed.scheme in {"http", "https"} or parsed.netloc:
        # Protocol-relative URLs are external references too.
        return None, "external_url"
    if parsed.scheme:
        return None, "unsupported_url_scheme"

    path = parsed.path
    if path.startswith(_LEGACY_PREFIX):
        parts = path[len(_LEGACY_PREFIX) :].split("/")
        if len(parts) != 2 or not all(parts):
            return None, "ambiguous_reference"
        sede_bucket, filename = parts
        if not _valid_bucket(sede_bucket) or not _valid_filename(filename):
            return None, "invalid_legacy_reference"
        return AttachmentReference("legacy", None, sede_bucket, filename), None

    for prefix in _PROTECTED_PREFIXES:
        if path.startswith(prefix):
            parts = path[len(prefix) :].split("/")
            if len(parts) != 3 or not all(parts):
                return None, "invalid_protected_reference"
            conversation_raw, sede_bucket, filename = parts
            conversation_id = _parse_uuid(conversation_raw)
            if conversation_id is None or not _valid_bucket(sede_bucket) or not _valid_filename(filename):
                return None, "invalid_protected_reference"
            return AttachmentReference("protected", conversation_id, sede_bucket, filename), None

    return None, "unsupported_local_reference"


def _resolve_conversation_binding(db: Any, room_id: str | None) -> tuple[ConversationBinding | None, str | None]:
    """Resolve a fail-closed, single-sede binding for a DM room."""

    if not room_id or not room_id.startswith("dm_"):
        return None, "message_not_bound_to_dm"
    conversation_id = _parse_uuid(room_id[3:])
    if conversation_id is None:
        return None, "invalid_dm_room"

    conversation = db.query(models.Conversation).filter(models.Conversation.id == conversation_id).first()
    if conversation is None:
        return None, "conversation_not_found"

    participants = (
        db.query(models.ConversationParticipant)
        .filter(models.ConversationParticipant.conversation_id == conversation_id)
        .all()
    )
    if not participants:
        return None, "conversation_without_participants"

    participant_ids = [participant.user_id for participant in participants if participant.user_id is not None]
    if len(participant_ids) != len(participants):
        return None, "participant_without_user"

    personas = db.query(models.Persona).filter(models.Persona.id.in_(participant_ids)).all()
    personas_by_id = {str(persona.id): persona for persona in personas}
    if len(personas_by_id) != len(set(str(value) for value in participant_ids)):
        return None, "participant_without_persona"

    sede_values = {getattr(personas_by_id[str(user_id)], "sede_id", None) for user_id in participant_ids}
    valid_sedes = {sede for sede in sede_values if sede is not None}
    if not valid_sedes:
        return ConversationBinding(conversation_id, "_global"), None
    if len(valid_sedes) != 1:
        return None, "cross_sede_conversation"

    # A global/superadmin participant can coexist with one tenant participant;
    # the tenant participant determines the protected storage bucket.
    return ConversationBinding(conversation_id, str(next(iter(valid_sedes)))), None


def _candidate_url(conversation_id: uuid.UUID, sede_bucket: str, filename: str) -> str:
    return f"/chat/attachments/{conversation_id}/{sede_bucket}/{filename}"


def classify_message(
    message: Any,
    db: Any,
    storage_root: Path,
    *,
    binding_resolver: Callable[[Any, str | None], tuple[ConversationBinding | None, str | None]] = _resolve_conversation_binding,
) -> MigrationDecision:
    """Classify one message and produce a safe, auditable decision."""

    raw_url = str(message.attachment_url or "")
    message_id = str(message.id)
    reference, parse_reason = parse_attachment_reference(raw_url)

    if parse_reason == "external_url":
        return MigrationDecision(message_id, raw_url, None, None, None, None, parse_reason, "preserve", False)
    if reference is None:
        return MigrationDecision(
            message_id, raw_url, None, None, None, None, parse_reason or "invalid_reference", "block", False
        )

    binding, binding_reason = binding_resolver(db, getattr(message, "room_id", None))
    conversation_id = str(binding.conversation_id) if binding else None
    candidate = (
        _candidate_url(binding.conversation_id, reference.sede_bucket, reference.filename)
        if binding
        else None
    )

    if binding is None:
        return MigrationDecision(
            message_id,
            raw_url,
            candidate,
            conversation_id,
            reference.sede_bucket,
            reference.filename,
            binding_reason or "conversation_binding_failed",
            "block",
            False,
        )

    if reference.conversation_id is not None and reference.conversation_id != binding.conversation_id:
        return MigrationDecision(
            message_id,
            raw_url,
            candidate,
            conversation_id,
            reference.sede_bucket,
            reference.filename,
            "conversation_reference_mismatch",
            "block",
            False,
        )

    if reference.sede_bucket != binding.sede_bucket:
        reason = "global_bucket_incompatible" if reference.sede_bucket == "_global" else "sede_bucket_mismatch"
        return MigrationDecision(
            message_id,
            raw_url,
            candidate,
            conversation_id,
            reference.sede_bucket,
            reference.filename,
            reason,
            "block",
            False,
        )

    storage_root = storage_root.expanduser().resolve(strict=False)
    filepath = (storage_root / reference.sede_bucket / reference.filename).resolve(strict=False)
    try:
        filepath.relative_to(storage_root)
    except ValueError:
        return MigrationDecision(
            message_id,
            raw_url,
            candidate,
            conversation_id,
            reference.sede_bucket,
            reference.filename,
            "file_outside_storage_root",
            "block",
            False,
        )

    file_exists = filepath.is_file()
    if not file_exists:
        return MigrationDecision(
            message_id,
            raw_url,
            candidate,
            conversation_id,
            reference.sede_bucket,
            reference.filename,
            "missing_file",
            "block",
            False,
        )

    if reference.kind == "protected" and raw_url == candidate:
        return MigrationDecision(
            message_id,
            raw_url,
            candidate,
            conversation_id,
            reference.sede_bucket,
            reference.filename,
            "already_protected",
            "skip",
            True,
        )

    reason = "legacy_reference" if reference.kind == "legacy" else "normalize_api_prefix"
    return MigrationDecision(
        message_id,
        raw_url,
        candidate,
        conversation_id,
        reference.sede_bucket,
        reference.filename,
        reason,
        "migrate",
        True,
    )


def _write_report(path: Path, report: dict[str, Any]) -> None:
    """Write a report atomically so a failed write cannot truncate the prior one."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _build_report(decisions: list[MigrationDecision], *, apply: bool, phase: str) -> dict[str, Any]:
    changed = [decision for decision in decisions if decision.action == "migrate"]
    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.reason] = counts.get(decision.reason, 0) + 1
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "dry_run": not apply,
        "apply_requested": apply,
        "total_messages": len(decisions),
        "migrated": sum(1 for decision in decisions if decision.applied),
        "would_migrate": len(changed) if not apply else 0,
        "counts_by_reason": counts,
        "items": [asdict(decision) for decision in decisions],
    }


def migrate_messages(
    db: Any,
    storage_root: Path,
    *,
    apply: bool = False,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Audit all attachment-bearing messages and optionally apply safe changes."""

    messages = db.query(models.ChatMessage).filter(models.ChatMessage.attachment_url.is_not(None)).all()
    decisions = [classify_message(message, db, storage_root) for message in messages]
    if not apply:
        return _build_report(decisions, apply=False, phase="dry_run")
    if report_path is None:
        raise ValueError("report_path is required when apply=True")

    # The preflight report is the recovery record if the final report write
    # fails after commit. It must be durable before any database mutation.
    _write_report(report_path, _build_report(decisions, apply=True, phase="preflight"))

    changed = [decision for decision in decisions if decision.action == "migrate"]
    for decision, message in zip(decisions, messages):
        if decision.action == "migrate" and decision.candidate_url:
            message.attachment_url = decision.candidate_url
    if changed:
        db.commit()
    for decision in changed:
        decision.applied = True

    report = _build_report(decisions, apply=True, phase="applied")
    _write_report(report_path, report)
    return report


def rollback_report(db: Any, report: dict[str, Any]) -> dict[str, int]:
    """Restore URLs without overwriting a later edit (safe to rerun)."""

    restored = skipped = missing = 0
    allow_preflight_recovery = report.get("phase") == "preflight" and report.get("apply_requested") is True
    for item in report.get("items", []):
        if item.get("action") != "migrate":
            continue
        if not item.get("applied") and not allow_preflight_recovery:
            continue
        message_id = _parse_uuid(item.get("message_id"))
        original_url = item.get("original_url")
        candidate_url = item.get("candidate_url")
        if message_id is None or not candidate_url or original_url is None:
            skipped += 1
            continue
        message = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
        if message is None:
            missing += 1
            continue
        if message.attachment_url != candidate_url:
            skipped += 1
            continue
        message.attachment_url = original_url
        restored += 1
    if restored:
        db.commit()
    return {"restored": restored, "skipped": skipped, "missing": missing}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Persist safe URL rewrites (default: audit only).")
    mode.add_argument("--rollback", type=Path, help="Restore URLs from an applied migration report.")
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=_PROJECT_ROOT / "static" / "chat_attachments",
        help="Attachment root (default: static/chat_attachments).",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("tmp/chat_attachment_migration_report.json"),
        help="JSON report path (default: tmp/chat_attachment_migration_report.json).",
    )
    args = parser.parse_args()

    if args.rollback is not None:
        report = json.loads(args.rollback.read_text(encoding="utf-8"))
        with SessionLocal() as db:
            result = rollback_report(db, report)
        print(f"Chat attachment rollback: {result['restored']} restored, {result['skipped']} skipped, {result['missing']} missing.")
        return 0

    with SessionLocal() as db:
        report = migrate_messages(db, args.storage_root, apply=args.apply, report_path=args.report)
    if not args.apply:
        _write_report(args.report, report)

    count = report["migrated"] if args.apply else report["would_migrate"]
    verb = "migrated" if args.apply else "eligible to migrate"
    print(f"Chat attachment migration {'applied' if args.apply else 'dry-run'}: {report['total_messages']} messages, {count} URL(s) {verb}.")
    print(f"Report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
