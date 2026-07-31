"""
Dedicated tests for academy.py — courses, lessons, enrollments, forum.
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
    admin, _, _ = _seed_admin(db_session, email="acad@test.com")
    headers = _auth_headers(client, email="acad@test.com", password="testpass123")
    return {"c": client, "h": headers, "s": db_session.query(models.Sede).first()}


class TestAcademyCourses:
    def test_list(self, full):
        assert _ok(full["c"].get("/api/academy/courses", headers=full["h"]).status_code)

    def test_get_not_found(self, full):
        assert full["c"].get(f"/api/academy/courses/{uuid.uuid4()}", headers=full["h"]).status_code == 404

    def test_lessons_not_found(self, full):
        assert full["c"].get(f"/api/academy/courses/{uuid.uuid4()}/lessons", headers=full["h"]).status_code == 404

    def test_assessments_not_found(self, full):
        assert full["c"].get(f"/api/academy/courses/{uuid.uuid4()}/assessments", headers=full["h"]).status_code == 404


class TestAcademyEnrollments:
    def test_my_enrollments(self, full):
        assert _ok(full["c"].get("/api/academy/me/enrollments", headers=full["h"]).status_code)

    def test_list(self, full):
        assert _ok(full["c"].get("/api/academy/enrollments", headers=full["h"]).status_code)


class TestAcademyProgress:
    def test_my_progress(self, full):
        assert _ok(full["c"].get("/api/academy/me/progress", headers=full["h"]).status_code)


class TestAcademyProfile:
    def test_my_profile(self, full):
        assert _ok(full["c"].get("/api/academy/me/profile", headers=full["h"]).status_code)


class TestAcademyCertificates:
    def test_my_certificates(self, full):
        assert _ok(full["c"].get("/api/academy/me/certificates", headers=full["h"]).status_code)

    def test_validate_not_found(self, full):
        assert full["c"].get("/api/academy/certificates/validate/invalid-code", headers=full["h"]).status_code == 404


class TestAcademyForum:
    def test_list_threads(self, full):
        assert _ok(full["c"].get("/api/academy/forum/threads", headers=full["h"]).status_code)

    def test_get_thread_not_found(self, full):
        assert full["c"].get(f"/api/academy/forum/threads/{uuid.uuid4()}", headers=full["h"]).status_code == 404


class TestAcademySchedule:
    def test_schedule(self, full):
        assert _ok(full["c"].get("/api/academy/schedule", headers=full["h"]).status_code)


class TestAcademyLesson:
    def test_lesson_progress_not_found(self, full):
        assert full["c"].get(f"/api/academy/lessons/{uuid.uuid4()}/progress", headers=full["h"]).status_code == 404

    def test_resources_not_found(self, full):
        assert full["c"].get(f"/api/academy/lessons/{uuid.uuid4()}/resources", headers=full["h"]).status_code == 404
