from __future__ import annotations

import uuid

from backend.core.identity import _as_uuid, get_user_sede_id


def test_as_uuid_accepts_uuid_and_string() -> None:
    value = uuid.uuid4()

    assert _as_uuid(value) == value
    assert _as_uuid(str(value)) == value


def test_as_uuid_rejects_invalid_values() -> None:
    assert _as_uuid(None) is None
    assert _as_uuid("not-a-uuid") is None


def test_get_user_sede_id_normalizes_tenant_result(monkeypatch) -> None:
    value = uuid.uuid4()
    monkeypatch.setattr(
        "backend.core.identity._tenant_get_user_sede_id",
        lambda _db, _user: str(value),
    )

    assert get_user_sede_id(object(), object()) == value
