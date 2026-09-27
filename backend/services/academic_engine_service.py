"""Academic Calculation Engine and Business Service for CCF Academy.

Handles:
- Validation of grading schemes and percentage cut distributions.
- Real-time calculation of student final grades based on weighted cuts (e.g. 30%, 30%, 40%).
- Real-time calculation of student cumulative and period GPA weighted by educational credits (Créditos Educativos).
- Synchronizing student subject records (actas y sábanas de notas).
"""

from __future__ import annotations

from typing import List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from backend import models
from backend.models_shared import _utcnow


def validate_grading_scheme_cuts(cuts: List[dict]) -> Tuple[bool, str]:
    """Validates that cuts have positive weights and sum exactly to 100.0%."""
    if not cuts:
        return False, "El esquema de calificación debe tener al menos un corte de nota"
    
    total_weight = 0.0
    for cut in cuts:
        w = float(cut.get("weight_percent") or 0.0)
        if w <= 0.0 or w > 100.0:
            return False, f"El peso del corte '{cut.get('name')}' debe estar entre 0.1% y 100%"
        total_weight += w
    
    if abs(total_weight - 100.0) > 0.01:
        return False, f"La suma de los cortes debe ser exactamente 100.0%. Suma actual: {total_weight:.1f}%"
    
    return True, ""


def calculate_and_sync_offering_grades(
    db: Session,
    offering_id: UUID,
    persona_id: UUID,
    actor_persona_id: Optional[UUID] = None,
) -> models.AcademyStudentSubjectRecord:
    """Calculates the weighted final grade for a student in a specific course offering

    using the offering's grading scheme cuts, updates the student subject record,
    and returns the updated record.
    """
    offering = (
        db.query(models.AcademyPeriodOffering)
        .options(
            joinedload(models.AcademyPeriodOffering.grading_scheme).joinedload(models.AcademyGradingScheme.cuts),
            joinedload(models.AcademyPeriodOffering.subject),
        )
        .filter(models.AcademyPeriodOffering.id == offering_id)
        .first()
    )
    if not offering:
        raise ValueError(f"Oferta académica {offering_id} no encontrada")

    scheme = offering.grading_scheme
    subject = offering.subject
    subject_credits = subject.credits if subject else 0
    passing_grade = scheme.passing_grade if scheme else 70.0

    # Retrieve all student cut grades for this offering
    cut_grades = (
        db.query(models.AcademyStudentPeriodGrade)
        .filter(
            models.AcademyStudentPeriodGrade.offering_id == offering_id,
            models.AcademyStudentPeriodGrade.persona_id == persona_id,
        )
        .all()
    )
    grades_by_cut = {g.cut_id: g.grade_value for g in cut_grades if g.grade_value is not None}

    # Compute weighted final grade: sum(grade_val * (weight_percent / 100))
    calculated_final = 0.0
    total_weight_graded = 0.0
    for cut in scheme.cuts:
        grade_val = grades_by_cut.get(cut.id)
        if grade_val is not None:
            calculated_final += grade_val * (cut.weight_percent / 100.0)
            total_weight_graded += cut.weight_percent

    calculated_final = round(calculated_final, 2)
    is_passed = calculated_final >= passing_grade

    # Find or create subject record
    record = (
        db.query(models.AcademyStudentSubjectRecord)
        .filter(
            models.AcademyStudentSubjectRecord.offering_id == offering_id,
            models.AcademyStudentSubjectRecord.persona_id == persona_id,
        )
        .first()
    )
    if not record:
        record = models.AcademyStudentSubjectRecord(
            offering_id=offering_id,
            persona_id=persona_id,
            credits_attempted=subject_credits,
            credits_earned=subject_credits if is_passed else 0,
            calculated_final_grade=calculated_final,
            passed=is_passed,
            status="approved" if is_passed else ("failed" if total_weight_graded >= 99.9 else "enrolled"),
            closed_by_persona_id=actor_persona_id,
        )
        db.add(record)
    else:
        record.calculated_final_grade = calculated_final
        record.passed = is_passed
        record.credits_attempted = subject_credits
        record.credits_earned = subject_credits if is_passed else 0
        if total_weight_graded >= 99.9:
            record.status = "approved" if is_passed else "failed"
        record.updated_at = _utcnow()
        if actor_persona_id:
            record.closed_by_persona_id = actor_persona_id

    db.flush()
    return record


def compute_student_transcript_summary(
    db: Session,
    persona_id: UUID,
) -> dict:
    """Computes the full academic record and credit-weighted GPA (PAPA) for a student.

    Formula:
        Weighted GPA = sum(final_grade * credits) / sum(credits)
    """
    records = (
        db.query(models.AcademyStudentSubjectRecord)
        .options(
            joinedload(models.AcademyStudentSubjectRecord.offering).joinedload(models.AcademyPeriodOffering.subject),
            joinedload(models.AcademyStudentSubjectRecord.offering).joinedload(models.AcademyPeriodOffering.academic_period),
            joinedload(models.AcademyStudentSubjectRecord.persona),
        )
        .filter(models.AcademyStudentSubjectRecord.persona_id == persona_id)
        .all()
    )

    persona = db.query(models.Persona).filter(models.Persona.id == persona_id).first()
    student_name = (
        " ".join([persona.first_name or "", persona.last_name or ""]).strip() or f"Estudiante {str(persona_id)[:8]}"
        if persona
        else "Estudiante"
    )

    total_credits_attempted = 0
    total_credits_earned = 0
    weighted_sum = 0.0
    total_credits_for_gpa = 0
    subjects_list = []

    for r in records:
        offering = r.offering
        subject = offering.subject if offering else None
        period = offering.academic_period if offering else None
        sub_code = subject.code if subject else "N/A"
        sub_name = subject.name if subject else "Asignatura"
        sub_credits = subject.credits if subject else 0
        per_code = period.code if period else "N/A"

        effective_grade = r.final_grade_override if r.final_grade_override is not None else (r.calculated_final_grade or 0.0)

        total_credits_attempted += sub_credits
        if r.passed:
            total_credits_earned += sub_credits

        if sub_credits > 0:
            weighted_sum += effective_grade * sub_credits
            total_credits_for_gpa += sub_credits

        subjects_list.append({
            "subject_code": sub_code,
            "subject_name": sub_name,
            "credits": sub_credits,
            "period_code": per_code,
            "final_grade": round(effective_grade, 2),
            "passed": r.passed,
            "status": r.status,
        })

    weighted_gpa = round(weighted_sum / total_credits_for_gpa, 2) if total_credits_for_gpa > 0 else 0.0

    return {
        "persona_id": persona_id,
        "student_name": student_name,
        "total_credits_attempted": total_credits_attempted,
        "total_credits_earned": total_credits_earned,
        "weighted_gpa": weighted_gpa,
        "subjects": subjects_list,
    }

def check_prerequisites_satisfied(db: Session, persona_id: UUID, subject: models.AcademyStudyPlanSubject) -> Tuple[bool, List[str]]:
    """Verifica que el estudiante aprobó los prerequisite_codes de la asignatura."""
    if not subject.prerequisite_codes:
        return True, []
        
    passed_records = (
        db.query(models.AcademyStudentSubjectRecord)
        .join(models.AcademyPeriodOffering)
        .join(models.AcademyStudyPlanSubject)
        .filter(
            models.AcademyStudentSubjectRecord.persona_id == persona_id,
            models.AcademyStudentSubjectRecord.passed == True,
            models.AcademyStudyPlanSubject.code.in_(subject.prerequisite_codes)
        )
        .all()
    )
    
    passed_codes = {r.offering.subject.code for r in passed_records if r.offering and r.offering.subject}
    missing = [req for req in subject.prerequisite_codes if req not in passed_codes]
    
    return len(missing) == 0, missing


def close_offering_grades(db: Session, offering_id: UUID, actor_id: UUID) -> dict:
    """Valida completitud, calcula finales, marca is_locked=True, cambia offering.status='closed'"""
    offering = db.query(models.AcademyPeriodOffering).options(
        joinedload(models.AcademyPeriodOffering.grading_scheme).joinedload(models.AcademyGradingScheme.cuts)
    ).filter(models.AcademyPeriodOffering.id == offering_id).first()
    
    if not offering:
        raise ValueError(f"Oferta {offering_id} no encontrada")
        
    enrollments = (
        db.query(models.AcademyStudentEnrollment)
        .filter(
            models.AcademyStudentEnrollment.offering_id == offering_id,
            models.AcademyStudentEnrollment.status == 'active',
            models.AcademyStudentEnrollment.deleted_at.is_(None)
        ).all()
    )
    
    scheme = offering.grading_scheme
    if not scheme or not scheme.cuts:
        raise ValueError("La oferta no tiene esquema de calificación con cortes")
        
    # Check completitud
    incomplete_students = []
    for enr in enrollments:
        grades = (
            db.query(models.AcademyStudentPeriodGrade)
            .filter(
                models.AcademyStudentPeriodGrade.offering_id == offering_id,
                models.AcademyStudentPeriodGrade.persona_id == enr.persona_id
            ).all()
        )
        graded_cuts = {g.cut_id for g in grades if g.grade_value is not None}
        if len(graded_cuts) < len(scheme.cuts):
            incomplete_students.append(str(enr.persona_id))
            
    if incomplete_students:
        return {"success": False, "incomplete_students": incomplete_students}
        
    # Calculate finals and lock
    for enr in enrollments:
        record = calculate_and_sync_offering_grades(db, offering_id, enr.persona_id, actor_id)
        record.is_locked = True
        
    offering.status = "closed"
    offering.updated_at = _utcnow()
    db.flush()
    
    return {"success": True, "incomplete_students": []}
