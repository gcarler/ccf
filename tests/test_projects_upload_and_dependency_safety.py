"""HTTP regressions for project upload safety and cyclic dependencies."""
import base64
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import pytest

from backend import models
from tests.conftest import auth_headers, seed_admin
from tests.factories_projects import create_project_factory, create_task_factory


@pytest.fixture
def project_context(db_session, client):
    user, _, sede = seed_admin(db_session, email="projects-safety@example.com")
    project = create_project_factory(db_session, sede_id=sede.id, owner_id=user.id)
    tasks = [create_task_factory(db_session, project.id) for _ in range(3)]
    db_session.commit()
    return project, tasks, auth_headers(client, email=user.email)


@pytest.mark.parametrize("chain_length", [2, 3])
def test_cycle_returns_422_without_persisting_rejected_edge(client, db_session, project_context, chain_length):
    project, tasks, headers = project_context
    route = f"/api/projects/{project.id}/dependencies"
    for predecessor, successor in zip(tasks[:chain_length], tasks[1:chain_length]):
        response = client.post(route, headers=headers, json={"predecessor_id": str(predecessor.id), "successor_id": str(successor.id)})
        assert response.status_code == 201, response.text
    before = db_session.query(models.ProjectTaskDependency).filter_by(project_id=project.id).count()
    response = client.post(route, headers=headers, json={"predecessor_id": str(tasks[chain_length-1].id), "successor_id": str(tasks[0].id)})
    assert response.status_code == 422, response.text
    assert "circular" in response.json()["detail"].lower()
    db_session.expire_all()
    assert db_session.query(models.ProjectTaskDependency).filter_by(project_id=project.id).count() == before
    # Rejection must not poison the next valid request/session.
    valid = client.post(route, headers=headers, json={"predecessor_id": str(tasks[0].id), "successor_id": str(tasks[2].id)})
    assert valid.status_code == 201, valid.text
    assert UUID(valid.json()["predecessor_id"]) == tasks[0].id


@pytest.fixture
def isolated_upload_storage(tmp_path, monkeypatch):
    from backend.api import projects as projects_api
    from backend.core.storage import StorageService
    storage = StorageService(base_dir=str(tmp_path / "uploads"))
    spy = Mock(wraps=storage.save_file)
    monkeypatch.setattr(storage, "save_file", spy)
    monkeypatch.setattr(projects_api, "storage_service", storage)
    return Path(storage.base_dir), spy


def upload_route(project, task, kind):
    if kind == "attachment":
        return f"/api/projects/{project.id}/tasks/{task.id}/attachments"
    return f"/api/projects/{project.id}/files/upload"


@pytest.mark.parametrize("kind", ["attachment", "vault"])
@pytest.mark.parametrize("filename,mime", [
    ("payload.exe", "application/octet-stream"),
    ("payload.php", "application/x-httpd-php"),
    ("payload.html", "text/html"),
    ("payload.svg", "image/svg+xml"),
    ("payload.HTML", "text/html"),
    ("payload.png.html", "text/html"),
    ("payload", "application/octet-stream"),
])
def test_rejected_extensions_never_reach_storage_or_database(client, db_session, project_context, isolated_upload_storage, kind, filename, mime):
    project, tasks, headers = project_context
    root, save = isolated_upload_storage
    response = client.post(upload_route(project, tasks[0], kind), headers=headers,
                           files={"file": (filename, b"<html><script>alert(1)</script></html>", mime)})
    assert response.status_code == 400, response.text
    assert "extension" in response.json()["detail"].lower()
    save.assert_not_called()
    assert not list(root.rglob("*"))
    assert db_session.query(models.ProjectAttachment).count() == 0
    assert db_session.query(models.ProjectFile).count() == 0


@pytest.mark.parametrize("kind", ["attachment", "vault"])
@pytest.mark.parametrize("filename", ["report.pdf", "diagram.png"])
def test_rejected_mime_mismatch_never_reaches_storage(client, db_session, project_context, isolated_upload_storage, kind, filename):
    project, tasks, headers = project_context
    root, save = isolated_upload_storage
    response = client.post(upload_route(project, tasks[0], kind), headers=headers,
                           files={"file": (filename, b"<html>active content</html>", "text/html")})
    assert response.status_code == 400, response.text
    save.assert_not_called()
    assert not list(root.rglob("*"))
    assert db_session.query(models.ProjectAttachment).count() == 0
    assert db_session.query(models.ProjectFile).count() == 0


@pytest.mark.parametrize("kind", ["attachment", "vault"])
@pytest.mark.parametrize("format", ["pdf", "png", "upper-pdf"])
def test_legitimate_documents_and_images_are_saved(client, db_session, project_context, isolated_upload_storage, kind, format):
    from reportlab.pdfgen.canvas import Canvas
    project, tasks, headers = project_context
    root, save = isolated_upload_storage
    if format == "png":
        contents = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        filename, mime = "diagram.png", "image/png"
    else:
        buffer = BytesIO()
        canvas = Canvas(buffer)
        canvas.drawString(30, 700, "Legitimate project evidence")
        canvas.save()
        contents = buffer.getvalue()
        filename, mime = ("report.PDF" if format == "upper-pdf" else "report.pdf"), "application/pdf"
    response = client.post(upload_route(project, tasks[0], kind), headers=headers,
                           files={"file": (filename, contents, mime)})
    assert response.status_code == 200, response.text
    save.assert_called_once()
    files = [item for item in root.rglob("*") if item.is_file()]
    assert len(files) == 1
    assert files[0].stat().st_size > 0
    if kind == "attachment":
        assert response.json()["id"] == str(tasks[0].id)
        assert any(item["filename"] == filename for item in response.json()["attachments"])
        assert db_session.query(models.ProjectAttachment).count() == 1
    else:
        assert db_session.query(models.ProjectFile).count() == 1
        assert response.json()["file_type"] == mime
        assert response.json()["file_size"] == len(contents)
        assert response.json()["file_url"].startswith("/api/static/projects/boveda/")


@pytest.mark.parametrize("kind", ["attachment", "vault"])
def test_upload_authentication_still_precedes_storage(client, project_context, isolated_upload_storage, kind):
    project, tasks, _ = project_context
    root, save = isolated_upload_storage
    response = client.post(upload_route(project, tasks[0], kind), files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")})
    assert response.status_code in (401, 403), response.text
    save.assert_not_called()
    assert not list(root.rglob("*"))
