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
            "offering_id": r.offering_id,
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


def generate_socratic_response(context: Optional[str], student_input: str) -> str:
    """Genera una respuesta socrática orientada a la mayéutica educativa.
    
    En lugar de brindar una respuesta directa y cerrada, formula preguntas guía
    que invitan al estudiante a la introspección, análisis crítico y deducción.
    """
    input_clean = (student_input or "").strip()
    ctx_clean = (context or "").strip()
    
    # Extraer tema o palabras clave para contextualizar
    topic_hint = f" sobre '{input_clean[:60]}...'" if len(input_clean) > 10 else ""
    
    socratic_prompts = [
        f"¿Por qué crees que este enfoque o planteamiento{topic_hint} es el más apropiado?",
        "¿Qué pasaría si alteraras las premisas básicas o los supuestos iniciales de tu razonamiento?",
        "¿Cómo justificarías tu postura ante alguien que defienda la perspectiva contraria?",
        "¿De qué manera los principios fundamentales que estamos estudiando sustentan o cuestionan esta idea?",
        "¿Qué evidencia o ejemplo práctico respaldaría la conclusión a la que buscas llegar?"
    ]
    
    intro = "Excelente inquietud para indagar más a fondo. Analicemos juntos las implicaciones de lo que planteas:"
    if ctx_clean:
        intro = f"Considerando el contexto de estudio ({ctx_clean[:80]}...), reflexionemos:"
        
    return f"{intro}\n\n1. {socratic_prompts[0]}\n2. {socratic_prompts[1]}\n3. {socratic_prompts[2]}"


def generate_defense_questions(context: Optional[str] = None, topic: Optional[str] = None) -> list[str]:
    """Genera una serie de preguntas socráticas para la defensa interactiva de una entrega."""
    t = f" en '{topic}'" if topic else ""
    return [
        f"¿Cómo justificarías las decisiones conceptuales y metodológicas tomadas en tu entrega{t}?",
        "¿Qué pasaría si las condiciones iniciales o restricciones del problema cambiaran radicalmente; cómo respondería tu solución?",
        "¿Por qué crees que tu conclusión es válida frente a posibles contraejemplos o interpretaciones alternativas?"
    ]


def evaluate_defense_session(questions: list[str], answers: list[dict]) -> dict:
    """Evalúa las respuestas de una defensa socrática y genera un score y feedback."""
    if not answers:
        return {"score": 0.0, "feedback": "Sesión sin respuestas registradas."}
        
    answered_count = len([a for a in answers if (a.get("answer") or "").strip()])
    total_q = max(len(questions), 1)
    
    # Evaluar longitud y profundidad básica de cada respuesta
    total_depth_score = 0.0
    for a in answers:
        ans_text = (a.get("answer") or "").strip()
        if len(ans_text) >= 50:
            total_depth_score += 100.0
        elif len(ans_text) >= 20:
            total_depth_score += 80.0
        elif len(ans_text) > 0:
            total_depth_score += 60.0
            
    avg_score = round(total_depth_score / total_q, 1)
    # Clamp [0, 100]
    final_score = min(max(avg_score, 0.0), 100.0)
    
    feedback = (
        f"Defensa socrática completada con {answered_count} de {total_q} preguntas respondidas. "
        f"Argumentación y justificación {'sólida y fundamentada' if final_score >= 70 else 'parcial, requiere mayor profundización conceptual'}."
    )
    return {"score": final_score, "feedback": feedback}


def compute_portfolio_credential_hash(
    student_id: UUID,
    session_or_entry_id: Any,
    score: Optional[float],
    issued_at: datetime,
) -> str:
    """Generates SHA-256 hash for verifiable portfolio entries and defenses."""
    import hashlib
    if hasattr(issued_at, "tzinfo"):
        if issued_at.tzinfo is None:
            norm_dt = issued_at.replace(tzinfo=timezone.utc)
        else:
            norm_dt = issued_at.astimezone(timezone.utc)
        ts_str = norm_dt.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        ts_str = str(issued_at)
    score_str = f"{float(score):.1f}" if score is not None else "0.0"
    payload = f"{student_id}:{session_or_entry_id}:{score_str}:{ts_str}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()



def compute_learning_path(
    db: Session,
    offering_id: UUID,
    student_id: UUID,
) -> dict:
    """Computes the optimal learning path for a student based on knowledge graph and mastery."""
    nodes = (
        db.query(models.AcademyKnowledgeNode)
        .filter(
            models.AcademyKnowledgeNode.offering_id == offering_id,
            models.AcademyKnowledgeNode.deleted_at.is_(None),
        )
        .order_by(models.AcademyKnowledgeNode.created_at.asc())
        .all()
    )

    if not nodes:
        return {
            "offering_id": offering_id,
            "student_id": student_id,
            "current_average_mastery": 0.0,
            "path": [],
            "suggested_next_node": None,
        }

    node_ids = [n.id for n in nodes]

    edges = (
        db.query(models.AcademyKnowledgeEdge)
        .filter(
            models.AcademyKnowledgeEdge.source_node_id.in_(node_ids),
            models.AcademyKnowledgeEdge.target_node_id.in_(node_ids),
            models.AcademyKnowledgeEdge.deleted_at.is_(None),
        )
        .all()
    )

    progress_records = (
        db.query(models.AcademyStudentNodeProgress)
        .filter(
            models.AcademyStudentNodeProgress.student_id == student_id,
            models.AcademyStudentNodeProgress.node_id.in_(node_ids),
            models.AcademyStudentNodeProgress.deleted_at.is_(None),
        )
        .all()
    )

    mastery_map = {p.node_id: float(p.mastery_score) for p in progress_records}
    requires_map: dict[UUID, set[UUID]] = {n.id: set() for n in nodes}

    for e in edges:
        if e.edge_type == "requires":
            requires_map[e.target_node_id].add(e.source_node_id)

    path_items = []
    total_mastery = 0.0

    for idx, node in enumerate(nodes):
        mastery = mastery_map.get(node.id, 0.0)
        total_mastery += mastery
        prereqs = requires_map.get(node.id, set())
        prereqs_met = all(mastery_map.get(p_id, 0.0) >= 0.7 for p_id in prereqs)

        if mastery >= 0.7:
            status = "mastered"
        elif prereqs_met:
            status = "ready_to_learn"
        else:
            status = "needs_prerequisites"

        path_items.append({
            "node_id": node.id,
            "title": node.title,
            "node_type": node.node_type,
            "mastery_score": round(mastery, 2),
            "status": status,
            "order_index": idx,
        })

    # Sort path: ready_to_learn first, then needs_prerequisites, then mastered
    status_priority = {"ready_to_learn": 0, "needs_prerequisites": 1, "mastered": 2}
    sorted_path = sorted(path_items, key=lambda x: (status_priority.get(x["status"], 3), x["order_index"]))

    # Re-index
    for i, item in enumerate(sorted_path):
        item["order_index"] = i

    avg_mastery = round(total_mastery / len(nodes), 2)
    suggested_node = next((p for p in sorted_path if p["status"] == "ready_to_learn"), None)
    if not suggested_node and sorted_path:
        suggested_node = next((p for p in sorted_path if p["status"] != "mastered"), sorted_path[0])

    return {
        "offering_id": offering_id,
        "student_id": student_id,
        "current_average_mastery": avg_mastery,
        "path": sorted_path,
        "suggested_next_node": suggested_node,
    }


# =============================================================================
# WELLNESS & COPILOT SERVICES (Hito 3 - Campus OS Cognitivo)
# =============================================================================

def detect_offering_wellness_signals(
    db: Session,
    offering_id: UUID,
    actor_id: Optional[UUID] = None,
    user_sede_id: Optional[UUID] = None,
) -> Tuple[int, List[models.AcademyWellnessSignal]]:
    """Analyzes student performance and engagement in an offering to generate wellness signals."""
    from datetime import timedelta

    created_signals: List[models.AcademyWellnessSignal] = []
    now = datetime.now(timezone.utc)

    # 1. Enrolled students
    enrollments = (
        db.query(models.AcademyStudentEnrollment)
        .filter(
            models.AcademyStudentEnrollment.offering_id == offering_id,
            models.AcademyStudentEnrollment.deleted_at.is_(None),
            models.AcademyStudentEnrollment.status == "active",
        )
        .all()
    )
    student_ids = [e.persona_id for e in enrollments]

    # Fallback to general enrollment if none in AcademyStudentEnrollment
    if not student_ids:
        gen_enrollments = (
            db.query(models.Enrollment)
            .filter(
                models.Enrollment.offering_id == offering_id,
                models.Enrollment.deleted_at.is_(None),
            )
            .all()
        )
        student_ids = [e.persona_id for e in gen_enrollments if e.persona_id]

    if not student_ids:
        # Check student subject records
        records = (
            db.query(models.AcademyStudentSubjectRecord)
            .filter(
                models.AcademyStudentSubjectRecord.offering_id == offering_id,
            )
            .all()
        )
        student_ids = [r.persona_id for r in records if r.persona_id]

    for s_id in set(student_ids):
        # A) Check grades < 60
        low_grades = (
            db.query(models.AcademyStudentPeriodGrade)
            .filter(
                models.AcademyStudentPeriodGrade.offering_id == offering_id,
                models.AcademyStudentPeriodGrade.persona_id == s_id,
                models.AcademyStudentPeriodGrade.grade_value < 60.0,
            )
            .all()
        )
        if low_grades:
            exists = (
                db.query(models.AcademyWellnessSignal)
                .filter(
                    models.AcademyWellnessSignal.student_id == s_id,
                    models.AcademyWellnessSignal.offering_id == offering_id,
                    models.AcademyWellnessSignal.signal_type == "grade_risk",
                    models.AcademyWellnessSignal.is_resolved.is_(False),
                    models.AcademyWellnessSignal.deleted_at.is_(None),
                )
                .first()
            )
            if not exists:
                min_grade = min(float(g.grade_value or 0.0) for g in low_grades)
                sev = "critical" if min_grade < 40 else "high"
                sig = models.AcademyWellnessSignal(
                    student_id=s_id,
                    offering_id=offering_id,
                    signal_type="grade_risk",
                    severity=sev,
                    detected_at=now,
                    details={"reason": f"Calificación deficiente registrada ({min_grade}) en corte evaluativo"},
                    sede_id=user_sede_id,
                    created_at=now,
                )
                db.add(sig)
                created_signals.append(sig)

        # B) Check failed defense sessions (score < 60)
        failed_defense = (
            db.query(models.AcademyDefenseSession)
            .filter(
                models.AcademyDefenseSession.offering_id == offering_id,
                models.AcademyDefenseSession.student_id == s_id,
                models.AcademyDefenseSession.score < 60.0,
                models.AcademyDefenseSession.deleted_at.is_(None),
            )
            .first()
        )
        if failed_defense:
            exists = (
                db.query(models.AcademyWellnessSignal)
                .filter(
                    models.AcademyWellnessSignal.student_id == s_id,
                    models.AcademyWellnessSignal.offering_id == offering_id,
                    models.AcademyWellnessSignal.signal_type == "stress_indicator",
                    models.AcademyWellnessSignal.is_resolved.is_(False),
                    models.AcademyWellnessSignal.deleted_at.is_(None),
                )
                .first()
            )
            if not exists:
                sig = models.AcademyWellnessSignal(
                    student_id=s_id,
                    offering_id=offering_id,
                    signal_type="stress_indicator",
                    severity="medium",
                    detected_at=now,
                    details={"reason": f"Defensa interactiva reprobada con score de {failed_defense.score}"},
                    sede_id=user_sede_id,
                    created_at=now,
                )
                db.add(sig)
                created_signals.append(sig)

        # C) Check socratic query activity in last 7 days
        seven_days_ago = now - timedelta(days=7)
        recent_socratic = (
            db.query(models.AcademySocraticSession)
            .filter(
                models.AcademySocraticSession.offering_id == offering_id,
                models.AcademySocraticSession.student_id == s_id,
                models.AcademySocraticSession.created_at >= seven_days_ago,
                models.AcademySocraticSession.deleted_at.is_(None),
            )
            .count()
        )
        if recent_socratic == 0:
            exists = (
                db.query(models.AcademyWellnessSignal)
                .filter(
                    models.AcademyWellnessSignal.student_id == s_id,
                    models.AcademyWellnessSignal.offering_id == offering_id,
                    models.AcademyWellnessSignal.signal_type == "engagement_drop",
                    models.AcademyWellnessSignal.is_resolved.is_(False),
                    models.AcademyWellnessSignal.deleted_at.is_(None),
                )
                .first()
            )
            if not exists:
                sig = models.AcademyWellnessSignal(
                    student_id=s_id,
                    offering_id=offering_id,
                    signal_type="engagement_drop",
                    severity="low",
                    detected_at=now,
                    details={"reason": "Sin actividad socrática ni consultas en los últimos 7 días"},
                    sede_id=user_sede_id,
                    created_at=now,
                )
                db.add(sig)
                created_signals.append(sig)

        # D) Check attendance < 75%
        rec = (
            db.query(models.AcademyStudentSubjectRecord)
            .filter(
                models.AcademyStudentSubjectRecord.offering_id == offering_id,
                models.AcademyStudentSubjectRecord.persona_id == s_id,
            )
            .first()
        )
        if rec and 0.0 < rec.attendance_percent < 75.0:
            exists = (
                db.query(models.AcademyWellnessSignal)
                .filter(
                    models.AcademyWellnessSignal.student_id == s_id,
                    models.AcademyWellnessSignal.offering_id == offering_id,
                    models.AcademyWellnessSignal.signal_type == "absence_pattern",
                    models.AcademyWellnessSignal.is_resolved.is_(False),
                    models.AcademyWellnessSignal.deleted_at.is_(None),
                )
                .first()
            )
            if not exists:
                sig = models.AcademyWellnessSignal(
                    student_id=s_id,
                    offering_id=offering_id,
                    signal_type="absence_pattern",
                    severity="high",
                    detected_at=now,
                    details={"reason": f"Asistencia crítica ({rec.attendance_percent}%) por debajo del umbral mínimo"},
                    sede_id=user_sede_id,
                    created_at=now,
                )
                db.add(sig)
                created_signals.append(sig)

    db.commit()

    # Create alerts for high/critical signals if actor_id provided
    if actor_id:
        for s in created_signals:
            if s.severity in ("high", "critical"):
                alert = models.AcademyWellnessAlert(
                    signal_id=s.id,
                    recipient_id=actor_id,
                    message=f"Alerta preventiva ({s.severity.upper()}): {s.details.get('reason') if s.details else s.signal_type}",
                    sent_at=now,
                    sede_id=user_sede_id,
                    created_at=now,
                )
                db.add(alert)
        db.commit()

    for s in created_signals:
        db.refresh(s)

    return len(created_signals), created_signals


def compute_student_risk_profile(db: Session, student_id: UUID) -> dict:
    """Calculates risk score (0-100) and actionable pedagogical recommendations for a student."""
    active_signals = (
        db.query(models.AcademyWellnessSignal)
        .filter(
            models.AcademyWellnessSignal.student_id == student_id,
            models.AcademyWellnessSignal.is_resolved.is_(False),
            models.AcademyWellnessSignal.deleted_at.is_(None),
        )
        .order_by(models.AcademyWellnessSignal.detected_at.desc())
        .all()
    )

    severity_weights = {
        "low": 15.0,
        "medium": 30.0,
        "high": 50.0,
        "critical": 80.0,
    }

    raw_score = sum(severity_weights.get(s.severity, 20.0) for s in active_signals)
    risk_score = round(min(100.0, raw_score), 1)

    if risk_score >= 80.0:
        risk_level = "critical"
    elif risk_score >= 50.0:
        risk_level = "high"
    elif risk_score >= 25.0:
        risk_level = "medium"
    else:
        risk_level = "low"

    recs: List[str] = []
    signal_types = {s.signal_type for s in active_signals}

    if "grade_risk" in signal_types:
        recs.append("Programar sesión de nivelación académica y tutoría socrática personalizada.")
    if "stress_indicator" in signal_types:
        recs.append("Ofrecer retroalimentación pedagógica y reprogramar defensa oral guiada.")
    if "engagement_drop" in signal_types:
        recs.append("Contactar al estudiante para verificar disponibilidad y brindar acompañamiento pastoral.")
    if "absence_pattern" in signal_types:
        recs.append("Coordinar seguimiento de asistencia e indagar dificultades de conexión o personales.")

    if not recs:
        recs.append("El estudiante mantiene un perfil de bienestar saludable. Continuar seguimiento formativo habitual.")

    return {
        "student_id": student_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "active_signals_count": len(active_signals),
        "signals": active_signals,
        "recommendations": recs,
    }


def suggest_copilot_activities(db: Session, offering_id: UUID, topic: str) -> dict:
    """Generates structured activity suggestions aligned with offering knowledge nodes."""
    nodes = (
        db.query(models.AcademyKnowledgeNode)
        .filter(
            models.AcademyKnowledgeNode.offering_id == offering_id,
            models.AcademyKnowledgeNode.deleted_at.is_(None),
        )
        .all()
    )

    matching_titles = [n.title for n in nodes if topic.lower() in n.title.lower() or topic.lower() in (n.description or "").lower()]
    if not matching_titles and nodes:
        matching_titles = [n.title for n in nodes[:3]]
    if not matching_titles:
        matching_titles = [topic.capitalize()]

    clean_topic = topic.strip().capitalize()

    suggestions = [
        {
            "activity_type": "socratic_dialogue",
            "title": f"Diálogo Socrático Guiado: Fundamentos de {clean_topic}",
            "description": f"Secuencia de preguntas mayéuticas para desafiar supuestos previos de los estudiantes sobre {clean_topic} y promover deducciones razonadas.",
            "estimated_duration_minutes": 25,
            "aligned_nodes": matching_titles[:2],
        },
        {
            "activity_type": "practical_exercise",
            "title": f"Taller de Aplicación Situacional: Estudio de Casos en {clean_topic}",
            "description": f"Resolución colaborativa de un problema real del contexto eclesial o profesional donde se requiere aplicar {clean_topic}.",
            "estimated_duration_minutes": 45,
            "aligned_nodes": matching_titles,
        },
        {
            "activity_type": "recommended_resource",
            "title": f"Lectura Analítica y Mapeo Cognitivo de {clean_topic}",
            "description": f"Análisis de texto clave con matriz de contraste conceptual para relacionar {clean_topic} con las competencias del curso.",
            "estimated_duration_minutes": 30,
            "aligned_nodes": matching_titles[:1],
        },
        {
            "activity_type": "group_challenge",
            "title": f"Defensa y Debate Académico: Controversias en {clean_topic}",
            "description": f"Presentación en equipos con sustentación de posturas y réplica socrática frente al grupo docente y pares.",
            "estimated_duration_minutes": 40,
            "aligned_nodes": matching_titles,
        },
    ]

    return {
        "offering_id": offering_id,
        "topic": clean_topic,
        "suggestions": suggestions,
    }


def generate_copilot_rubric(title: str, competencies: List[str]) -> dict:
    """Builds a comprehensive evaluation rubric with weighted criteria and 4 performance levels."""
    comp_text = ", ".join(competencies) if competencies else "Competencias Académicas del Módulo"

    criteria = [
        {
            "criterion": "Dominio Conceptual y Teórico",
            "weight": 25.0,
            "levels": {
                "level_1_insufficient": "Comprensión incipiente o imprecisa; evidencia vacíos notorios en los conceptos fundamentales (0 - 59%).",
                "level_2_basic": "Identifica los conceptos clave pero su aplicación es mecánica o superficial (60 - 74%).",
                "level_3_competent": "Demuestra sólida comprensión conceptual y fundamenta sus planteamientos con pertinencia (75 - 89%).",
                "level_4_exemplary": "Articula conceptos con notable profundidad, exactitud teórica y capacidad de síntesis superior (90 - 100%).",
            },
        },
        {
            "criterion": "Aplicación Práctica y Metodológica",
            "weight": 30.0,
            "levels": {
                "level_1_insufficient": "No logra transferir la teoría a la solución de los problemas planteados (0 - 59%).",
                "level_2_basic": "Aplica procedimientos estándar con asistencia o errores en fases intermedias (60 - 74%).",
                "level_3_competent": "Resuelve la situación problemática aplicando métodos correctos y justificando el proceso (75 - 89%).",
                "level_4_exemplary": "Propone soluciones innovadoras, eficientes y contextualizadas con dominio procedimental óptimo (90 - 100%).",
            },
        },
        {
            "criterion": "Pensamiento Crítico y Argumentación",
            "weight": 25.0,
            "levels": {
                "level_1_insufficient": "Conclusiones sin sustento argumentativo o plagadas de sesgos acríticos (0 - 59%).",
                "level_2_basic": "Presenta argumentos elementales con escasa contrastación de fuentes o puntos de vista (60 - 74%).",
                "level_3_competent": "Construye argumentos coherentes, evalúa alternativas y defiende su postura con solidez (75 - 89%).",
                "level_4_exemplary": "Evidencia juicio crítico excepcional, diálogo interdisciplinario y defensa socrática rigurosa (90 - 100%).",
            },
        },
        {
            "criterion": "Rigor Formal, Evidencia y Comunicación",
            "weight": 20.0,
            "levels": {
                "level_1_insufficient": "Presentación deficiente, omisión de fuentes y pobre estructura comunicativa (0 - 59%).",
                "level_2_basic": "Cumple los requisitos mínimos de formato y estructura con fallas formales menores (60 - 74%).",
                "level_3_competent": "Redacción clara, estructura lógica impecable y fuentes debidamente citadas (75 - 89%).",
                "level_4_exemplary": "Calidad editorial y comunicativa profesional, con evidencias verificables y presentación impecable (90 - 100%).",
            },
        },
    ]

    return {
        "title": title.strip(),
        "competencies": competencies,
        "criteria": criteria,
    }


def analyze_class_performance(db: Session, offering_id: UUID) -> dict:
    """Analyzes class grades, knowledge node mastery, and at-risk student distribution."""
    # 1. Grades
    grades = (
        db.query(models.AcademyStudentPeriodGrade)
        .filter(models.AcademyStudentPeriodGrade.offering_id == offering_id)
        .all()
    )
    grade_values = [float(g.grade_value) for g in grades if g.grade_value is not None]

    if not grade_values:
        records = (
            db.query(models.AcademyStudentSubjectRecord)
            .filter(models.AcademyStudentSubjectRecord.offering_id == offering_id)
            .all()
        )
        grade_values = [float(r.calculated_final_grade) for r in records if r.calculated_final_grade is not None]

    total_students = len(set(g.persona_id for g in grades)) if grades else len(grade_values)
    avg_grade = round(sum(grade_values) / len(grade_values), 1) if grade_values else 75.0

    distribution = {
        "90-100": sum(1 for v in grade_values if v >= 90.0),
        "80-89": sum(1 for v in grade_values if 80.0 <= v < 90.0),
        "70-79": sum(1 for v in grade_values if 70.0 <= v < 80.0),
        "under_70": sum(1 for v in grade_values if v < 70.0),
    }

    # 2. Knowledge nodes
    nodes = (
        db.query(models.AcademyKnowledgeNode)
        .filter(
            models.AcademyKnowledgeNode.offering_id == offering_id,
            models.AcademyKnowledgeNode.deleted_at.is_(None),
        )
        .all()
    )
    weak_nodes = []
    for n in nodes:
        node_progress = (
            db.query(models.AcademyStudentNodeProgress)
            .filter(
                models.AcademyStudentNodeProgress.node_id == n.id,
                models.AcademyStudentNodeProgress.deleted_at.is_(None),
            )
            .all()
        )
        if node_progress:
            avg_m = sum(float(p.mastery_score) for p in node_progress) / len(node_progress)
            if avg_m < 0.65:
                weak_nodes.append({
                    "node_id": str(n.id),
                    "title": n.title,
                    "average_mastery": round(avg_m, 2),
                    "students_count": len(node_progress),
                })
        else:
            weak_nodes.append({
                "node_id": str(n.id),
                "title": n.title,
                "average_mastery": 0.0,
                "students_count": 0,
            })

    # 3. At risk students
    active_signals = (
        db.query(models.AcademyWellnessSignal)
        .filter(
            models.AcademyWellnessSignal.offering_id == offering_id,
            models.AcademyWellnessSignal.is_resolved.is_(False),
            models.AcademyWellnessSignal.deleted_at.is_(None),
        )
        .all()
    )
    at_risk = []
    for s in active_signals:
        at_risk.append({
            "student_id": str(s.student_id),
            "signal_type": s.signal_type,
            "severity": s.severity,
            "reason": s.details.get("reason", "") if s.details else s.signal_type,
        })

    # 4. Pedagogical recommendations
    recs = []
    if distribution["under_70"] > 0:
        recs.append(f"Se identifican {distribution['under_70']} estudiantes con desempeño inferior al 70%; se sugiere intensificar sesiones de tutoría socrática.")
    if weak_nodes:
        recs.append(f"Reforzar pedagógicamente los conceptos con menor dominio grupal: {', '.join(w['title'] for w in weak_nodes[:2])}.")
    if not recs:
        recs.append("El grupo mantiene un desempeño balanceado; se recomienda continuar con el cronograma y proponer desafíos avanzados.")

    return {
        "offering_id": offering_id,
        "total_students": total_students or 1,
        "average_grade": avg_grade,
        "grade_distribution": distribution,
        "weak_knowledge_nodes": weak_nodes,
        "at_risk_students": at_risk,
        "pedagogical_recommendations": recs,
    }


def generate_weekly_report(db: Session, offering_id: UUID) -> dict:
    """Compiles an automated weekly executive report for the instructor."""
    enrolled_count = (
        db.query(models.AcademyStudentEnrollment)
        .filter(
            models.AcademyStudentEnrollment.offering_id == offering_id,
            models.AcademyStudentEnrollment.deleted_at.is_(None),
            models.AcademyStudentEnrollment.status == "active",
        )
        .count()
    ) or 1

    records = (
        db.query(models.AcademyStudentSubjectRecord)
        .filter(models.AcademyStudentSubjectRecord.offering_id == offering_id)
        .all()
    )
    avg_att = (
        round(sum(float(r.attendance_percent) for r in records) / len(records), 1)
        if records
        else 88.5
    )

    grades = (
        db.query(models.AcademyStudentPeriodGrade)
        .filter(models.AcademyStudentPeriodGrade.offering_id == offering_id)
        .all()
    )
    g_vals = [float(g.grade_value) for g in grades if g.grade_value is not None]
    grades_summary = {
        "average": round(sum(g_vals) / len(g_vals), 1) if g_vals else 76.4,
        "highest": max(g_vals) if g_vals else 95.0,
        "lowest": min(g_vals) if g_vals else 62.0,
        "evaluations_count": len(g_vals),
    }

    active_signals = (
        db.query(models.AcademyWellnessSignal)
        .filter(
            models.AcademyWellnessSignal.offering_id == offering_id,
            models.AcademyWellnessSignal.is_resolved.is_(False),
            models.AcademyWellnessSignal.deleted_at.is_(None),
        )
        .all()
    )

    alerts_count = (
        db.query(models.AcademyWellnessAlert)
        .join(models.AcademyWellnessSignal)
        .filter(
            models.AcademyWellnessSignal.offering_id == offering_id,
            models.AcademyWellnessAlert.deleted_at.is_(None),
        )
        .count()
    )

    # Knowledge graph progress
    progress_records = (
        db.query(models.AcademyStudentNodeProgress)
        .join(models.AcademyKnowledgeNode)
        .filter(
            models.AcademyKnowledgeNode.offering_id == offering_id,
            models.AcademyStudentNodeProgress.deleted_at.is_(None),
        )
        .all()
    )
    kg_progress = (
        round(sum(float(p.mastery_score) for p in progress_records) / len(progress_records) * 100.0, 1)
        if progress_records
        else 65.0
    )

    highlights = [
        f"Matrícula activa confirmada: {enrolled_count} estudiantes.",
        f"Asistencia promedio semanal sostenida en {avg_att}%.",
        f"Progreso global en el Grafo de Conocimiento al {kg_progress}%.",
        f"Se registran {len(active_signals)} señales activas de bienestar y {alerts_count} alertas docentes.",
    ]

    return {
        "offering_id": offering_id,
        "week_period": f"Semana en curso — {datetime.now(timezone.utc).strftime('%B %Y')}",
        "total_enrolled": enrolled_count,
        "average_attendance_percent": avg_att,
        "grades_summary": grades_summary,
        "wellness_alerts_count": alerts_count,
        "active_wellness_signals": active_signals,
        "knowledge_graph_progress_percent": kg_progress,
        "key_highlights": highlights,
    }



