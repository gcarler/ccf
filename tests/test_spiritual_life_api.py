"""Tests for the Spiritual Life module."""
from datetime import date, timedelta

import pytest

from backend import models
from tests.conftest import auth_headers, seed_admin, seed_user_with_role


@pytest.fixture(scope="function")
def admin_client(client, db_session):
    user, persona, sede = seed_admin(db_session)
    headers = auth_headers(client)
    return client, headers, sede, persona


@pytest.fixture(scope="function")
def editor_client(client, db_session):
    user, persona, sede = seed_user_with_role(
        db_session,
        role_name="EDITOR_SL",
        email="editor-sl@test.com",
        permisos={"spiritual_life:read": "allow", "spiritual_life:edit": "allow"},
    )
    headers = auth_headers(client, email="editor-sl@test.com")
    return client, headers, sede, persona


@pytest.fixture(scope="function")
def reader_client(client, db_session):
    user, persona, sede = seed_user_with_role(
        db_session,
        role_name="READER_SL",
        email="reader-sl@test.com",
        permisos={"spiritual_life:read": "allow"},
    )
    headers = auth_headers(client, email="reader-sl@test.com")
    return client, headers, sede, persona


@pytest.fixture(scope="function")
def manager_client(client, db_session):
    user, persona, sede = seed_user_with_role(
        db_session,
        role_name="MANAGER_SL",
        email="manager-sl@test.com",
        permisos={
            "spiritual_life:read": "allow",
            "spiritual_life:edit": "allow",
            "spiritual_life:manage": "allow",
        },
    )
    headers = auth_headers(client, email="manager-sl@test.com")
    return client, headers, sede, persona


def _create_milestone(client, headers, persona_id, milestone_type="Decision_Fe", event_date=None):
    if event_date is None:
        event_date = str(date.today())
    return client.post(
        "/api/spiritual-life/milestones",
        headers=headers,
        json={
            "persona_id": str(persona_id),
            "type": milestone_type,
            "event_date": event_date,
            "notes": "Test milestone",
        },
    )


class TestMilestoneCRUD:
    def test_create_milestone_as_manager(self, manager_client):
        client, headers, sede, persona = manager_client
        resp = _create_milestone(client, headers, persona.id)
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "Decision_Fe"
        assert data["persona_id"] == str(persona.id)

    def test_create_milestone_as_editor_fails(self, editor_client):
        client, headers, sede, persona = editor_client
        resp = _create_milestone(client, headers, persona.id)
        assert resp.status_code == 403

    def test_list_milestones_for_persona(self, manager_client):
        client, headers, sede, persona = manager_client
        _create_milestone(client, headers, persona.id)
        resp = client.get(f"/api/spiritual-life/milestones/{persona.id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["type"] == "Decision_Fe"

    def test_get_milestone_detail(self, manager_client):
        client, headers, sede, persona = manager_client
        create_resp = _create_milestone(client, headers, persona.id)
        milestone_id = create_resp.json()["id"]
        resp = client.get(f"/api/spiritual-life/milestone/{milestone_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == milestone_id

    def test_update_milestone(self, editor_client):
        client, headers, sede, persona = editor_client
        # Editor cannot create, so seed milestone directly
        milestone = models.SpiritualMilestone(
            persona_id=persona.id,
            sede_id=sede.id,
            type="Decision_Fe",
            event_date=date.today(),
            notes="Original",
        )
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        db.add(milestone)
        db.commit()
        db.refresh(milestone)

        resp = client.patch(
            f"/api/spiritual-life/milestone/{milestone.id}",
            headers=headers,
            json={"notes": "Updated notes"},
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Updated notes"

    def test_delete_milestone(self, editor_client):
        client, headers, sede, persona = editor_client
        milestone = models.SpiritualMilestone(
            persona_id=persona.id,
            sede_id=sede.id,
            type="Decision_Fe",
            event_date=date.today(),
        )
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        db.add(milestone)
        db.commit()
        db.refresh(milestone)

        resp = client.delete(f"/api/spiritual-life/milestone/{milestone.id}", headers=headers)
        assert resp.status_code == 204

        get_resp = client.get(f"/api/spiritual-life/milestone/{milestone.id}", headers=headers)
        assert get_resp.status_code == 404


class TestMilestoneRBAC:
    def test_reader_can_read_but_not_create(self, reader_client):
        client, headers, sede, persona = reader_client
        read_resp = client.get(f"/api/spiritual-life/milestones/{persona.id}", headers=headers)
        assert read_resp.status_code == 200

        create_resp = _create_milestone(client, headers, persona.id)
        assert create_resp.status_code == 403

    def test_editor_can_update_but_not_create(self, editor_client):
        client, headers, sede, persona = editor_client
        create_resp = _create_milestone(client, headers, persona.id)
        assert create_resp.status_code == 403

        milestone = models.SpiritualMilestone(
            persona_id=persona.id,
            sede_id=sede.id,
            type="Bautismo_Aguas",
            event_date=date.today(),
        )
        from tests.conftest import TestingSessionLocal
        db = TestingSessionLocal()
        db.add(milestone)
        db.commit()
        db.refresh(milestone)

        patch_resp = client.patch(
            f"/api/spiritual-life/milestone/{milestone.id}",
            headers=headers,
            json={"notes": "Updated"},
        )
        assert patch_resp.status_code == 200


class TestMilestoneValidation:
    def test_invalid_type_rejected(self, manager_client):
        client, headers, sede, persona = manager_client
        resp = _create_milestone(client, headers, persona.id, milestone_type="Invalid_Type")
        assert resp.status_code == 422

    def test_cross_sede_persona_returns_404(self, manager_client):
        client, headers, sede, persona = manager_client
        from tests.conftest import TestingSessionLocal
        from backend import models as _models

        other_sede = _models.Sede(
            id=__import__("uuid").uuid4(),
            nombre="Otra Sede",
            ciudad="Medellin",
            es_activa=True,
        )
        db = TestingSessionLocal()
        db.add(other_sede)
        db.commit()

        other_persona = models.Persona(
            id=__import__("uuid").uuid4(),
            first_name="Otro",
            last_name="Usuario",
            sede_id=other_sede.id,
        )
        db.add(other_persona)
        db.commit()

        resp = _create_milestone(client, headers, other_persona.id)
        assert resp.status_code == 404
