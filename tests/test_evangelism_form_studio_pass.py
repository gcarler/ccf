"""
Tests for Event Form Studio, Sequential Correlative, and Digital Pass Super-PRO (TKT-EVT-STUDIO-01).

Validates:
1. Event pre-registration fields update & retrieval.
2. Dynamic Form Studio endpoints: GET /events/{id}/form and PUT /events/{id}/form.
3. Sequential registration_number generation (1, 2, 3...) and registration_code formatting (#CCF-EVT-0001).
4. Digital Pass PDF generation endpoints:
   - Admin: GET /api/evangelism/events/{id}/registrations/{reg_id}/pass
   - Public: GET /api/public/events/{id}/registrations/{reg_id}/pass
"""

from __future__ import annotations

import datetime
import uuid
import pytest

from backend import models
from tests.conftest import auth_headers, seed_admin


@pytest.fixture
def evangelism_setup(client, db_session):
    admin, _, sede = seed_admin(db_session, email="formstudio@ccf.test")
    headers = auth_headers(client, email="formstudio@ccf.test", password="testpass123")
    return {"client": client, "headers": headers, "db": db_session, "sede": sede, "admin": admin}


def test_event_preregistration_config_and_form_studio(evangelism_setup):
    client = evangelism_setup["client"]
    headers = evangelism_setup["headers"]
    db = evangelism_setup["db"]
    sede = evangelism_setup["sede"]

    # 1. Create event
    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Gran Cruzada Evangelística 2026",
        description="Evento masivo de cosecha y transformación",
        event_date=datetime.date(2026, 10, 15),
        start_time="18:00",
        end_time="21:00",
        location="Auditorio Central CCF",
        event_type="SPECIAL",
        sede_id=sede.id,
        requires_registration=True,
        capacity_max=500,
        waiting_list_enabled=True,
        qr_mode="PER_REGISTRANT",
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # 2. GET /events/{id}/form initially returns empty fields
    get_form_resp = client.get(f"/api/evangelism/events/{event.id}/form", headers=headers)
    assert get_form_resp.status_code == 200, get_form_resp.text
    form_data = get_form_resp.json()
    assert form_data["fields"] == []

    # 3. PUT /events/{id}/form to save Form Studio schema (7 presets + custom fields)
    fields_payload = [
        {
            "id": "id_document",
            "type": "text",
            "label": "Documento de Identidad",
            "placeholder": "C.C. / T.I. / Pasaporte",
            "required": True,
        },
        {
            "id": "full_name",
            "type": "text",
            "label": "Nombre Completo",
            "placeholder": "Nombres y Apellidos",
            "required": True,
        },
        {
            "id": "invited_by",
            "type": "text",
            "label": "¿Quién te invitó?",
            "placeholder": "Nombre de la persona o líder que te invitó",
            "required": False,
        },
        {
            "id": "prayer_request",
            "type": "textarea",
            "label": "Petición de Oración",
            "placeholder": "¿Por qué motivo te gustaría que oremos?",
            "required": False,
        },
        {
            "id": "first_time",
            "type": "checkbox",
            "label": "¿Es tu primera vez en CCF?",
            "required": False,
        },
    ]

    put_form_resp = client.put(
        f"/api/evangelism/events/{event.id}/form",
        json={"fields": fields_payload},
        headers=headers,
    )
    assert put_form_resp.status_code == 200, put_form_resp.text
    saved_form = put_form_resp.json()
    assert saved_form["fields_count"] == 5
    assert saved_form["form_id"] is not None

    # Verify event has form_id linked
    db.refresh(event)
    assert event.form_id is not None
    assert str(event.form_id) == saved_form["form_id"]

    # 4. GET /events/{id}/form now returns the saved schema
    get_form_resp2 = client.get(f"/api/evangelism/events/{event.id}/form", headers=headers)
    assert get_form_resp2.status_code == 200
    form_data2 = get_form_resp2.json()
    assert len(form_data2["fields"]) == 5
    assert form_data2["fields"][0]["id"] == "id_document"
    assert form_data2["fields"][0]["required"] is True


def test_sequential_registration_correlative_and_pass_pdf(evangelism_setup):
    client = evangelism_setup["client"]
    headers = evangelism_setup["headers"]
    db = evangelism_setup["db"]
    sede = evangelism_setup["sede"]

    event = models.CrmEvent(
        id=uuid.uuid4(),
        name="Congreso Apostólico y Misionero",
        description="Pase de acceso con numeración correlativa",
        event_date=datetime.date(2026, 11, 20),
        start_time="19:00",
        end_time="22:00",
        location="Coliseo Mayor",
        event_type="SPECIAL",
        sede_id=sede.id,
        requires_registration=True,
        capacity_max=1000,
        waiting_list_enabled=True,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Register 3 personas publicly
    registrations = []
    for i in range(1, 4):
        reg_resp = client.post(
            f"/api/public/events/{event.id}/register",
            json={
                "first_name": f"Participante",
                "last_name": f"Numero {i}",
                "email": f"asistente{i}_{uuid.uuid4().hex[:6]}@ccf.com",
                "phone": f"+57 300 000 {i:04d}",
                "accept_contact": True,
            },
        )
        assert reg_resp.status_code == 200, reg_resp.text
        data = reg_resp.json()
        assert data["registration_number"] == i
        expected_code = f"#CCF-EVT-{i:04d}"
        assert data["registration_code"] == expected_code
        registrations.append(data)

    reg_1 = registrations[0]

    # Test Admin Download Pass (PDF)
    admin_pass_resp = client.get(
        f"/api/evangelism/events/{event.id}/registrations/{reg_1['id']}/pass",
        headers=headers,
    )
    assert admin_pass_resp.status_code == 200, admin_pass_resp.text
    assert admin_pass_resp.headers["content-type"] == "application/pdf"
    assert admin_pass_resp.content.startswith(b"%PDF")
    assert len(admin_pass_resp.content) > 1000

    # Test Public Download Pass (PDF)
    public_pass_resp = client.get(
        f"/api/public/events/{event.id}/registrations/{reg_1['id']}/pass"
    )
    assert public_pass_resp.status_code == 200, public_pass_resp.text
    assert public_pass_resp.headers["content-type"] == "application/pdf"
    assert public_pass_resp.content.startswith(b"%PDF")
    assert len(public_pass_resp.content) > 1000
