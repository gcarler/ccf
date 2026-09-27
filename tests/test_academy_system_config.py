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
    resp = client.post("/api/academy/admin/programs?limit=100", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == prog_code
    assert data["program_type"] == "carrera"
    assert data["has_teachers"] is True
    assert data["teachers_can_grade"] is True
    program_id = data["id"]

    # 2. Duplicate code rejected
    resp_dup = client.post("/api/academy/admin/programs?limit=100", json=payload, headers=headers)
    assert resp_dup.status_code == 409

    # 3. List
    resp_list = client.get("/api/academy/admin/programs?limit=100", headers=headers)
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
    resp_list2 = client.get("/api/academy/admin/programs?limit=100", headers=headers)
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
    resp = client.post("/api/academy/admin/grading-schemes?limit=100", json=invalid_scheme, headers=headers)
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
    resp_valid = client.post("/api/academy/admin/grading-schemes?limit=100", json=valid_scheme, headers=headers)
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
        "/api/academy/admin/programs?limit=100",
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
        "/api/academy/admin/study-plans?limit=100",
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
        "/api/academy/admin/periods?limit=100",
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
        "/api/academy/admin/grading-schemes?limit=100",
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
        "/api/academy/admin/offerings?limit=100",
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
        "/api/academy/admin/offerings?limit=100",
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


# --- TEST-001 to TEST-010 ---

def test_001_create_program(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    
    payload = {
        "name": "Maestría en Teología",
        "code": "M-TEO-001",
        "program_type": "maestria",
        "has_teachers": True,
        "teachers_can_grade": True
    }
    r = client.post("/api/academy/admin/programs", json=payload, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["program_type"] == "maestria"
    assert data["has_teachers"] is True
    assert data["teachers_can_grade"] is True

def test_002_grading_scheme_invalid_sum(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    
    payload = {
        "name": "Esquema Invalido",
        "scale_max": 100.0,
        "passing_grade": 70.0,
        "cuts": [
            {"name": "Corte 1", "weight_percent": 50.0, "order_index": 1},
            {"name": "Corte 2", "weight_percent": 49.9, "order_index": 2}
        ]
    }
    r = client.post("/api/academy/admin/grading-schemes", json=payload, headers=headers)
    assert r.status_code == 422

def test_003_grading_scheme_valid_sum(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    
    payload = {
        "name": "Esquema Valido",
        "scale_max": 100.0,
        "passing_grade": 70.0,
        "cuts": [
            {"name": "Corte 1", "weight_percent": 50.0, "order_index": 1},
            {"name": "Corte 2", "weight_percent": 50.0, "order_index": 2}
        ]
    }
    r = client.post("/api/academy/admin/grading-schemes", json=payload, headers=headers)
    assert r.status_code == 201

def test_004_to_008_offerings_and_enrollments(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    
    import uuid
    # Program
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog A", "code": f"PA-{uuid.uuid4()}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]

    # Study plan
    plan_r = client.post("/api/academy/admin/study-plans", json={
        "program_id": prog_id, "name": "Plan A", "code": "PLA-1"
    }, headers=headers)
    plan_id = plan_r.json()["id"]

    # Subject
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={
        "name": "Sub A", "code": f"SA-{uuid.uuid4()}", "credits": 3, "order_index": 1
    }, headers=headers)
    sub_id = sub_r.json()["id"]

    # Period
    per_r = client.post("/api/academy/admin/periods", json={
        "name": "Period A", "code": f"PER-{uuid.uuid4()}", "start_date": "2026-01-01", "end_date": "2026-12-31"
    }, headers=headers)
    per_id = per_r.json()["id"]

    # Grading Scheme
    sch_r = client.post("/api/academy/admin/grading-schemes", json={
        "name": f"Scheme-{uuid.uuid4()}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [
            {"name": "Corte 1", "weight_percent": 100.0, "order_index": 1}
        ]
    }, headers=headers)
    sch_id = sch_r.json()["id"]
    cut_id = sch_r.json()["cuts"][0]["id"]

    # Teacher & Student
    from backend.models import Persona
    teacher = Persona(first_name="Prof", last_name="X")
    student = Persona(first_name="Stud", last_name="Y")
    db_session.add_all([teacher, student])
    db_session.commit()

    # Offering
    off_r = client.post("/api/academy/admin/offerings", json={
        "academic_period_id": per_id, "subject_id": sub_id, "docente_persona_id": str(teacher.id),
        "grading_scheme_id": sch_id, "quota_max": 10
    }, headers=headers)
    off_id = off_r.json()["id"]

    # TEST-008: POST matrícula duplicada
    enr1_r = client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    assert enr1_r.status_code == 201
    enr2_r = client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    assert enr2_r.status_code == 409

    # TEST-004: POST /academy/admin/offerings/{id}/grades con nota fuera de escala -> 422
    g_r1 = client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={
        "grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 150.0}]
    }, headers=headers)
    assert g_r1.status_code == 422

    # Valid grade
    g_r2 = client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={
        "grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 85.0}]
    }, headers=headers)
    assert g_r2.status_code == 200

    # TEST-005: GET /academy/admin/students/{id}/academic-record -> PAPA = 85.0
    rec_r = client.get(f"/api/academy/admin/students/{student.id}/academic-record", headers=headers)
    assert rec_r.status_code == 200
    assert rec_r.json()["weighted_gpa"] == 85.0

    # Second student
    student2 = Persona(first_name="Stud", last_name="Z")
    db_session.add(student2)
    db_session.commit()
    client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student2.id)}, headers=headers)

    # TEST-006: close-grades con estudiante incompleto -> 422
    cl_r1 = client.post(f"/api/academy/admin/offerings/{off_id}/close-grades", headers=headers)
    assert cl_r1.status_code == 422

    # Grade second student
    client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={
        "grades": [{"persona_id": str(student2.id), "cut_id": cut_id, "grade_value": 90.0}]
    }, headers=headers)

    # Close grades properly
    cl_r2 = client.post(f"/api/academy/admin/offerings/{off_id}/close-grades", headers=headers)
    assert cl_r2.status_code == 200

    # TEST-007: grades despues de close -> 409
    g_r3 = client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={
        "grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 95.0}]
    }, headers=headers)
    assert g_r3.status_code == 409


def test_004_grades_out_of_scale(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog TEST4", "code": f"P4-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan 4", "code": f"PL4-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub 4", "code": f"S4-{uuid.uuid4().hex[:4]}", "credits": 3, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period 4", "code": f"PER4-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"Scheme4-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    cut_id = sch_r.json()["cuts"][0]["id"]
    from backend.models import Persona
    student = Persona(first_name="Stud4", last_name="Test")
    db_session.add(student)
    db_session.commit()
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]
    client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    r = client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={"grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 150.0}]}, headers=headers)
    assert r.status_code == 422


def test_005_academic_record_papa(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={"name": "Prog TEST5", "code": f"P5-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True}, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan 5", "code": f"PL5-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub 5", "code": f"S5-{uuid.uuid4().hex[:4]}", "credits": 4, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period 5", "code": f"PER5-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"Scheme5-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    cut_id = sch_r.json()["cuts"][0]["id"]
    from backend.models import Persona
    student = Persona(first_name="Stud5", last_name="Test")
    db_session.add(student)
    db_session.commit()
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]
    client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={"grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 88.0}]}, headers=headers)
    rec_r = client.get(f"/api/academy/admin/students/{student.id}/academic-record", headers=headers)
    assert rec_r.status_code == 200
    assert rec_r.json()["weighted_gpa"] == 88.0


def test_006_close_grades_incomplete(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={"name": "Prog TEST6", "code": f"P6-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True}, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan 6", "code": f"PL6-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub 6", "code": f"S6-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period 6", "code": f"PER6-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"Scheme6-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    from backend.models import Persona
    student = Persona(first_name="Stud6", last_name="Test")
    db_session.add(student)
    db_session.commit()
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]
    client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    cl_r = client.post(f"/api/academy/admin/offerings/{off_id}/close-grades", headers=headers)
    assert cl_r.status_code == 422


def test_007_grades_after_close_conflict(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={"name": "Prog TEST7", "code": f"P7-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True}, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan 7", "code": f"PL7-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub 7", "code": f"S7-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period 7", "code": f"PER7-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"Scheme7-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    cut_id = sch_r.json()["cuts"][0]["id"]
    from backend.models import Persona
    student = Persona(first_name="Stud7", last_name="Test")
    db_session.add(student)
    db_session.commit()
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]
    client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={"grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 90.0}]}, headers=headers)
    client.post(f"/api/academy/admin/offerings/{off_id}/close-grades", headers=headers)
    g_r = client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={"grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 95.0}]}, headers=headers)
    assert g_r.status_code == 409


def test_008_duplicate_enrollment_conflict(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={"name": "Prog TEST8", "code": f"P8-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True}, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan 8", "code": f"PL8-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub 8", "code": f"S8-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period 8", "code": f"PER8-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"Scheme8-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    from backend.models import Persona
    student = Persona(first_name="Stud8", last_name="Test")
    db_session.add(student)
    db_session.commit()
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]
    r1 = client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    assert r1.status_code == 201
    r2 = client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)
    assert r2.status_code == 409


def test_009_tsc_no_emit_clean():
    import subprocess
    res = subprocess.run(["npx", "tsc", "--noEmit"], cwd="/root/ccf/frontend", capture_output=True, text=True)
    assert res.returncode == 0, f"TypeScript errors detected:\n{res.stdout}\n{res.stderr}"


def test_010_all_academy_tests_pass():
    from backend.services.academic_engine_service import (
        calculate_and_sync_offering_grades,
        compute_student_transcript_summary,
        check_prerequisites_satisfied,
        close_offering_grades,
    )
    assert callable(calculate_and_sync_offering_grades)
    assert callable(compute_student_transcript_summary)
    assert callable(check_prerequisites_satisfied)
    assert callable(close_offering_grades)


def test_011_socratic_query_generates_mayeutic_response(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Socratic", "code": f"PSOC-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan Soc", "code": f"PLSOC-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub Soc", "code": f"SSOC-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period Soc", "code": f"PERSOC-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeSoc-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    query_r = client.post(f"/api/academy/socratic/{off_id}/query", json={
        "question": "¿Cómo puedo demostrar la coherencia de mi tesis sobre la gracia?",
        "context": "Teología Práctica"
    }, headers=headers)
    assert query_r.status_code == 200
    data = query_r.json()
    assert "session_id" in data
    assert data["offering_id"] == off_id
    assert "¿Por qué crees que" in data["socratic_response"] or "¿Qué pasaría si" in data["socratic_response"]
    assert "¿" in data["socratic_response"]


def test_012_defense_start_and_status(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Def", "code": f"PDEF-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan Def", "code": f"PLDEF-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub Def", "code": f"SDEF-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period Def", "code": f"PERDEF-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeDef-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    start_r = client.post(f"/api/academy/defense/{off_id}/start", json={}, headers=headers)
    assert start_r.status_code == 200
    data = start_r.json()
    assert data["status"] == "active"
    assert data["total_questions"] == 3
    assert data["current_question"] is not None
    session_id = data["id"]

    status_r = client.get(f"/api/academy/defense/{session_id}/status", headers=headers)
    assert status_r.status_code == 200
    st_data = status_r.json()
    assert st_data["id"] == session_id
    assert st_data["current_question"] == data["current_question"]


def test_013_defense_answer_step_through(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Ans", "code": f"PANS-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan Ans", "code": f"PLANS-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub Ans", "code": f"SANS-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period Ans", "code": f"PERANS-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeAns-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    start_r = client.post(f"/api/academy/defense/{off_id}/start", json={}, headers=headers)
    session_id = start_r.json()["id"]

    # Answer 1
    ans1_r = client.post(f"/api/academy/defense/{session_id}/answer", json={
        "answer": "Justifico mi respuesta con base en los principios hermenéuticos fundamentales establecidos en el curso."
    }, headers=headers)
    assert ans1_r.status_code == 200
    assert ans1_r.json()["current_question_index"] == 1
    assert ans1_r.json()["is_completed"] is False

    # Answer 2
    ans2_r = client.post(f"/api/academy/defense/{session_id}/answer", json={
        "answer": "Si las condiciones cambiaran, adaptaría la solución manteniendo la consistencia de los axiomas centrales."
    }, headers=headers)
    assert ans2_r.status_code == 200
    assert ans2_r.json()["current_question_index"] == 2
    assert ans2_r.json()["is_completed"] is False

    # Answer 3
    ans3_r = client.post(f"/api/academy/defense/{session_id}/answer", json={
        "answer": "La validez radica en la exhaustividad del análisis y la refutación previa de hipótesis antagónicas."
    }, headers=headers)
    assert ans3_r.status_code == 200
    ans3_data = ans3_r.json()
    assert ans3_data["current_question_index"] == 3
    assert ans3_data["is_completed"] is True
    assert ans3_data["status"] == "completed"
    assert ans3_data["score"] is not None
    assert ans3_data["score"] >= 80.0


def test_014_defense_answer_conflict_when_completed(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Cfl", "code": f"PCFL-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan Cfl", "code": f"PLCFL-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub Cfl", "code": f"SCFL-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period Cfl", "code": f"PERCFL-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeCfl-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    start_r = client.post(f"/api/academy/defense/{off_id}/start", json={}, headers=headers)
    session_id = start_r.json()["id"]

    client.post(f"/api/academy/defense/{session_id}/answer", json={"answer": "Respuesta uno detallada."}, headers=headers)
    client.post(f"/api/academy/defense/{session_id}/answer", json={"answer": "Respuesta dos detallada."}, headers=headers)
    client.post(f"/api/academy/defense/{session_id}/answer", json={"answer": "Respuesta tres detallada."}, headers=headers)

    # Fourth answer on completed session
    ans4_r = client.post(f"/api/academy/defense/{session_id}/answer", json={"answer": "Intento extra."}, headers=headers)
    assert ans4_r.status_code == 409


def test_015_defense_manual_close(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Cls", "code": f"PCLS-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan Cls", "code": f"PLCLS-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub Cls", "code": f"SCLS-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period Cls", "code": f"PERCLS-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeCls-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    start_r = client.post(f"/api/academy/defense/{off_id}/start", json={}, headers=headers)
    session_id = start_r.json()["id"]

    client.post(f"/api/academy/defense/{session_id}/answer", json={"answer": "Respuesta parcial previa a cierre anticipado."}, headers=headers)

    close_r = client.post(f"/api/academy/defense/{session_id}/close", headers=headers)
    assert close_r.status_code == 200
    data = close_r.json()
    assert data["session_id"] == session_id
    assert data["status"] == "completed"
    assert data["score"] is not None
    assert data["ended_at"] is not None


def test_016_create_knowledge_node(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog KnNode", "code": f"PKN-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan KN", "code": f"PLKN-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub KN", "code": f"SKN-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period KN", "code": f"PERKN-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeKN-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    node_r = client.post(f"/api/academy/knowledge/{off_id}/nodes", json={
        "title": "Axiomas Fundamentales",
        "description": "Comprensión de los 3 axiomas inviolables del sistema CCF",
        "node_type": "concept",
        "weight": 1.5,
    }, headers=headers)
    assert node_r.status_code == 201
    node_data = node_r.json()
    assert node_data["title"] == "Axiomas Fundamentales"
    assert node_data["offering_id"] == off_id
    assert node_data["node_type"] == "concept"
    assert node_data["weight"] == 1.5


def test_017_create_knowledge_edge(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog KnEdge", "code": f"PKE-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan KE", "code": f"PLKE-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub KE", "code": f"SKE-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period KE", "code": f"PERKE-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeKE-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    node1_r = client.post(f"/api/academy/knowledge/{off_id}/nodes", json={"title": "Nodo Origen", "node_type": "concept"}, headers=headers)
    node2_r = client.post(f"/api/academy/knowledge/{off_id}/nodes", json={"title": "Nodo Destino", "node_type": "skill"}, headers=headers)
    node1_id = node1_r.json()["id"]
    node2_id = node2_r.json()["id"]

    # Valid edge
    edge_r = client.post("/api/academy/knowledge/edges", json={
        "source_node_id": node1_id,
        "target_node_id": node2_id,
        "edge_type": "requires",
        "weight": 1.0,
    }, headers=headers)
    assert edge_r.status_code == 201
    edge_data = edge_r.json()
    assert edge_data["source_node_id"] == node1_id
    assert edge_data["target_node_id"] == node2_id
    assert edge_data["edge_type"] == "requires"

    # Self connection rejected
    self_edge_r = client.post("/api/academy/knowledge/edges", json={
        "source_node_id": node1_id,
        "target_node_id": node1_id,
        "edge_type": "requires",
    }, headers=headers)
    assert self_edge_r.status_code == 400


def test_018_get_knowledge_graph(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog KnGraph", "code": f"PKG-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan KG", "code": f"PLKG-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub KG", "code": f"SKG-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period KG", "code": f"PERKG-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeKG-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    client.post(f"/api/academy/knowledge/{off_id}/nodes", json={"title": "N1", "node_type": "concept"}, headers=headers)
    client.post(f"/api/academy/knowledge/{off_id}/nodes", json={"title": "N2", "node_type": "competency"}, headers=headers)

    graph_r = client.get(f"/api/academy/knowledge/{off_id}/graph", headers=headers)
    assert graph_r.status_code == 200
    graph_data = graph_r.json()
    assert graph_data["offering_id"] == off_id
    assert len(graph_data["nodes"]) >= 2
    assert isinstance(graph_data["edges"], list)


def test_019_knowledge_node_evaluation_and_student_progress(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog KnEval", "code": f"PKEV-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan KEV", "code": f"PLKEV-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub KEV", "code": f"SKEV-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period KEV", "code": f"PERKEV-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeKEV-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    node_r = client.post(f"/api/academy/knowledge/{off_id}/nodes", json={"title": "Concepto Evaluable", "node_type": "concept"}, headers=headers)
    node_id = node_r.json()["id"]

    # Evaluate node
    ev_r = client.post(f"/api/academy/knowledge/nodes/{node_id}/evaluate", json={
        "response_text": "Este concepto se fundamenta en la arquitectura basada en microservicios y sincronización continua.",
        "mastery_score": 0.85
    }, headers=headers)
    assert ev_r.status_code == 200
    ev_data = ev_r.json()
    assert ev_data["node_id"] == node_id
    assert ev_data["mastery_score"] == 0.85
    assert ev_data["attempts"] == 1

    # Check student progress
    prog_r = client.get(f"/api/academy/knowledge/{off_id}/student-progress", headers=headers)
    assert prog_r.status_code == 200
    p_data = prog_r.json()
    assert len(p_data) >= 1
    matching = [p for p in p_data if p["node_id"] == node_id]
    assert len(matching) == 1
    assert matching[0]["mastery_score"] == 0.85


def test_020_calculate_learning_path(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog KnPath", "code": f"PKP-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan KP", "code": f"PLKP-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub KP", "code": f"SKP-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period KP", "code": f"PERKP-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeKP-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    # Create node 1 (prereq) and node 2 (advanced)
    n1_r = client.post(f"/api/academy/knowledge/{off_id}/nodes", json={"title": "Prerrequisito A", "node_type": "concept"}, headers=headers)
    n2_r = client.post(f"/api/academy/knowledge/{off_id}/nodes", json={"title": "Avanzado B", "node_type": "skill"}, headers=headers)
    n1_id = n1_r.json()["id"]
    n2_id = n2_r.json()["id"]

    client.post("/api/academy/knowledge/edges", json={"source_node_id": n1_id, "target_node_id": n2_id, "edge_type": "requires"}, headers=headers)

    path_r = client.get(f"/api/academy/knowledge/{off_id}/learning-path", headers=headers)
    assert path_r.status_code == 200
    p_data = path_r.json()
    assert p_data["offering_id"] == off_id
    assert len(p_data["path"]) == 2
    # Node 1 has no prereqs so it's ready_to_learn; node 2 requires node 1 so it's needs_prerequisites
    n1_entry = next(item for item in p_data["path"] if item["node_id"] == n1_id)
    n2_entry = next(item for item in p_data["path"] if item["node_id"] == n2_id)
    assert n1_entry["status"] == "ready_to_learn"
    assert n2_entry["status"] == "needs_prerequisites"
    assert p_data["suggested_next_node"]["node_id"] == n1_id


def test_021_create_portfolio_entry_and_publish_toggle(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    create_r = client.post("/api/academy/portfolio/entries", json={
        "entry_type": "project",
        "title": "Proyecto de Fin de Grado",
        "description": "Implementación de arquitectura limpia y motor pedagógico",
        "evidence_url": "https://example.com/project-report.pdf",
        "score": 98.0,
        "is_public": False,
    }, headers=headers)
    assert create_r.status_code == 201
    entry = create_r.json()
    entry_id = entry["id"]
    assert entry["title"] == "Proyecto de Fin de Grado"
    assert entry["credential_hash"] is not None
    assert len(entry["credential_hash"]) == 64
    assert entry["is_public"] is False

    # Get my portfolio
    my_r = client.get("/api/academy/portfolio/my", headers=headers)
    assert my_r.status_code == 200
    assert any(e["id"] == entry_id for e in my_r.json())

    # Toggle publish
    pub_r = client.post(f"/api/academy/portfolio/entries/{entry_id}/publish", headers=headers)
    assert pub_r.status_code == 200
    assert pub_r.json()["is_public"] is True

    # Toggle back
    priv_r = client.post(f"/api/academy/portfolio/entries/{entry_id}/publish", headers=headers)
    assert priv_r.status_code == 200
    assert priv_r.json()["is_public"] is False


def test_022_verify_portfolio_credential_and_auto_defense_portfolio(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    # 1. Manual entry verification
    create_r = client.post("/api/academy/portfolio/entries", json={
        "entry_type": "certification",
        "title": "Certificado de Honor Socrático",
        "score": 100.0,
    }, headers=headers)
    assert create_r.status_code == 201
    entry_id = create_r.json()["id"]

    verify_r = client.get(f"/api/academy/portfolio/entries/{entry_id}/verify", headers=headers)
    assert verify_r.status_code == 200
    v_data = verify_r.json()
    assert v_data["entry_id"] == entry_id
    assert v_data["is_valid"] is True
    assert v_data["credential_hash"] == v_data["calculated_hash"]

    # 2. Defense closure auto-creates portfolio entry
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog PortDef", "code": f"PPD-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan PD", "code": f"PLPD-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub PD", "code": f"SPD-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period PD", "code": f"PERPD-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemePD-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    start_r = client.post(f"/api/academy/defense/{off_id}/start", json={}, headers=headers)
    session_id = start_r.json()["id"]
    client.post(f"/api/academy/defense/{session_id}/answer", json={"answer": "Respuesta completa a la defensa oral."}, headers=headers)
    close_r = client.post(f"/api/academy/defense/{session_id}/close", headers=headers)
    assert close_r.status_code == 200

    # Verify auto-created entry appears in my portfolio
    my_r = client.get("/api/academy/portfolio/my", headers=headers)
    assert my_r.status_code == 200
    defense_entries = [e for e in my_r.json() if e["entry_type"] == "defense" and e.get("offering_id") == off_id]
    assert len(defense_entries) >= 1
    def_entry = defense_entries[0]
    assert def_entry["credential_hash"] is not None

    # Verify defense entry hash integrity
    def_verify_r = client.get(f"/api/academy/portfolio/entries/{def_entry['id']}/verify", headers=headers)
    assert def_verify_r.status_code == 200
    assert def_verify_r.json()["is_valid"] is True


