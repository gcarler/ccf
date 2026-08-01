from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

from backend import models
from scripts import migrate_chat_attachment_urls as migration
from tests.conftest import seed_admin


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self.rows)

    def first(self):
        return self.rows[0] if self.rows else None


class _Db:
    def __init__(self, messages):
        self.messages = messages
        self.commit_count = 0
        self.report_path: Path | None = None
        self.report_phases: list[str] = []

    def query(self, model):
        return _Query(self.messages)

    def commit(self):
        self.commit_count += 1
        if self.report_path is not None:
            report = json.loads(self.report_path.read_text(encoding="utf-8"))
            self.report_phases.append(report["phase"])


def _message(url: str, *, room_id: str | None = None):
    return SimpleNamespace(id=uuid.uuid4(), attachment_url=url, room_id=room_id)


def _binding(conversation_id: uuid.UUID, sede_bucket: str):
    def resolve(_db, _room_id):
        return migration.ConversationBinding(conversation_id, sede_bucket), None

    return resolve


def test_parse_malformed_url_is_blocked_without_aborting():
    reference, reason = migration.parse_attachment_reference("//[broken-host/file.pdf")
    assert reference is None
    assert reason == "invalid_reference"


def test_parse_legacy_ambiguous_and_external_references():
    reference, reason = migration.parse_attachment_reference(
        "/static/chat_attachments/11111111-1111-1111-1111-111111111111/file.pdf"
    )
    assert reason is None
    assert reference is not None
    assert reference.kind == "legacy"

    assert migration.parse_attachment_reference("/static/chat_attachments/file.pdf")[1] == "ambiguous_reference"
    assert migration.parse_attachment_reference("https://cdn.example/file.pdf")[1] == "external_url"
    assert migration.parse_attachment_reference("//cdn.example/file.pdf")[1] == "external_url"


def test_classify_valid_legacy_reference_and_missing_file(tmp_path: Path):
    conversation_id = uuid.uuid4()
    sede = str(uuid.uuid4())
    storage = tmp_path / "chat_attachments" / sede
    storage.mkdir(parents=True)
    (storage / "file.pdf").write_bytes(b"pdf")
    resolver = _binding(conversation_id, sede)

    valid = _message(f"/static/chat_attachments/{sede}/file.pdf", room_id=f"dm_{conversation_id}")
    decision = migration.classify_message(valid, None, tmp_path / "chat_attachments", binding_resolver=resolver)
    assert decision.action == "migrate"
    assert decision.reason == "legacy_reference"
    assert decision.candidate_url == f"/chat/attachments/{conversation_id}/{sede}/file.pdf"
    assert decision.file_exists is True

    missing = _message(f"/static/chat_attachments/{sede}/missing.pdf", room_id=f"dm_{conversation_id}")
    missing_decision = migration.classify_message(
        missing, None, tmp_path / "chat_attachments", binding_resolver=resolver
    )
    assert missing_decision.action == "block"
    assert missing_decision.reason == "missing_file"
    assert missing.attachment_url.endswith("missing.pdf")


def test_classify_blocks_cross_conversation_and_cross_sede_references(tmp_path: Path):
    conversation_id = uuid.uuid4()
    other_conversation_id = uuid.uuid4()
    sede = str(uuid.uuid4())
    (tmp_path / sede).mkdir()
    (tmp_path / sede / "file.pdf").write_bytes(b"pdf")
    resolver = _binding(conversation_id, sede)

    wrong_conversation = _message(
        f"/chat/attachments/{other_conversation_id}/{sede}/file.pdf",
        room_id=f"dm_{conversation_id}",
    )
    decision = migration.classify_message(
        wrong_conversation, None, tmp_path, binding_resolver=resolver
    )
    assert decision.action == "block"
    assert decision.reason == "conversation_reference_mismatch"

    other_sede = str(uuid.uuid4())
    wrong_sede = _message(
        f"/static/chat_attachments/{other_sede}/file.pdf",
        room_id=f"dm_{conversation_id}",
    )
    decision = migration.classify_message(wrong_sede, None, tmp_path, binding_resolver=resolver)
    assert decision.action == "block"
    assert decision.reason == "sede_bucket_mismatch"


def test_classify_normalizes_api_url_and_rejects_symlink_outside_storage(tmp_path: Path):
    conversation_id = uuid.uuid4()
    sede = str(uuid.uuid4())
    root = tmp_path / "chat_attachments"
    (root / sede).mkdir(parents=True)
    (root / sede / "file.pdf").write_bytes(b"pdf")
    resolver = _binding(conversation_id, sede)

    api_url = _message(
        f"/api/chat/attachments/{conversation_id}/{sede}/file.pdf?download=1",
        room_id=f"dm_{conversation_id}",
    )
    decision = migration.classify_message(api_url, None, root, binding_resolver=resolver)
    assert decision.action == "migrate"
    assert decision.reason == "normalize_api_prefix"
    assert decision.candidate_url == f"/chat/attachments/{conversation_id}/{sede}/file.pdf"

    outside = tmp_path / "outside.pdf"
    outside.write_bytes(b"secret")
    (root / sede / "link.pdf").symlink_to(outside)
    linked = _message(f"/static/chat_attachments/{sede}/link.pdf", room_id=f"dm_{conversation_id}")
    decision = migration.classify_message(linked, None, root, binding_resolver=resolver)
    assert decision.action == "block"
    assert decision.reason == "file_outside_storage_root"


def test_resolve_binding_uses_tenant_sede_and_fails_closed_for_cross_sede(db_session):
    admin_a, persona_a, sede_a = seed_admin(db_session, email="migration-a@example.com")
    admin_b, persona_b, sede_b = seed_admin(db_session, email="migration-b@example.com")

    same_sede = models.Conversation(id=uuid.uuid4())
    db_session.add(same_sede)
    db_session.flush()
    db_session.add_all(
        [
            models.ConversationParticipant(conversation_id=same_sede.id, user_id=admin_a.id),
            models.ConversationParticipant(conversation_id=same_sede.id, user_id=persona_b.id),
        ]
    )
    # A global/superadmin Persona may coexist with one tenant participant;
    # the tenant participant still determines the protected bucket.
    persona_b.sede_id = None
    db_session.commit()

    binding, reason = migration._resolve_conversation_binding(db_session, f"dm_{same_sede.id}")
    assert reason is None
    assert binding == migration.ConversationBinding(same_sede.id, str(sede_a.id))

    persona_b.sede_id = sede_b.id
    cross_sede = models.Conversation(id=uuid.uuid4())
    db_session.add(cross_sede)
    db_session.flush()
    db_session.add_all(
        [
            models.ConversationParticipant(conversation_id=cross_sede.id, user_id=admin_a.id),
            models.ConversationParticipant(conversation_id=cross_sede.id, user_id=persona_b.id),
        ]
    )
    db_session.commit()

    binding, reason = migration._resolve_conversation_binding(db_session, f"dm_{cross_sede.id}")
    assert binding is None
    assert reason == "cross_sede_conversation"


def test_dry_run_does_not_mutate_and_apply_writes_preflight_then_supports_rollback(tmp_path: Path):
    conversation_id = uuid.uuid4()
    sede = str(uuid.uuid4())
    root = tmp_path / "chat_attachments"
    (root / sede).mkdir(parents=True)
    (root / sede / "file.pdf").write_bytes(b"pdf")
    original = f"/static/chat_attachments/{sede}/file.pdf"
    message = _message(original, room_id=f"dm_{conversation_id}")
    db = _Db([message])
    resolver = _binding(conversation_id, sede)

    # Patch the module-level classifier only for this isolated fake DB test.
    original_classifier = migration.classify_message
    migration.classify_message = lambda msg, fake_db, storage: original_classifier(
        msg, fake_db, storage, binding_resolver=resolver
    )
    try:
        dry_report = migration.migrate_messages(db, root, apply=False)
        assert dry_report["dry_run"] is True
        assert dry_report["would_migrate"] == 1
        assert message.attachment_url == original
        assert db.commit_count == 0

        report_path = tmp_path / "migration.json"
        db.report_path = report_path
        applied = migration.migrate_messages(db, root, apply=True, report_path=report_path)
        assert message.attachment_url == f"/chat/attachments/{conversation_id}/{sede}/file.pdf"
        assert applied["migrated"] == 1
        assert applied["items"][0]["applied"] is True
        assert db.report_phases == ["preflight"]
        assert json.loads(report_path.read_text(encoding="utf-8"))["phase"] == "applied"

        result = migration.rollback_report(db, applied)
        assert result == {"restored": 1, "skipped": 0, "missing": 0}
        assert message.attachment_url == original

        # A second rollback is a no-op and cannot overwrite a later edit.
        result = migration.rollback_report(db, applied)
        assert result["restored"] == 0
    finally:
        migration.classify_message = original_classifier
