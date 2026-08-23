"""Pruebas del MCP privado de Academia."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken

from backend import models
from tests.conftest import TestingSessionLocal, seed_admin


@pytest.fixture
def academy_scope(db_session):
    admin, _persona, sede = seed_admin(db_session, email="mcp-academy-admin@test.com")
    course = models.Course(
        id=uuid.uuid4(),
        sede_id=sede.id,
        code="MCP-ACA-001",
        slug="mcp-academia",
        title="Curso MCP",
        modality="online",
        is_published=True,
    )
    other_sede = models.Sede(id=uuid.uuid4(), nombre="Otra sede Academia", ciudad="Cali", es_activa=True)
    other_course = models.Course(
        id=uuid.uuid4(),
        sede_id=other_sede.id,
        code="MCP-ACA-002",
        slug="mcp-academia-otra",
        title="Curso de otra sede",
        modality="online",
        is_published=True,
    )
    db_session.add_all([course, other_sede, other_course])
    db_session.commit()
    return {"admin_id": admin.id, "course": course, "other_course": other_course, "sede": sede}


def _authenticate(subject):
    return auth_context_var.set(
        AuthenticatedUser(
            AccessToken(
                token="academy-test-token",
                client_id="test-client",
                subject=str(subject),
                scopes=["academy:read", "academy:study", "academy:edit", "academy:manage"],
            )
        )
    )


class TestMcpAcademyContract:
    def test_registers_academy_tools(self):
        from backend.mcp_academy import academy_mcp

        tools = asyncio.run(academy_mcp.list_tools())
        names = {tool.name for tool in tools}
        assert {
            "list_academy_courses",
            "create_academy_course",
            "create_academy_lesson",
            "enroll_current_user",
            "register_academy_attendance",
        } <= names

    def test_course_catalog_is_scoped_and_lifecycle_works(self, monkeypatch, academy_scope):
        import backend.mcp_academy as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(academy_scope["admin_id"])
        try:
            catalog = module.list_academy_courses(limit=100)
            created = module.create_academy_course(
                code="MCP-ACA-003",
                title="Curso creado por MCP",
                modality="online",
            )
            archived = module.archive_academy_course(uuid.UUID(str(created["id"])))
        finally:
            auth_context_var.reset(token)

        ids = {item["id"] for item in catalog["items"]}
        assert str(academy_scope["course"].id) in ids
        assert str(academy_scope["other_course"].id) not in ids
        assert created["sede_id"] == str(academy_scope["sede"].id)
        assert archived["status"] == "archived"

    def test_lesson_and_enrollment_attendance_are_idempotent(self, monkeypatch, academy_scope):
        import backend.mcp_academy as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(academy_scope["admin_id"])
        try:
            lesson = module.create_academy_lesson(
                course_id=academy_scope["course"].id,
                title="Lección MCP",
                is_published=True,
            )
            enrollment = module.enroll_current_user(academy_scope["course"].id)
            first = module.register_academy_attendance(
                uuid.UUID(enrollment["enrollment_id"]),
                "2026-08-20T10:00:00Z",
            )
            second = module.register_academy_attendance(
                uuid.UUID(enrollment["enrollment_id"]),
                "2026-08-20T10:00:00Z",
                status="present",
            )
        finally:
            auth_context_var.reset(token)

        assert lesson["course_id"] == str(academy_scope["course"].id)
        assert first["attendance_id"] == second["attendance_id"]

    def test_global_course_cannot_be_mutated(self, monkeypatch, academy_scope, db_session):
        global_course = models.Course(
            id=uuid.uuid4(),
            sede_id=None,
            code="MCP-ACA-GLOBAL",
            title="Curso global",
            modality="online",
            is_published=True,
        )
        db_session.add(global_course)
        db_session.commit()
        import backend.mcp_academy as module

        monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
        token = _authenticate(academy_scope["admin_id"])
        try:
            with pytest.raises(ValueError, match="globales"):
                module.update_academy_course(global_course.id, {"title": "No permitido"})
        finally:
            auth_context_var.reset(token)
