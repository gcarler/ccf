import uuid
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from backend.crud import projects
from backend.schemas.projects import ProjectFileLinkDrivePayload


@pytest.mark.parametrize("as_model", [False, True])
def test_drive_link_uses_validated_payload_before_storage(monkeypatch, as_model):
    data = {"drive_url": "https://drive.google.com/file/d/abcdefghijklmnop/view", "name": "Acta"}
    payload = ProjectFileLinkDrivePayload(**data) if as_model else data
    store = Mock(return_value=object())
    monkeypatch.setattr(projects, "create_project_file", store)
    result = projects.link_drive_file(Mock(), uuid.uuid4(), payload=payload)
    assert result is store.return_value
    assert store.call_args.kwargs["name"] == "Acta"
    assert store.call_args.kwargs["file_url"] == data["drive_url"]


def test_drive_link_rejects_invalid_payload_without_storage(monkeypatch):
    store = Mock()
    monkeypatch.setattr(projects, "create_project_file", store)
    with pytest.raises(ValidationError):
        projects.link_drive_file(Mock(), uuid.uuid4(), payload={"name": "Missing URL"})
    store.assert_not_called()
