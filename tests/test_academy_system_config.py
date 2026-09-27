"""Test suite for Super-PRO Academic System: Programs, Study Plans, Credits & Grading Schemes."""

import uuid
import pytest

from backend import models
from tests.conftest import auth_headers, seed_admin
from backend.services.academic_engine_service import (
    validate_grading_scheme_cuts,
)


def test_validate_grading_scheme_cuts_logic():
    """Unit test for grading cut percentage validation."""
    # Valid 30-30-40 distribution
    valid_cuts = [
        {"name": "Corte 1", "weight_percent": 30.0},
        {"name": "Corte 2", "weight_percent": 30.0},
        {"name": "Corte 3", "weight_percent": 40.0},
    ]
    ok, err = validate_grading_scheme_cuts(valid_cuts)
    assert ok is True
    assert err == ""

    # Invalid: sums to 90%
    invalid_cuts = [
        {"name": "Corte 1", "weight_percent": 30.0},
        {"name": "Corte 2", "weight_percent": 30.0},
        {"name": "Corte 3", "weight_percent": 30.0},
    ]
    ok, err = validate_grading_scheme_cuts(invalid_cuts)
    assert ok is False
    assert "100.0%" in err

    # Invalid: negative or 0 weight
    bad_cut = [{"name": "Corte 1", "weight_percent": 0.0}]
    ok, err = validate_grading_scheme_cuts(bad_cut)
    assert ok is False


def test_program_lifecycle_and_config(client, db_session):
    """Test full CRUD on configurable formation processes (Diplomados, Carreras, etc.)."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    prog_code = f"CARR-TEO-{uuid.uuid4().hex[:6].upper()}"
    payload = {
        "code": prog_code,
        "name": "Licenciatura en Teología Pastoral",
        "description": "Formación integral para pastores y líderes",
        "program_type": "carrera",
        "level_name": "Pregrado Teológico",
        "total_duration_type": "semestres",
        "total_duration_units": 6,
        "total_credits": 120,
        "modality": "presencial",
        "has_teachers": True,
        "teachers_can_grade": True,
        "min_passing_grade": 70.0,
        "grading_scale_max": 100.0,
        "min_attendance_percent": 80.0,
        "is_active": True,
    }

    # 1. Create
    resp = client.post("/api/academy/admin/programs", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == prog_code
    assert data["program_type"] == "carrera"
    assert data["has_teachers"] is True
    assert data["teachers_can_grade"] is True
    program_id = data["id"]

    # 2. Duplicate code rejected
    resp_dup = client.post("/api/academy/admin/programs", json=payload, headers=headers)
    assert resp_dup.status_code == 409

    # 3. List
    resp_list = client.get("/api/academy/admin/programs", headers=headers)
    assert resp_list.status_code == 200
    programs = resp_list.json()
    assert any(p["id"] == program_id for p in programs)

    # 4. Update
    resp_upd = client.patch(
        f"/api/academy/admin/programs/{program_id}",
        json={"total_duration_units": 8, "total_credits": 140},
        headers=headers,
    )
    assert resp_upd.status_code == 200
    assert resp_upd.json()["total_duration_units"] == 8
    assert resp_upd.json()["total_credits"] == 140

    # 5. Delete (soft-delete)
    resp_del = client.delete(f"/api/academy/admin/programs/{program_id}", headers=headers)
    assert resp_del.status_code == 204

    # Verify not in active list
    resp_list2 = client.get("/api/academy/admin/programs", headers=headers)
    assert all(p["id"] != program_id for p in resp_list2.json())


def test_grading_scheme_cuts_validation_and_creation(client, db_session):
    """Test creating and rejecting grading schemes with custom cuts."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    # Try creating scheme that doesn't sum to 100% -> should fail with 422
    invalid_scheme = {
        "name": "Esquema Inválido 50-30",
        "scale_max": 100.0,
        "passing_grade": 70.0,
        "cuts": [
            {"name": "Corte 1", "order_index": 1, "weight_percent": 50.0},
            {"name": "Corte 2", "order_index": 2, "weight_percent": 30.0},
        ],
    }
    resp = client.post("/api/academy/admin/grading-schemes", json=invalid_scheme, headers=headers)
    assert resp.status_code == 422
    assert "100.0%" in resp.json()["detail"]

    # Valid scheme (30-30-40) -> should succeed
    valid_scheme = {
        "name": f"Esquema 30-30-40 Test {uuid.uuid4().hex[:4]}",
        "description": "Tres notas semestrales ponderadas",
        "scale_max": 100.0,
        "passing_grade": 70.0,
        "is_default": False,
        "cuts": [
            {"name": "Primer Parcial (30%)", "order_index": 1, "weight_percent": 30.0},
            {"name": "Segundo Parcial (30%)", "order_index": 2, "weight_percent": 30.0},
            {"name": "Proyecto Final (40%)", "order_index": 3, "weight_percent": 40.0},
        ],
    }
    resp_valid = client.post("/api/academy/admin/grading-schemes", json=valid_scheme, headers=headers)
    assert resp_valid.status_code == 201, resp_valid.text
    data = resp_valid.json()
    assert len(data["cuts"]) == 3
    assert data["cuts"][0]["weight_percent"] == 30.0
    assert data["cuts"][2]["weight_percent"] == 40.0


def test_study_plan_educational_credits_and_offerings(client, db_session):
    """Test study plan with subjects of unequal credits and weighted grade calculation."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    # 1. Create a program
    prog_resp = client.post(
        "/api/academy/admin/programs",
        json={
            "code": f"DIP-{uuid.uuid4().hex[:6].upper()}",
            "name": "Diplomado en Liderazgo Pastoral",
            "program_type": "diplomado",
            "total_duration_units": 2,
            "min_passing_grade": 70.0,
        },
        headers=headers,
    )
    prog_id = prog_resp.json()["id"]

    # 2. Create a study plan (pensum)
    plan_resp = client.post(
        "/api/academy/admin/study-plans",
        json={
            "program_id": prog_id,
            "code": f"PLAN-{uuid.uuid4().hex[:4].upper()}",
            "name": "Malla Curricular 2026",
            "total_levels": 2,
            "level_type": "semestre",
        },
        headers=headers,
    )
    assert plan_resp.status_code == 201
    plan_id = plan_resp.json()["id"]

    # 3. Add Subject 1: "Teología Fundamental" (4 Créditos Educativos)
    sub1_resp = client.post(
        f"/api/academy/admin/study-plans/{plan_id}/subjects",
        json={
            "code": f"TEO-101-{uuid.uuid4().hex[:4].upper()}",
            "name": "Teología Fundamental",
            "level_number": 1,
            "credits": 4,  # 4 créditos
            "weekly_hours_theory": 3,
            "weekly_hours_practice": 1,
            "is_mandatory": True,
        },
        headers=headers,
    )
    assert sub1_resp.status_code == 201
    sub1_id = sub1_resp.json()["id"]

    # 4. Add Subject 2: "Taller de Oratoria" (2 Créditos Educativos)
    sub2_resp = client.post(
        f"/api/academy/admin/study-plans/{plan_id}/subjects",
        json={
            "code": f"ORA-101-{uuid.uuid4().hex[:4].upper()}",
            "name": "Taller de Oratoria",
            "level_number": 1,
            "credits": 2,  # 2 créditos
            "weekly_hours_theory": 1,
            "weekly_hours_practice": 2,
            "is_mandatory": True,
        },
        headers=headers,
    )
    assert sub2_resp.status_code == 201
    sub2_id = sub2_resp.json()["id"]

    # Verify study plan credits recalculated to 4 + 2 = 6
    plan_check = client.get(f"/api/academy/admin/study-plans/{plan_id}", headers=headers)
    assert plan_check.json()["total_credits"] == 6

    # 5. Create Academic Period: "2026-I"
    period_resp = client.post(
        "/api/academy/admin/periods",
        json={
            "code": f"2026-I-{uuid.uuid4().hex[:4].upper()}",
            "name": "Semestre Académico 2026-I",
            "period_type": "semestral",
            "start_date": "2026-02-01",
            "end_date": "2026-06-30",
            "status": "open",
        },
        headers=headers,
    )
    assert period_resp.status_code == 201
    period_id = period_resp.json()["id"]

    # 6. Create Grading Scheme with 3 cuts: 30%, 30%, 40%
    scheme_resp = client.post(
        "/api/academy/admin/grading-schemes",
        json={
            "name": f"Esquema 30-30-40 #{uuid.uuid4().hex[:4]}",
            "scale_max": 100.0,
            "passing_grade": 70.0,
            "cuts": [
                {"name": "Corte 1", "order_index": 1, "weight_percent": 30.0},
                {"name": "Corte 2", "order_index": 2, "weight_percent": 30.0},
                {"name": "Corte 3", "order_index": 3, "weight_percent": 40.0},
            ],
        },
        headers=headers,
    )
    scheme_data = scheme_resp.json()
    scheme_id = scheme_data["id"]
    cuts = scheme_data["cuts"]
    cut1_id = cuts[0]["id"]
    cut2_id = cuts[1]["id"]
    cut3_id = cuts[2]["id"]

    # 7. Create Offering for Subject 1 (4 credits)
    offering_resp = client.post(
        "/api/academy/admin/offerings",
        json={
            "academic_period_id": period_id,
            "subject_id": sub1_id,
            "grading_scheme_id": scheme_id,
            "group_name": "Grupo A",
            "quota_max": 30,
        },
        headers=headers,
    )
    assert offering_resp.status_code == 201
    offering_id = offering_resp.json()["id"]

    # 8. Create a test student Persona
    student_id = uuid.uuid4()
    student = models.Persona(
        id=student_id,
        first_name="Juan",
        last_name="Estudiante",
        email=f"juan_{student_id.hex[:6]}@example.com",
    )
    db_session.add(student)
    db_session.commit()

    # 9. Submit Grades for Student in Offering (Corte 1: 80, Corte 2: 90, Corte 3: 100)
    grade_resp = client.post(
        f"/api/academy/admin/offerings/{offering_id}/grades",
        json={
            "offering_id": offering_id,
            "grades": [
                {"persona_id": str(student_id), "cut_id": cut1_id, "grade_value": 80.0},
                {"persona_id": str(student_id), "cut_id": cut2_id, "grade_value": 90.0},
                {"persona_id": str(student_id), "cut_id": cut3_id, "grade_value": 100.0},
            ],
        },
        headers=headers,
    )
    assert grade_resp.status_code == 200

    # 10. Check calculated final grade:
    # (80 * 0.3) + (90 * 0.3) + (100 * 0.4) = 24 + 27 + 40 = 91.0
    offering_grades = client.get(f"/api/academy/admin/offerings/{offering_id}/grades", headers=headers)
    assert offering_grades.status_code == 200
    records = offering_grades.json()["records"]
    assert len(records) == 1
    rec = records[0]
    assert rec["calculated_final_grade"] == 91.0
    assert rec["passed"] is True
    assert rec["credits_attempted"] == 4
    assert rec["credits_earned"] == 4

    # 11. Create Offering for Subject 2 (2 credits) & Grade it with 60.0 (Failed)
    offering2_resp = client.post(
        "/api/academy/admin/offerings",
        json={
            "academic_period_id": period_id,
            "subject_id": sub2_id,
            "grading_scheme_id": scheme_id,
            "group_name": "Grupo A",
            "quota_max": 30,
        },
        headers=headers,
    )
    offering2_id = offering2_resp.json()["id"]

    client.post(
        f"/api/academy/admin/offerings/{offering2_id}/grades",
        json={
            "offering_id": offering2_id,
            "grades": [
                {"persona_id": str(student_id), "cut_id": cut1_id, "grade_value": 60.0},
                {"persona_id": str(student_id), "cut_id": cut2_id, "grade_value": 60.0},
                {"persona_id": str(student_id), "cut_id": cut3_id, "grade_value": 60.0},
            ],
        },
        headers=headers,
    )

    # 12. Check Academic Transcript & Credit-Weighted GPA (PAPA):
    # Subject 1 (4 credits): 91.0 -> 91.0 * 4 = 364.0
    # Subject 2 (2 credits): 60.0 -> 60.0 * 2 = 120.0
    # Total weighted sum = 484.0 / (4 + 2 = 6 credits) = 80.67
    transcript_resp = client.get(f"/api/academy/admin/students/{student_id}/academic-record", headers=headers)
    assert transcript_resp.status_code == 200
    transcript = transcript_resp.json()
    assert transcript["total_credits_attempted"] == 6
    assert transcript["total_credits_earned"] == 4  # Subject 2 failed so 0 credits earned
    assert transcript["weighted_gpa"] == 80.67
    assert len(transcript["subjects"]) == 2
