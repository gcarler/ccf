"""
Tests for projects.py — main CRUD endpoints.
"""
from __future__ import annotations

import uuid

import pytest

from backend import models
from tests.conftest import auth_headers as _auth_headers
from tests.conftest import seed_admin as _seed_admin


def _ok(status):
    return status in (200, 201, 204)


@pytest.fixture
def full(client, db_session):
    admin, _, _ = _seed_admin(db_session, email="proj@test.com")
    headers = _auth_headers(client, email="proj@test.com", password="testpass123")
    return {"c": client, "h": headers}


def _make_project(full):
    c, h = full["c"], full["h"]
    resp = c.post("/api/projects", json={"title": f"P-{uuid.uuid4().hex[:6]}"}, headers=h)
    assert _ok(resp.status_code)
    return resp.json()


class TestProjectCRUD:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/projects", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post("/api/projects", json={"title": f"P-{uuid.uuid4().hex[:6]}"}, headers=full["h"]).status_code)
    def test_get(self, full):
        assert _ok(full["c"].get(f"/api/projects/{_make_project(full)['id']}", headers=full["h"]).status_code)
    def test_patch(self, full):
        assert _ok(full["c"].patch(f"/api/projects/{_make_project(full)['id']}", json={"title": "Upd"}, headers=full["h"]).status_code)
    def test_delete(self, full):
        assert _ok(full["c"].delete(f"/api/projects/{_make_project(full)['id']}", headers=full["h"]).status_code)
    def test_not_found(self, full):
        assert full["c"].get(f"/api/projects/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestProjectPhases:
    def test_list(self, full):
        assert _ok(full["c"].get(f"/api/projects/{_make_project(full)['id']}/phases", headers=full["h"]).status_code)


class TestProjectTasks:
    def test_list(self, full):
        assert _ok(full["c"].get(f"/api/projects/{_make_project(full)['id']}/tasks", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post(f"/api/projects/{_make_project(full)['id']}/tasks", json={"title": "T"}, headers=full["h"]).status_code)
    def test_get_task(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "Get"}, headers=full["h"]).json()
        assert _ok(full["c"].get(f"/api/projects/tasks/{t['id']}", headers=full["h"]).status_code)
    def test_patch_task(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "Patch"}, headers=full["h"]).json()
        assert _ok(full["c"].patch(f"/api/projects/tasks/{t['id']}", json={"title": "Upd"}, headers=full["h"]).status_code)
    def test_delete_task(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "Del"}, headers=full["h"]).json()
        assert _ok(full["c"].delete(f"/api/projects/{p['id']}/tasks/{t['id']}", headers=full["h"]).status_code)
    def test_not_found(self, full):
        assert full["c"].get(f"/api/projects/tasks/{uuid.uuid4()}", headers=full["h"]).status_code == 404
    def test_my_tasks(self, full):
        assert _ok(full["c"].get("/api/projects/tasks", headers=full["h"]).status_code)


class TestProjectComments:
    def test_list_all(self, full):
        assert _ok(full["c"].get("/api/projects/comments", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post(f"/api/projects/{_make_project(full)['id']}/comments", json={"content": "Hi"}, headers=full["h"]).status_code)


class TestProjectSummary:
    def test_summary(self, full):
        assert _ok(full["c"].get("/api/projects/summary", headers=full["h"]).status_code)


class TestProjectWorkload:
    def test_workload(self, full):
        assert _ok(full["c"].get("/api/projects/workload", headers=full["h"]).status_code)


class TestProjectActivities:
    def test_activities(self, full):
        assert _ok(full["c"].get("/api/projects/activities", headers=full["h"]).status_code)


class TestProjectInbox:
    def test_inbox(self, full):
        assert _ok(full["c"].get("/api/projects/inbox", headers=full["h"]).status_code)


class TestProjectWhiteboards:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/projects/whiteboards", headers=full["h"]).status_code)
    def test_get(self, full):
        assert _ok(full["c"].get(f"/api/projects/{_make_project(full)['id']}/whiteboard", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post(f"/api/projects/{_make_project(full)['id']}/whiteboard", json={"content": "D"}, headers=full["h"]).status_code)
    def test_delete(self, full):
        p = _make_project(full)
        full["c"].post(f"/api/projects/{p['id']}/whiteboard", json={"content": "D"}, headers=full["h"])
        assert _ok(full["c"].delete(f"/api/projects/{p['id']}/whiteboard", headers=full["h"]).status_code)


class TestProjectWiki:
    def test_get(self, full):
        assert _ok(full["c"].get(f"/api/projects/{_make_project(full)['id']}/wiki", headers=full["h"]).status_code)
    def test_create(self, full):
        assert _ok(full["c"].post(f"/api/projects/{_make_project(full)['id']}/wiki", json={"title": "W", "content": "C"}, headers=full["h"]).status_code)


class TestProjectMessages:
    def test_messages(self, full):
        assert _ok(full["c"].get(f"/api/projects/{_make_project(full)['id']}/messages", headers=full["h"]).status_code)


class TestProjectSubtask:
    def test_create(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "P"}, headers=full["h"]).json()
        assert _ok(full["c"].post(f"/api/projects/{p['id']}/tasks/{t['id']}/subtasks", json={"title": "S"}, headers=full["h"]).status_code)
    def test_patch(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "P"}, headers=full["h"]).json()
        st = full["c"].post(f"/api/projects/{p['id']}/tasks/{t['id']}/subtasks", json={"title": "S"}, headers=full["h"]).json()
        assert _ok(full["c"].patch(f"/api/projects/{p['id']}/tasks/{t['id']}/subtasks/{st['id']}", json={"title": "U"}, headers=full["h"]).status_code)
    def test_delete(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "P"}, headers=full["h"]).json()
        st = full["c"].post(f"/api/projects/{p['id']}/tasks/{t['id']}/subtasks", json={"title": "S"}, headers=full["h"]).json()
        assert _ok(full["c"].delete(f"/api/projects/{p['id']}/tasks/{t['id']}/subtasks/{st['id']}", headers=full["h"]).status_code)


class TestProjectSupplies:
    def test_list_supplies(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "T"}, headers=full["h"]).json()
        assert _ok(full["c"].get(f"/api/projects/{p['id']}/tasks/{t['id']}/supplies", headers=full["h"]).status_code)

    def test_create_supply(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "T"}, headers=full["h"]).json()
        assert _ok(full["c"].post(f"/api/projects/{p['id']}/tasks/{t['id']}/supplies",
            json={"item_name": "Hammer", "quantity": 2}, headers=full["h"]).status_code)

    def test_patch_supply(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "T"}, headers=full["h"]).json()
        s = full["c"].post(f"/api/projects/{p['id']}/tasks/{t['id']}/supplies",
            json={"item_name": "Nail", "quantity": 10}, headers=full["h"]).json()
        assert _ok(full["c"].patch(f"/api/projects/{p['id']}/tasks/{t['id']}/supplies/{s['id']}",
            json={"quantity": 5}, headers=full["h"]).status_code)

    def test_delete_supply(self, full):
        p = _make_project(full)
        t = full["c"].post(f"/api/projects/{p['id']}/tasks", json={"title": "T"}, headers=full["h"]).json()
        s = full["c"].post(f"/api/projects/{p['id']}/tasks/{t['id']}/supplies",
            json={"item_name": "Nail", "quantity": 5}, headers=full["h"]).json()
        assert _ok(full["c"].delete(f"/api/projects/{p['id']}/tasks/{t['id']}/supplies/{s['id']}",
            headers=full["h"]).status_code)


class TestProjectAttachments:
    def test_get_task_with_attachments(self, full):
        p = _make_project(full)
        assert _ok(full["c"].get(f"/api/projects/{p['id']}/tasks", headers=full["h"]).status_code)

    def test_delete_attachment_not_found(self, full):
        p = _make_project(full)
        assert full["c"].delete(f"/api/projects/{p['id']}/tasks/{uuid.uuid4()}/attachments/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404


class TestProjectInboxRead:
    def test_read_not_found(self, full):
        assert full["c"].post(f"/api/projects/inbox/{uuid.uuid4()}/read",
            headers=full["h"]).status_code == 404


class TestProjectCommentsPatch:
    def test_patch_not_found(self, full):
        assert full["c"].patch(f"/api/projects/comments/{uuid.uuid4()}",
            json={"content": "X"}, headers=full["h"]).status_code == 404

    def test_delete_not_found(self, full):
        assert full["c"].delete(f"/api/projects/comments/{uuid.uuid4()}",
            headers=full["h"]).status_code == 404
