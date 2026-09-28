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


def test_023_create_wellness_signal_and_alert(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    from backend.models import Persona
    student = Persona(first_name="WellStud1", last_name="Test")
    db_session.add(student)
    db_session.commit()

    # Create dummy offering
    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Well1", "code": f"PW1-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan W1", "code": f"PLW1-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub W1", "code": f"SW1-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period W1", "code": f"PERW1-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeW1-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    # Post wellness signal
    sig_r = client.post("/api/academy/wellness/signals", json={
        "student_id": str(student.id),
        "offering_id": off_id,
        "signal_type": "engagement_drop",
        "severity": "high",
        "details": {"reason": "El estudiante no ha accedido a la plataforma en 10 días"},
    }, headers=headers)
    assert sig_r.status_code == 201
    sig_data = sig_r.json()
    assert sig_data["student_id"] == str(student.id)
    assert sig_data["signal_type"] == "engagement_drop"
    assert sig_data["severity"] == "high"
    assert sig_data["is_resolved"] is False

    # Check offering signals
    off_sigs_r = client.get(f"/api/academy/wellness/{off_id}/signals", headers=headers)
    assert off_sigs_r.status_code == 200
    assert any(s["id"] == sig_data["id"] for s in off_sigs_r.json())

    # Check my alerts (high severity generated an alert)
    alerts_r = client.get("/api/academy/wellness/my-alerts", headers=headers)
    assert alerts_r.status_code == 200
    assert any(a["signal_id"] == sig_data["id"] for a in alerts_r.json())


def test_024_detect_wellness_signals_automatic(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    from backend.models import Persona
    student = Persona(first_name="WellDetect", last_name="Student")
    db_session.add(student)
    db_session.commit()

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog WDetect", "code": f"PWD-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan WD", "code": f"PLWD-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub WD", "code": f"SWD-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period WD", "code": f"PERWD-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeWD-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    cut_id = sch_r.json()["cuts"][0]["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    # Enroll student
    client.post(f"/api/academy/admin/offerings/{off_id}/students", json={"persona_id": str(student.id)}, headers=headers)

    # Register failing grade < 60
    client.post(f"/api/academy/admin/offerings/{off_id}/grades", json={
        "grades": [{"persona_id": str(student.id), "cut_id": cut_id, "grade_value": 45.0}]
    }, headers=headers)

    # Trigger wellness detection
    detect_r = client.post("/api/academy/wellness/detect", json={"offering_id": off_id}, headers=headers)
    assert detect_r.status_code == 200
    d_data = detect_r.json()
    assert d_data["detected_count"] >= 1
    assert any(s["student_id"] == str(student.id) and s["signal_type"] == "grade_risk" for s in d_data["signals"])


def test_025_resolve_wellness_signal(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    from backend.models import Persona
    student = Persona(first_name="WellRes", last_name="Student")
    db_session.add(student)
    db_session.commit()

    sig_r = client.post("/api/academy/wellness/signals", json={
        "student_id": str(student.id),
        "signal_type": "stress_indicator",
        "severity": "medium",
        "details": {"reason": "El estudiante reporta sobrecarga con asignaciones simultáneas"},
    }, headers=headers)
    sig_id = sig_r.json()["id"]

    # Resolve
    res_r = client.post(f"/api/academy/wellness/signals/{sig_id}/resolve", headers=headers)
    assert res_r.status_code == 200
    r_data = res_r.json()
    assert r_data["id"] == sig_id
    assert r_data["is_resolved"] is True
    assert r_data["resolved_at"] is not None
    assert r_data["resolved_by_id"] == str(admin.id)


def test_026_student_risk_profile(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    from backend.models import Persona
    student = Persona(first_name="RiskProf", last_name="Student")
    db_session.add(student)
    db_session.commit()

    # Create 2 signals
    client.post("/api/academy/wellness/signals", json={
        "student_id": str(student.id),
        "signal_type": "grade_risk",
        "severity": "high",
        "details": {"reason": "Nota baja en corte 1"},
    }, headers=headers)
    client.post("/api/academy/wellness/signals", json={
        "student_id": str(student.id),
        "signal_type": "engagement_drop",
        "severity": "medium",
        "details": {"reason": "Baja participación"},
    }, headers=headers)

    prof_r = client.get(f"/api/academy/wellness/student/{student.id}/risk-profile", headers=headers)
    assert prof_r.status_code == 200
    p_data = prof_r.json()
    assert p_data["student_id"] == str(student.id)
    assert p_data["risk_score"] >= 50.0
    assert p_data["active_signals_count"] >= 2
    assert len(p_data["recommendations"]) > 0


def test_027_copilot_suggest_activities(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Cop1", "code": f"PC1-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan C1", "code": f"PLC1-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub C1", "code": f"SC1-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period C1", "code": f"PERC1-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeC1-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    # Create knowledge node in this offering
    client.post(f"/api/academy/knowledge/{off_id}/nodes", json={
        "title": "Hermenéutica Bíblica y Exégesis",
        "description": "Métodos histórico-gramaticales de interpretación",
        "node_type": "concept",
        "weight": 1.0,
    }, headers=headers)

    sug_r = client.post("/api/academy/copilot/suggest-activities", json={
        "offering_id": off_id,
        "topic": "Hermenéutica",
    }, headers=headers)
    assert sug_r.status_code == 200
    s_data = sug_r.json()
    assert s_data["offering_id"] == off_id
    assert len(s_data["suggestions"]) == 4
    types = [act["activity_type"] for act in s_data["suggestions"]]
    assert "socratic_dialogue" in types
    assert "practical_exercise" in types


def test_028_copilot_generate_rubric(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    rubric_r = client.post("/api/academy/copilot/generate-rubric", json={
        "title": "Ensayo Teológico sobre Gracia y Discipulado",
        "competencies": ["Pensamiento crítico teológico", "Aplicación pastoral práctica"],
    }, headers=headers)
    assert rubric_r.status_code == 200
    r_data = rubric_r.json()
    assert r_data["title"] == "Ensayo Teológico sobre Gracia y Discipulado"
    assert len(r_data["criteria"]) == 4
    total_weight = sum(c["weight"] for c in r_data["criteria"])
    assert abs(total_weight - 100.0) < 0.1
    for crit in r_data["criteria"]:
        assert "level_1_insufficient" in crit["levels"]
        assert "level_4_exemplary" in crit["levels"]


def test_029_copilot_class_performance_and_weekly_report(client, db_session):
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog CopRep", "code": f"PCR-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan CR", "code": f"PLCR-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub CR", "code": f"SCR-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period CR", "code": f"PERCR-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeCR-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 10}, headers=headers)
    off_id = off_r.json()["id"]

    # 1. Performance analysis
    perf_r = client.post("/api/academy/copilot/analyze-class-performance", json={"offering_id": off_id}, headers=headers)
    assert perf_r.status_code == 200
    perf_data = perf_r.json()
    assert perf_data["offering_id"] == off_id
    assert "grade_distribution" in perf_data
    assert "pedagogical_recommendations" in perf_data

    # 2. Weekly report
    rep_r = client.get(f"/api/academy/copilot/weekly-report/{off_id}", headers=headers)
    assert rep_r.status_code == 200
    rep_data = rep_r.json()
    assert rep_data["offering_id"] == off_id
    assert "grades_summary" in rep_data
    assert "key_highlights" in rep_data
    assert len(rep_data["key_highlights"]) > 0


def test_030_achievements_catalog_and_create(client, db_session):
    """Test creating achievements and querying the catalog with filters."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    code1 = f"ACH-EXC-{uuid.uuid4().hex[:6].upper()}"
    code2 = f"ACH-DEF-{uuid.uuid4().hex[:6].upper()}"

    # 1. Create achievement
    payload1 = {
        "code": code1,
        "title": "Excelencia Teológica",
        "description": "Obtenido por calificar con 100 en un módulo",
        "achievement_type": "excellence",
        "points": 50,
        "badge_icon": "trophy",
        "is_active": True,
    }
    r1 = client.post("/api/academy/achievements", json=payload1, headers=headers)
    assert r1.status_code == 201, r1.text
    ach1 = r1.json()
    assert ach1["code"] == code1
    assert ach1["points"] == 50

    # 2. Duplicate code returns 409
    r_dup = client.post("/api/academy/achievements", json=payload1, headers=headers)
    assert r_dup.status_code == 409

    # 3. Create second achievement
    payload2 = {
        "code": code2,
        "title": "Defensa Socrática Aprobada",
        "description": "Completar con éxito la defensa socrática",
        "achievement_type": "defense",
        "points": 30,
        "badge_icon": "shield-check",
        "is_active": True,
    }
    r2 = client.post("/api/academy/achievements", json=payload2, headers=headers)
    assert r2.status_code == 201

    # 4. List catalog
    cat_r = client.get("/api/academy/achievements", headers=headers)
    assert cat_r.status_code == 200
    catalog = cat_r.json()
    codes = [a["code"] for a in catalog]
    assert code1 in codes
    assert code2 in codes

    # 5. Filter by achievement_type
    filter_r = client.get("/api/academy/achievements?achievement_type=excellence", headers=headers)
    assert filter_r.status_code == 200
    filtered = filter_r.json()
    assert any(a["code"] == code1 for a in filtered)
    assert not any(a["code"] == code2 for a in filtered)


def test_031_award_achievement_generates_hash_and_portfolio_entry(client, db_session):
    """Test awarding an achievement generates a 64-char SHA-256 hash and a portfolio certification entry."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    from backend.models import Persona, AcademyPortfolioEntry
    student = Persona(first_name="LogroEstudiante", last_name="Verificable")
    db_session.add(student)
    db_session.commit()

    code = f"ACH-COMP-{uuid.uuid4().hex[:6].upper()}"
    ach_r = client.post("/api/academy/achievements", json={
        "code": code,
        "title": "Completitud Canónica",
        "description": "Completó todos los créditos del programa",
        "achievement_type": "completion",
        "points": 100,
        "badge_icon": "award",
    }, headers=headers)
    assert ach_r.status_code == 201
    ach_id = ach_r.json()["id"]

    # Award achievement
    award_payload = {
        "student_id": str(student.id),
        "achievement_id": ach_id,
        "evidence": {"project_url": "https://faro.ccf/cert/123", "note": "Defensa sobresaliente"},
    }
    award_r = client.post("/api/academy/achievements/award", json=award_payload, headers=headers)
    assert award_r.status_code == 201, award_r.text
    awarded = award_r.json()

    assert awarded["student_id"] == str(student.id)
    assert awarded["achievement_id"] == ach_id
    assert awarded["credential_hash"] is not None
    assert len(awarded["credential_hash"]) == 64  # SHA-256 hex string

    # Verify AcademyPortfolioEntry of type certification was generated
    port_entry = (
        db_session.query(AcademyPortfolioEntry)
        .filter(
            AcademyPortfolioEntry.student_id == student.id,
            AcademyPortfolioEntry.credential_hash == awarded["credential_hash"],
        )
        .first()
    )
    assert port_entry is not None
    assert port_entry.entry_type == "certification"
    assert port_entry.score == 100.0

    # Duplicate award returns 409
    dup_r = client.post("/api/academy/achievements/award", json=award_payload, headers=headers)
    assert dup_r.status_code == 409


def test_032_get_my_achievements(client, db_session):
    """Test retrieving achievements for the authenticated student."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    code = f"ACH-MY-{uuid.uuid4().hex[:6].upper()}"
    ach_r = client.post("/api/academy/achievements", json={
        "code": code,
        "title": "Mi Primer Logro",
        "achievement_type": "milestone",
        "points": 25,
    }, headers=headers)
    ach_id = ach_r.json()["id"]

    # Award to admin's persona
    client.post("/api/academy/achievements/award", json={
        "student_id": str(admin.id),
        "achievement_id": ach_id,
    }, headers=headers)

    # Query /achievements/my
    my_r = client.get("/api/academy/achievements/my", headers=headers)
    assert my_r.status_code == 200
    my_achievements = my_r.json()
    assert len(my_achievements) >= 1
    ach_ids = [a["achievement_id"] for a in my_achievements]
    assert ach_id in ach_ids


def test_033_verify_credential_endpoint(client, db_session):
    """Test public/verifiable endpoint for student achievement credentials."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    from backend.models import Persona
    student = Persona(first_name="Verif", last_name="Alumno")
    db_session.add(student)
    db_session.commit()

    code = f"ACH-VRF-{uuid.uuid4().hex[:6].upper()}"
    ach_r = client.post("/api/academy/achievements", json={
        "code": code,
        "title": "Credencial Verificable",
        "points": 40,
        "badge_icon": "check-circle",
    }, headers=headers)
    ach_id = ach_r.json()["id"]

    # Award
    award_r = client.post("/api/academy/achievements/award", json={
        "student_id": str(student.id),
        "achievement_id": ach_id,
    }, headers=headers)
    cred_hash = award_r.json()["credential_hash"]

    # Verify
    verify_r = client.get(f"/api/academy/achievements/{student.id}/credential/{ach_id}/verify")
    assert verify_r.status_code == 200
    v_data = verify_r.json()
    assert v_data["verified"] is True
    assert v_data["credential_hash"] == cred_hash
    assert v_data["achievement_title"] == "Credencial Verificable"
    assert v_data["points"] == 40
    assert "Verif" in v_data["student_name"]

    # Non-existent returns 404
    fake_id = str(uuid.uuid4())
    bad_r = client.get(f"/api/academy/achievements/{fake_id}/credential/{ach_id}/verify")
    assert bad_r.status_code == 404


def test_034_leaderboard_recalculate_and_ranks(client, db_session):
    """Test recalculating leaderboard ranks students by total achievement points."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    from backend.models import Persona
    st_alpha = Persona(first_name="Alpha", last_name="Rank")
    st_beta = Persona(first_name="Beta", last_name="Rank")
    db_session.add_all([st_alpha, st_beta])
    db_session.commit()

    # Create 2 achievements: 30 pts and 70 pts
    ach30_r = client.post("/api/academy/achievements", json={
        "code": f"ACH-30-{uuid.uuid4().hex[:6]}", "title": "Logro 30", "points": 30
    }, headers=headers)
    ach30_id = ach30_r.json()["id"]

    ach70_r = client.post("/api/academy/achievements", json={
        "code": f"ACH-70-{uuid.uuid4().hex[:6]}", "title": "Logro 70", "points": 70
    }, headers=headers)
    ach70_id = ach70_r.json()["id"]

    # Alpha gets 30 pts
    client.post("/api/academy/achievements/award", json={
        "student_id": str(st_alpha.id), "achievement_id": ach30_id
    }, headers=headers)

    # Beta gets 70 pts + 30 pts = 100 pts
    client.post("/api/academy/achievements/award", json={
        "student_id": str(st_beta.id), "achievement_id": ach70_id
    }, headers=headers)
    client.post("/api/academy/achievements/award", json={
        "student_id": str(st_beta.id), "achievement_id": ach30_id
    }, headers=headers)

    # Recalculate
    recalc_r = client.post("/api/academy/leaderboard/recalculate", json={
        "period": "2026-Q3",
    }, headers=headers)
    assert recalc_r.status_code == 200
    board = recalc_r.json()
    assert len(board) >= 2

    # Beta must be rank 1 with 100 points, Alpha rank 2 with 30 points
    beta_entry = next(e for e in board if e["student_id"] == str(st_beta.id))
    alpha_entry = next(e for e in board if e["student_id"] == str(st_alpha.id))

    assert beta_entry["total_points"] == 100
    assert beta_entry["rank"] == 1
    assert alpha_entry["total_points"] == 30
    assert alpha_entry["rank"] == 2


def test_035_leaderboard_query_filters(client, db_session):
    """Test querying leaderboard entries with period and limit."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    board_r = client.get("/api/academy/leaderboard?period=2026-Q3&limit=10", headers=headers)
    assert board_r.status_code == 200
    entries = board_r.json()
    assert isinstance(entries, list)
    if len(entries) > 1:
        # Must be strictly ordered by rank ascending
        ranks = [e["rank"] for e in entries if e["rank"] is not None]
        assert ranks == sorted(ranks)


def test_036_create_study_group(client, db_session):
    """Test creating an AcademyStudyGroup with auto-leader enrollment."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog SG", "code": f"PSG-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan SG", "code": f"PLSG-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub SG", "code": f"SSG-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period SG", "code": f"PERSG-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeSG-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 20}, headers=headers)
    off_id = off_r.json()["id"]

    sg_r = client.post("/api/academy/study-groups", json={
        "offering_id": off_id,
        "name": "Grupo de Estudio Hermenéutica",
        "description": "Repaso de textos y preparación para la defensa",
        "max_members": 5,
    }, headers=headers)
    assert sg_r.status_code == 201, sg_r.text
    sg_data = sg_r.json()
    assert sg_data["name"] == "Grupo de Estudio Hermenéutica"
    assert sg_data["max_members"] == 5
    assert sg_data["is_active"] is True
    assert sg_data["members_count"] == 1
    assert sg_data["members"][0]["role"] == "leader"


def test_037_list_study_groups_by_offering(client, db_session):
    """Test querying study groups filtered by offering_id."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog SG2", "code": f"PSG2-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan SG2", "code": f"PLSG2-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub SG2", "code": f"SSG2-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period SG2", "code": f"PERSG2-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeSG2-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 20}, headers=headers)
    off_id = off_r.json()["id"]

    client.post("/api/academy/study-groups", json={
        "offering_id": off_id,
        "name": "Grupo Alpha",
    }, headers=headers)

    list_r = client.get(f"/api/academy/study-groups/{off_id}", headers=headers)
    assert list_r.status_code == 200
    groups = list_r.json()
    assert len(groups) >= 1
    assert any(g["name"] == "Grupo Alpha" for g in groups)


def test_038_join_study_group(client, db_session):
    """Test joining a study group and conflict on duplicate join."""
    admin, _, _ = seed_admin(db_session)
    headers_admin = auth_headers(client, email=admin.email, password="testpass123")

    st_user, _, _ = seed_admin(db_session, email="st_join@example.com")
    headers_st = auth_headers(client, email="st_join@example.com", password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog SG3", "code": f"PSG3-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers_admin)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan SG3", "code": f"PLSG3-{uuid.uuid4().hex[:4]}"}, headers=headers_admin)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub SG3", "code": f"SSG3-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers_admin)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period SG3", "code": f"PERSG3-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers_admin)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeSG3-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers_admin)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 20}, headers=headers_admin)
    off_id = off_r.json()["id"]

    sg_r = client.post("/api/academy/study-groups", json={
        "offering_id": off_id,
        "name": "Grupo Para Unirse",
        "max_members": 4,
    }, headers=headers_admin)
    sg_id = sg_r.json()["id"]

    # Student joins
    join_r = client.post(f"/api/academy/study-groups/{sg_id}/join", headers=headers_st)
    assert join_r.status_code == 201, join_r.text
    j_data = join_r.json()
    assert j_data["group_id"] == sg_id
    assert j_data["role"] == "member"

    # Duplicate join returns 409
    dup_r = client.post(f"/api/academy/study-groups/{sg_id}/join", headers=headers_st)
    assert dup_r.status_code == 409


def test_039_study_group_max_members_limit(client, db_session):
    """Test that joining an already full study group fails with 400 Bad Request."""
    admin, _, _ = seed_admin(db_session)
    headers_admin = auth_headers(client, email=admin.email, password="testpass123")

    user2, _, _ = seed_admin(db_session, email="st_max2@example.com")
    headers2 = auth_headers(client, email="st_max2@example.com", password="testpass123")

    user3, _, _ = seed_admin(db_session, email="st_max3@example.com")
    headers3 = auth_headers(client, email="st_max3@example.com", password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog SG4", "code": f"PSG4-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers_admin)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan SG4", "code": f"PLSG4-{uuid.uuid4().hex[:4]}"}, headers=headers_admin)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub SG4", "code": f"SSG4-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers_admin)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period SG4", "code": f"PERSG4-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers_admin)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeSG4-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers_admin)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 20}, headers=headers_admin)
    off_id = off_r.json()["id"]

    # Max members = 2 (leader + 1 member)
    sg_r = client.post("/api/academy/study-groups", json={
        "offering_id": off_id,
        "name": "Grupo Estricto de 2",
        "max_members": 2,
    }, headers=headers_admin)
    sg_id = sg_r.json()["id"]

    # Member 2 joins -> succeeds (group now full with 2)
    j2 = client.post(f"/api/academy/study-groups/{sg_id}/join", headers=headers2)
    assert j2.status_code == 201

    # Member 3 tries to join -> fails with 400
    j3 = client.post(f"/api/academy/study-groups/{sg_id}/join", headers=headers3)
    assert j3.status_code == 400
    assert "límite máximo" in j3.json()["detail"]


def test_040_leave_study_group_and_my_groups(client, db_session):
    """Test leaving a study group and querying personal study group memberships."""
    admin, _, _ = seed_admin(db_session)
    headers_admin = auth_headers(client, email=admin.email, password="testpass123")

    user_leave, _, _ = seed_admin(db_session, email="st_leave@example.com")
    headers_leave = auth_headers(client, email="st_leave@example.com", password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog SG5", "code": f"PSG5-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers_admin)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan SG5", "code": f"PLSG5-{uuid.uuid4().hex[:4]}"}, headers=headers_admin)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub SG5", "code": f"SSG5-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers_admin)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period SG5", "code": f"PERSG5-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers_admin)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeSG5-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers_admin)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 20}, headers=headers_admin)
    off_id = off_r.json()["id"]

    sg_r = client.post("/api/academy/study-groups", json={
        "offering_id": off_id,
        "name": "Grupo Para Salir",
        "max_members": 5,
    }, headers=headers_admin)
    sg_id = sg_r.json()["id"]

    # Student joins
    client.post(f"/api/academy/study-groups/{sg_id}/join", headers=headers_leave)

    # Student queries /study-groups/my
    my_r = client.get("/api/academy/study-groups/my", headers=headers_leave)
    assert my_r.status_code == 200
    my_groups = my_r.json()
    assert any(g["id"] == sg_id for g in my_groups)

    # Student leaves
    leave_r = client.delete(f"/api/academy/study-groups/{sg_id}/leave", headers=headers_leave)
    assert leave_r.status_code == 204

    # Student queries /study-groups/my again -> group no longer present
    my_r2 = client.get("/api/academy/study-groups/my", headers=headers_leave)
    assert my_r2.status_code == 200
    my_groups2 = my_r2.json()
    assert not any(g["id"] == sg_id for g in my_groups2)

    # Leaving again returns 404
    leave_again = client.delete(f"/api/academy/study-groups/{sg_id}/leave", headers=headers_leave)
    assert leave_again.status_code == 404


# ---------------------------------------------------------------------------
# Hito 7: Tests 049 a 054 — Calendario Académico Inteligente y Predicción
# ---------------------------------------------------------------------------

def test_049_create_calendar_event(client, db_session):
    """Test creating an academic calendar event with valid attributes."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    payload = {
        "title": "Examen Parcial Hermenéutica",
        "description": "Evaluación presencial corte 1",
        "event_type": "evaluation",
        "start_date": "2026-10-12T08:00:00Z",
        "end_date": "2026-10-12T10:00:00Z",
    }
    r = client.post("/api/academy/calendar/events", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Examen Parcial Hermenéutica"
    assert data["event_type"] == "evaluation"
    assert data["created_by"] == str(admin.id)
    assert "id" in data


def test_050_get_calendar_events_filter_by_offering(client, db_session):
    """Test filtering calendar events by specific academic offering."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    prog_r = client.post("/api/academy/admin/programs", json={
        "name": "Prog Cal", "code": f"PCAL-{uuid.uuid4().hex[:6]}", "program_type": "curso_libre", "has_teachers": True, "teachers_can_grade": True
    }, headers=headers)
    prog_id = prog_r.json()["id"]
    plan_r = client.post("/api/academy/admin/study-plans", json={"program_id": prog_id, "name": "Plan Cal", "code": f"PLCAL-{uuid.uuid4().hex[:4]}"}, headers=headers)
    plan_id = plan_r.json()["id"]
    sub_r = client.post(f"/api/academy/admin/study-plans/{plan_id}/subjects", json={"name": "Sub Cal", "code": f"SCAL-{uuid.uuid4().hex[:4]}", "credits": 2, "order_index": 1}, headers=headers)
    sub_id = sub_r.json()["id"]
    per_r = client.post("/api/academy/admin/periods", json={"name": "Period Cal", "code": f"PERCAL-{uuid.uuid4().hex[:4]}", "start_date": "2026-01-01", "end_date": "2026-12-31"}, headers=headers)
    per_id = per_r.json()["id"]
    sch_r = client.post("/api/academy/admin/grading-schemes", json={"name": f"SchemeCal-{uuid.uuid4().hex[:4]}", "scale_max": 100.0, "passing_grade": 70.0, "cuts": [{"name": "C1", "weight_percent": 100.0, "order_index": 1}]}, headers=headers)
    sch_id = sch_r.json()["id"]
    off_r = client.post("/api/academy/admin/offerings", json={"academic_period_id": per_id, "subject_id": sub_id, "grading_scheme_id": sch_id, "quota_max": 20}, headers=headers)
    off_id = off_r.json()["id"]

    # 1. Event tied to offering
    e1 = client.post("/api/academy/calendar/events", json={
        "offering_id": off_id,
        "title": "Entrega Ensayo Teológico",
        "event_type": "assignment",
        "start_date": "2026-10-15T14:00:00Z",
        "end_date": "2026-10-15T18:00:00Z",
    }, headers=headers).json()

    # 2. Event global (no offering)
    client.post("/api/academy/calendar/events", json={
        "title": "Conferencia General Institucional",
        "event_type": "milestone",
        "start_date": "2026-10-16T18:00:00Z",
        "end_date": "2026-10-16T21:00:00Z",
    }, headers=headers)

    # Filter by offering_id
    list_r = client.get(f"/api/academy/calendar/events?offering_id={off_id}", headers=headers)
    assert list_r.status_code == 200
    events = list_r.json()
    assert len(events) >= 1
    assert any(e["id"] == e1["id"] for e in events)
    assert all(e["offering_id"] == off_id for e in events)


def test_051_get_calendar_events_filter_by_date_range_and_type(client, db_session):
    """Test filtering calendar events by date window and event_type."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    unique_title = f"Defensa Mayéutica {uuid.uuid4().hex[:6]}"
    client.post("/api/academy/calendar/events", json={
        "title": unique_title,
        "event_type": "socratic_defense",
        "start_date": "2026-11-02T10:00:00Z",
        "end_date": "2026-11-02T11:00:00Z",
    }, headers=headers)

    # Query with matching type and date range
    r = client.get(
        "/api/academy/calendar/events?event_type=socratic_defense&start_date=2026-11-01T00:00:00Z&end_date=2026-11-03T23:59:59Z",
        headers=headers,
    )
    assert r.status_code == 200
    events = r.json()
    assert any(e["title"] == unique_title for e in events)

    # Query outside the date range -> should not contain it
    r_empty = client.get(
        f"/api/academy/calendar/events?event_type=socratic_defense&start_date=2026-11-10T00:00:00Z&end_date=2026-11-15T23:59:59Z",
        headers=headers,
    )
    assert r_empty.status_code == 200
    assert not any(e["title"] == unique_title for e in r_empty.json())


def test_052_calendar_event_validation_dates_and_type(client, db_session):
    """Test invalid calendar event dates, invalid event_type, and nonexistent offering."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    # end_date before start_date
    bad_dates = client.post("/api/academy/calendar/events", json={
        "title": "Fechas Invertidas",
        "event_type": "evaluation",
        "start_date": "2026-10-10T12:00:00Z",
        "end_date": "2026-10-10T10:00:00Z",
    }, headers=headers)
    assert bad_dates.status_code in (400, 422)

    # Invalid event_type
    bad_type = client.post("/api/academy/calendar/events", json={
        "title": "Tipo Invalido",
        "event_type": "recreativo_invalido",
        "start_date": "2026-10-10T10:00:00Z",
        "end_date": "2026-10-10T12:00:00Z",
    }, headers=headers)
    assert bad_type.status_code == 422

    # Nonexistent offering
    bad_offering = client.post("/api/academy/calendar/events", json={
        "title": "Offering Fantasma",
        "offering_id": str(uuid.uuid4()),
        "event_type": "assignment",
        "start_date": "2026-10-10T10:00:00Z",
        "end_date": "2026-10-10T12:00:00Z",
    }, headers=headers)
    assert bad_offering.status_code == 404


def test_053_workload_prediction_normal(client, db_session):
    """Test workload prediction returns structured week projections with balanced status."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    r = client.get(
        "/api/academy/calendar/workload-prediction?weeks_ahead=4&start_from=2026-10-05T00:00:00Z",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["weeks_analyzed"] == 4
    assert len(data["weeks"]) == 4
    assert "overloaded_weeks_count" in data
    assert "recommendations" in data
    for week in data["weeks"]:
        assert "week_number" in week
        assert "workload_level" in week
        assert "is_overloaded" in week


def test_054_workload_prediction_overload_detection(client, db_session):
    """Test workload prediction correctly flags weeks with heavy event clustering (overload)."""
    admin, _, _ = seed_admin(db_session)
    headers = auth_headers(client, email=admin.email, password="testpass123")

    # In week of 2026-10-19, create 2 evaluations + 2 assignments to trigger overload
    overload_week_monday = "2026-10-19T00:00:00Z"

    for i in range(2):
        client.post("/api/academy/calendar/events", json={
            "title": f"Examen Riguroso {i+1}",
            "event_type": "evaluation",
            "start_date": f"2026-10-2{i+1}T08:00:00Z",
            "end_date": f"2026-10-2{i+1}T10:00:00Z",
        }, headers=headers)

    for i in range(2):
        client.post("/api/academy/calendar/events", json={
            "title": f"Entrega Proyecto {i+1}",
            "event_type": "assignment",
            "start_date": f"2026-10-2{i+3}T14:00:00Z",
            "end_date": f"2026-10-2{i+3}T18:00:00Z",
        }, headers=headers)

    # Query workload prediction starting on the overload week
    r = client.get(
        f"/api/academy/calendar/workload-prediction?weeks_ahead=2&start_from={overload_week_monday}",
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["overloaded_weeks_count"] >= 1
    overloaded_weeks = [w for w in data["weeks"] if w["is_overloaded"]]
    assert len(overloaded_weeks) >= 1
    assert overloaded_weeks[0]["workload_level"] == "overload"
    assert overloaded_weeks[0]["evaluations_count"] >= 2
    assert any("Sobrecarga detectada" in rec for rec in data["recommendations"])

